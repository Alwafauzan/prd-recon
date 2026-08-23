#!/usr/bin/env python3
"""Read-only Neurovi PRD audit report.

Reports domain groups, E2E domains, owned PRDs, scanner gap candidates with
status, and every recorded fix: automatic source-fact closures, user-confirmed
session decisions, logged defects, and release history. Never writes to the
repository.

The report has two layers:
  1. A plain-language "Ringkasan untuk PM" section for non-technical readers
     (progress, decisions made, what's genuinely still open).
  2. Technical per-group/per-E2E detail (scanner status codes, evidence
     references, decision IDs) for the auditor's own record.

Document-level cross-referencing between open scanner candidates and
confirmed decisions is a heuristic (same document, not the same literal
gap) and is always labelled as such -- it is never presented as proof that
a specific gap is closed.
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

FIX_SOURCE_FACT = "RESOLVED_BY_SOURCE_FACT"
OPEN_STATUSES = {
    "OPEN_SOURCE_EXPLICIT_GAP",
    "OPEN_INSUFFICIENT_SOURCE_EVIDENCE",
    "HUMAN_DECISION_REQUIRED",
}
EXCLUDED_STATUS = "EXCLUDED_NON_ACTIVE_SOURCE_EVIDENCE"

STATUS_LABEL_PLAIN = {
    "RESOLVED_BY_SOURCE_FACT": "sudah lengkap otomatis dari dokumen sumber",
    "OPEN_SOURCE_EXPLICIT_GAP": "memang belum diatur dalam dokumen",
    "OPEN_INSUFFICIENT_SOURCE_EVIDENCE": "bukti di dokumen belum cukup jelas",
    "HUMAN_DECISION_REQUIRED": "menunggu keputusan resmi",
    "EXCLUDED_NON_ACTIVE_SOURCE_EVIDENCE": "di luar cakupan aktif (diabaikan)",
}

SESSION_STATUS_LABEL_PLAIN = {
    "RECONCILED": "selesai",
    "BASELINED": "selesai & dibakukan",
    "AWAITING_USER_DECISION": "berjalan -- masih ada keputusan yang belum difinalisasi",
    "SELECTED_FOR_REVIEW": "dipilih, belum mulai ditinjau",
    "STOPPED_BY_USER": "dihentikan sementara oleh pengguna",
}

DONE_SESSION_STATUSES = {"RECONCILED", "BASELINED"}


def load_json(path, label):
    if not path.is_file():
        sys.exit(f"ERROR: {label} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"ERROR: cannot read {label} {path}: {exc}")


def read_csv_rows(path):
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def short(text, limit=110):
    if not text:
        return "-"
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def cell(text, limit=110):
    return short(text, limit).replace("|", "\\|")


def parse_doc_ids(raw):
    if not raw:
        return []
    return [part.strip() for part in str(raw).split(";") if part.strip()]


def build_doc_id_to_code(manifest):
    """Map every known source document_id (primary or alternate representation)
    to the canonical PRD code, so a decision's affected_documents can be
    resolved to the same document_code used by scanner gap candidates."""
    mapping = {}
    for doc in manifest.get("documents", []):
        code = doc.get("document_code")
        if not code:
            continue
        primary_id = doc.get("primary_source_document_id")
        if primary_id:
            mapping[primary_id] = code
        for rep in doc.get("source_representations") or []:
            rep_id = rep.get("document_id")
            if rep_id:
                mapping[rep_id] = code
    return mapping


def collect_sessions(repo, doc_id_to_code):
    """Return per-E2E session, decision, and defect information.

    Supports both known workspace layouts:
      reconciliation/workspaces/<e2e>/sessions/<mode>/session.json  (current)
      reconciliation/workspaces/<e2e>/session.json                 (legacy, flat)
    """
    sessions = {}
    workspaces = repo / "reconciliation" / "workspaces"
    if not workspaces.is_dir():
        return sessions

    session_files = set(workspaces.glob("*/sessions/*/session.json"))
    session_files |= set(workspaces.glob("*/session.json"))

    for session_file in sorted(session_files):
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        mode_dir = session_file.parent
        rel_parts = session_file.relative_to(workspaces).parts
        e2e_code = data.get("e2e_code") or rel_parts[0]
        entry = sessions.setdefault(
            e2e_code,
            {
                "sessions": [],
                "decisions": [],
                "defects": [],
                "decision_doc_index": defaultdict(list),
            },
        )
        entry["sessions"].append(
            {
                "session_id": data.get("session_id", mode_dir.name),
                "mode": data.get("reconciliation_mode", "UNKNOWN"),
                "status": data.get("status", "UNKNOWN"),
                "updated_at": data.get("updated_at", ""),
            }
        )
        for row in read_csv_rows(mode_dir / "decision-register.csv"):
            if row.get("status") != "USER_CONFIRMED":
                continue
            decision_id = row.get("decision_id", "")
            doc_ids = parse_doc_ids(row.get("affected_documents"))
            doc_codes = sorted({doc_id_to_code[d] for d in doc_ids if d in doc_id_to_code})
            entry["decisions"].append(
                {
                    "decision_id": decision_id,
                    "decision_type": row.get("decision_type", ""),
                    "question": row.get("question", ""),
                    "user_decision": row.get("user_decision", ""),
                    "decided_at": row.get("decided_at", ""),
                    "affected_document_codes": doc_codes,
                }
            )
            for code in doc_codes:
                entry["decision_doc_index"][code].append(decision_id)
        for row in read_csv_rows(mode_dir / "defect-register.csv"):
            entry["defects"].append(
                {
                    "defect_id": row.get("defect_id", ""),
                    "defect_type": row.get("defect_type", ""),
                    "summary": row.get("summary", ""),
                    "status": row.get("status", ""),
                    "decision_question": row.get("decision_question", ""),
                    "notes": row.get("notes", ""),
                }
            )
    return sessions


def collect_releases(repo):
    releases = []
    releases_dir = repo / "reconciliation" / "releases"
    if not releases_dir.is_dir():
        return releases
    for manifest_file in sorted(releases_dir.glob("v*/manifest.json")):
        try:
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        releases.append(
            {
                "version": data.get("repository_version", manifest_file.parent.name),
                "created_at": data.get("created_at", ""),
                "changed_document_count": len(data.get("changed_documents", [])),
                "decision_count": len(data.get("decision_ids", [])),
            }
        )
    return releases


def build_report(repo, e2e_filter=None, group_filter=None):
    worklist = load_json(
        repo / "reconciliation" / "e2e-inventory" / "domain-worklist.json",
        "E2E inventory",
    )
    manifest = load_json(
        repo / "reconciliation" / "canonical" / "manifest.json",
        "canonical manifest",
    )
    automatic = load_json(
        repo / "reconciliation" / "canonical" / "automatic-reconciliation.json",
        "automatic reconciliation register",
    )

    code_by_content = {
        doc["content_id"]: doc["document_code"] for doc in manifest.get("documents", [])
    }
    doc_id_to_code = build_doc_id_to_code(manifest)

    gaps_by_e2e = {}
    for item in automatic.get("items", []):
        gaps_by_e2e.setdefault(item.get("e2e_code", "UNKNOWN"), []).append(item)

    sessions = collect_sessions(repo, doc_id_to_code)
    releases = collect_releases(repo)

    groups = {}
    for domain in worklist.get("domains", []):
        e2e_code = domain.get("e2e_code")
        if e2e_filter and e2e_code != e2e_filter:
            continue
        group = domain.get("domain_group", "tanpa-kelompok")
        if group_filter and group != group_filter:
            continue
        prds = [
            {
                "code": code_by_content.get(doc.get("content_id"), "-"),
                "title": doc.get("title", ""),
                "stage": doc.get("worklist_stage", ""),
                "order": doc.get("worklist_order", 0),
            }
            for doc in domain.get("documents", [])
        ]
        info = sessions.get(
            e2e_code,
            {"sessions": [], "decisions": [], "defects": [], "decision_doc_index": {}},
        )
        groups.setdefault(group, []).append(
            {
                "e2e_code": e2e_code,
                "title": domain.get("title", ""),
                "purpose": domain.get("purpose", ""),
                "relation_count": domain.get("relation_count", 0),
                "cross_domain_relation_count": domain.get(
                    "cross_domain_relation_count", 0
                ),
                "prds": prds,
                "gaps": gaps_by_e2e.get(e2e_code, []),
                "session_info": info,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "canonical_version": manifest.get("canonical_version"),
            "baseline_status": manifest.get("baseline_status"),
            "release_status": manifest.get("release_status"),
            "unique_prd_count": manifest.get("unique_prd_count"),
            "domain_count": manifest.get("domain_count"),
            "semantic_changes": manifest.get("semantic_changes"),
        },
        "automatic_summary": automatic.get("summary", {}),
        "groups": groups,
        "releases": releases,
    }


def gap_counts(items):
    counter = Counter(item.get("reconciliation_status", "UNKNOWN") for item in items)
    return {
        "open": sum(counter.get(status, 0) for status in OPEN_STATUSES),
        "fixed_source_fact": counter.get(FIX_SOURCE_FACT, 0),
        "excluded": counter.get(EXCLUDED_STATUS, 0),
    }


def split_open_items(open_items, decision_doc_index):
    """Split open scanner candidates into those whose document has at least
    one confirmed decision recorded (possibly-addressed, needs verification)
    versus those with no recorded decision at all on that document."""
    matched, unmatched = [], []
    for item in open_items:
        doc_decisions = decision_doc_index.get(item.get("document_code"), [])
        if doc_decisions:
            matched.append((item, doc_decisions))
        else:
            unmatched.append(item)
    return matched, unmatched


def open_defects(defects):
    return [d for d in defects if (d.get("status") or "").upper() == "OPEN"]


def render_pm_summary(report):
    lines = []
    lines.append("## Ringkasan untuk PM")
    lines.append("")
    lines.append(
        "> Bahasa non-teknis. Untuk detail lengkap (ID, status mentah, bukti "
        "kutipan dokumen), lihat bagian teknis di bawah."
    )
    lines.append("")

    any_domain = False
    for group_name in sorted(report["groups"]):
        for domain in report["groups"][group_name]:
            any_domain = True
            gaps = domain["gaps"]
            counts = gap_counts(gaps)
            info = domain["session_info"]
            open_items = [
                item for item in gaps if item.get("reconciliation_status") in OPEN_STATUSES
            ]
            matched, unmatched = split_open_items(
                open_items, info.get("decision_doc_index", {})
            )
            decisions = info["decisions"]
            sessions_list = info["sessions"]
            defects = open_defects(info["defects"])

            lines.append(f"### {domain['title']} ({domain['e2e_code']})")
            lines.append("")
            lines.append(f"- Cakupan: **{len(domain['prds'])} dokumen PRD** ditinjau.")
            lines.append(
                f"- ✅ **{counts['fixed_source_fact']} item** sudah lengkap otomatis "
                "dari dokumen sumber (tidak perlu keputusan manusia)."
            )
            if decisions:
                lines.append(
                    f"- ✅ **{len(decisions)} keputusan resmi** sudah diambil dan "
                    "tercatat (lihat detail teknis untuk daftar lengkap)."
                )
            else:
                lines.append("- Belum ada keputusan resmi manusia yang tercatat untuk alur ini.")
            if open_items:
                if matched:
                    lines.append(
                        f"- 🔎 **{len(matched)} item** masih tercatat sebagai kandidat "
                        "tinjauan pada dokumen yang *sudah* punya keputusan resmi -- "
                        "kemungkinan sudah tercakup, tapi perlu verifikasi akhir satu "
                        "per satu (bukan otomatis dianggap selesai)."
                    )
                if unmatched:
                    lines.append(
                        f"- ⚠️ **{len(unmatched)} item** belum punya keputusan resmi "
                        "sama sekali pada dokumennya -- ini yang benar-benar masih "
                        "perlu ditindaklanjuti."
                    )
            else:
                lines.append("- Tidak ada kandidat tinjauan tersisa dari pemindaian dokumen.")
            if defects:
                lines.append(
                    f"- 🛑 **{len(defects)} catatan masalah** yang sudah pernah "
                    "ditinjau tapi *sengaja* dibiarkan terbuka oleh pengambil "
                    "keputusan (lihat detail teknis untuk alasannya)."
                )
            if sessions_list:
                session_bits = []
                for s in sessions_list:
                    label = SESSION_STATUS_LABEL_PLAIN.get(s["status"], s["status"])
                    session_bits.append(f"{s['mode']} ({label})")
                lines.append(f"- Status sesi peninjauan: {', '.join(session_bits)}.")
                if not any(s["status"] in DONE_SESSION_STATUSES for s in sessions_list):
                    lines.append(
                        "  - Catatan: belum ada sesi yang ditandai *selesai* secara "
                        "resmi, walau seluruh keputusan di dalamnya sudah diambil. "
                        "Sebaiknya sesi ditutup secara resmi agar status tercatat akurat."
                    )
            else:
                lines.append("- Status sesi peninjauan: belum ada sesi yang tercatat.")
            lines.append("")

    if not any_domain:
        lines.append("Tidak ada alur (E2E) pada cakupan filter ini.")
        lines.append("")

    return lines


def render_markdown(report, summary_only=False):
    lines = []
    baseline = report["baseline"]
    summary = report["automatic_summary"]
    total_items = sum(
        len(domain["gaps"]) for group in report["groups"].values() for domain in group
    )
    total_open = sum(
        gap_counts(domain["gaps"])["open"]
        for group in report["groups"].values()
        for domain in group
    )
    total_fixed = sum(
        gap_counts(domain["gaps"])["fixed_source_fact"]
        for group in report["groups"].values()
        for domain in group
    )
    total_excluded = sum(
        gap_counts(domain["gaps"])["excluded"]
        for group in report["groups"].values()
        for domain in group
    )
    all_sessions = [
        session
        for group in report["groups"].values()
        for domain in group
        for session in domain["session_info"]["sessions"]
    ]
    all_decisions = [
        decision
        for group in report["groups"].values()
        for domain in group
        for decision in domain["session_info"]["decisions"]
    ]

    lines.append("# Laporan Audit Rekonsiliasi PRD")
    lines.append("")
    lines.append(
        "> Read-only. Kandidat gap adalah temuan mekanis untuk direview, bukan "
        "kesalahan pasti dan bukan requirement yang disetujui."
    )
    lines.append("")
    lines.append(f"- Dibuat (UTC): `{report['generated_at']}`")
    lines.append(
        f"- Baseline canonical: `{baseline['canonical_version']}` "
        f"(`{baseline['baseline_status']}`, rilis: `{baseline['release_status']}`, "
        f"perubahan semantik: `{baseline['semantic_changes']}`)"
    )
    lines.append("")

    lines.extend(render_pm_summary(report))

    lines.append("## Ringkasan Global (teknis)")
    lines.append("")
    lines.append(
        f"- Kelompok: **{len(report['groups'])}** | E2E: "
        f"**{sum(len(g) for g in report['groups'].values())}** | PRD unik: "
        f"**{baseline['unique_prd_count']}**"
    )
    lines.append(
        f"- Kandidat gap (cakupan report): **{total_items}** | masih terbuka: "
        f"**{total_open}** | tertutup dari source fact: **{total_fixed}** | "
        f"dikecualikan: **{total_excluded}**"
    )
    if summary:
        lines.append(
            f"- Register global (seluruh repo, tanpa filter): {summary.get('candidate_count', 0)} "
            f"kandidat, {summary.get('resolved_by_source_fact_count', 0)} tertutup otomatis, "
            f"{summary.get('human_decision_required_count', 0)} menunggu keputusan manusia"
        )
    lines.append(
        f"- Sesi rekonsiliasi tercatat: **{len(all_sessions)}** | keputusan "
        f"USER_CONFIRMED: **{len(all_decisions)}** | rilis: **{len(report['releases'])}**"
    )
    if not all_sessions:
        lines.append(
            "- **Belum ada sesi rekonsiliasi manusia yang tercatat.** Seluruh fix "
            "di bawah berasal dari penutupan otomatis source fact."
        )
    lines.append("")

    if report["releases"]:
        lines.append("## Riwayat Rilis")
        lines.append("")
        lines.append("| Versi | Dibuat | Dokumen berubah | Keputusan |")
        lines.append("|---|---|---|---|")
        for release in report["releases"]:
            lines.append(
                f"| `{release['version']}` | {release['created_at']} | "
                f"{release['changed_document_count']} | {release['decision_count']} |"
            )
        lines.append("")

    for group_name in sorted(report["groups"]):
        lines.append(f"## Kelompok: {group_name}")
        lines.append("")
        for domain in report["groups"][group_name]:
            counts = gap_counts(domain["gaps"])
            lines.append(f"### {domain['e2e_code']} | {domain['title']}")
            lines.append("")
            lines.append(f"- Tujuan: {domain['purpose']}")
            lines.append(
                f"- PRD: **{len(domain['prds'])}** | relasi: "
                f"{domain['relation_count']} | lintas-domain: "
                f"{domain['cross_domain_relation_count']}"
            )
            lines.append(
                f"- Gap terbuka: **{counts['open']}** | fix source fact: "
                f"**{counts['fixed_source_fact']}** | dikecualikan: "
                f"**{counts['excluded']}**"
            )
            info = domain["session_info"]
            if info["sessions"]:
                session_text = ", ".join(
                    f"`{s['session_id']}` ({s['mode']}, {s['status']})"
                    for s in info["sessions"]
                )
                lines.append(f"- Sesi: {session_text}")
            else:
                lines.append("- Sesi: belum ada")
            lines.append("")
            lines.append("| Kode | PRD | Stage |")
            lines.append("|---|---|---|")
            for prd in domain["prds"]:
                lines.append(
                    f"| `{prd['code']}` | {cell(prd['title'], 80)} | {prd['stage']} |"
                )
            lines.append("")

            if summary_only:
                continue

            open_items = [
                item
                for item in domain["gaps"]
                if item.get("reconciliation_status") in OPEN_STATUSES
            ]
            fixed_items = [
                item
                for item in domain["gaps"]
                if item.get("reconciliation_status") == FIX_SOURCE_FACT
            ]
            excluded_items = [
                item
                for item in domain["gaps"]
                if item.get("reconciliation_status") == EXCLUDED_STATUS
            ]
            decision_doc_index = info.get("decision_doc_index", {})

            lines.append(f"#### Gap terbuka ({len(open_items)})")
            lines.append("")
            lines.append(
                "Kolom \"Terkait keputusan?\" menandakan dokumen yang sama sudah "
                "punya keputusan resmi tercatat -- ini indikasi, bukan bukti gap "
                "ini pasti tertutup; tetap verifikasi ke dokumen."
            )
            lines.append("")
            if open_items:
                lines.append("| ID | Mode | PRD | Jenis | Status | Terkait keputusan? | Bukti |")
                lines.append("|---|---|---|---|---|---|---|")
                for item in open_items:
                    doc_decisions = decision_doc_index.get(item.get("document_code"), [])
                    related = ", ".join(f"`{d}`" for d in doc_decisions) if doc_decisions else "-"
                    status_plain = STATUS_LABEL_PLAIN.get(
                        item["reconciliation_status"], item["reconciliation_status"]
                    )
                    lines.append(
                        f"| `{item['reconciliation_id']}` | {item['reconciliation_mode']} "
                        f"| `{item['document_code']}` | {item['candidate_type']} "
                        f"| {item['reconciliation_status']} ({status_plain}) "
                        f"| {related} "
                        f"| {cell(item.get('evidence_reference') or '-', 90)} |"
                    )
            else:
                lines.append("Tidak ada gap terbuka pada cakupan register ini.")
            lines.append("")

            lines.append(f"#### Sudah diperbaiki dari source fact ({len(fixed_items)})")
            lines.append("")
            if fixed_items:
                lines.append("| ID | Mode | PRD | Jenis | Bukti literal |")
                lines.append("|---|---|---|---|---|")
                for item in fixed_items:
                    lines.append(
                        f"| `{item['reconciliation_id']}` | {item['reconciliation_mode']} "
                        f"| `{item['document_code']}` | {item['candidate_type']} "
                        f"| {cell(item.get('evidence_reference') or '-', 90)} |"
                    )
            else:
                lines.append("Belum ada fix pada cakupan register ini.")
            lines.append("")

            lines.append(f"#### Dikecualikan dari cakupan aktif ({len(excluded_items)})")
            lines.append("")
            if excluded_items:
                lines.append("| ID | Mode | PRD | Jenis | Alasan | Bukti |")
                lines.append("|---|---|---|---|---|---|")
                for item in excluded_items:
                    lines.append(
                        f"| `{item['reconciliation_id']}` | {item['reconciliation_mode']} "
                        f"| `{item['document_code']}` | {item['candidate_type']} "
                        f"| {item.get('reason', '-')} "
                        f"| {cell(item.get('evidence_reference') or '-', 90)} |"
                    )
            else:
                lines.append("Tidak ada item dikecualikan pada cakupan register ini.")
            lines.append("")

            decisions = info["decisions"]
            lines.append(f"#### Keputusan terkonfirmasi ({len(decisions)})")
            lines.append("")
            if decisions:
                lines.append("| ID | Jenis | Pertanyaan | Keputusan | Dokumen terdampak | Waktu |")
                lines.append("|---|---|---|---|---|---|")
                for decision in decisions:
                    doc_codes = ", ".join(f"`{c}`" for c in decision["affected_document_codes"])
                    lines.append(
                        f"| `{decision['decision_id']}` | {decision['decision_type']} "
                        f"| {cell(decision['question'], 70)} "
                        f"| {cell(decision['user_decision'], 70)} "
                        f"| {doc_codes or '-'} "
                        f"| {decision['decided_at']} |"
                    )
            else:
                lines.append("Belum ada keputusan manusia yang tercatat.")
            lines.append("")

            defects = info["defects"]
            lines.append(f"#### Defect tercatat dari sesi manusia ({len(defects)})")
            lines.append("")
            if defects:
                lines.append("| ID | Jenis | Ringkasan | Status | Catatan |")
                lines.append("|---|---|---|---|---|")
                for defect in defects:
                    lines.append(
                        f"| `{defect['defect_id']}` | {defect['defect_type']} "
                        f"| {cell(defect['summary'], 90)} "
                        f"| {defect['status']} "
                        f"| {cell(defect['notes'], 90)} |"
                    )
            else:
                lines.append("Belum ada defect tercatat dari sesi manusia.")
            lines.append("")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Read-only Neurovi PRD audit report"
    )
    parser.add_argument("--repo", default="neurovi-prd", help="document repository path")
    parser.add_argument("--e2e", help="only include one E2E code, e.g. E2E-RJ")
    parser.add_argument("--group", help="only include one domain group")
    parser.add_argument("--summary-only", action="store_true", help="skip gap item tables")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--output", help="write the report to this file instead of stdout")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    repo = Path(args.repo)
    if not repo.is_dir():
        sys.exit(f"ERROR: repository not found: {repo}")

    report = build_report(repo, e2e_filter=args.e2e, group_filter=args.group)
    if args.e2e and not any(report["groups"].values()):
        sys.exit(f"ERROR: E2E not found in inventory: {args.e2e}")
    if args.group and not report["groups"]:
        sys.exit(f"ERROR: domain group not found in inventory: {args.group}")

    if args.json:
        output = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    else:
        output = render_markdown(report, summary_only=args.summary_only)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
