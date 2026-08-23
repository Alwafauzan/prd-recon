#!/usr/bin/env python3
"""Generate a read-only HTML dashboard of Neurovi PRD reconciliation workspaces.

Reads reconciliation session workspaces (sessions, decision/interview/defect
registers, review-session notes), the scanner candidate register, the canonical
manifest, and the E2E worklist from the document repository, then renders:

  - one detail page per E2E  -> output/workspace-<E2E>.html
  - one overview index        -> output/index.html

The document repository is never modified. Every run rewrites the HTML output
files completely, so re-running the script always refreshes the dashboard.
Reported facts come only from recorded registers; scanner candidates stay
review candidates and a session only counts as done when its status is
RECONCILED or BASELINED.
"""

import argparse
import csv
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DONE_SESSION_STATUSES = {"RECONCILED", "BASELINED"}
OPEN_SCANNER_STATUSES = {
    "OPEN_SOURCE_EXPLICIT_GAP",
    "OPEN_INSUFFICIENT_SOURCE_EVIDENCE",
    "HUMAN_DECISION_REQUIRED",
}

SESSION_BADGE = {
    "RECONCILED": ("b-green", "RECONCILED"),
    "BASELINED": ("b-green", "BASELINED"),
    "AWAITING_USER_DECISION": ("b-amber", "AWAITING_USER_DECISION"),
    "SELECTED_FOR_REVIEW": ("b-blue", "SELECTED_FOR_REVIEW"),
    "STOPPED_BY_USER": ("b-red", "STOPPED_BY_USER"),
}

DECISION_TYPE_BADGE = {
    "CONFLICT_RESOLUTION": ("b-violet", "CONFLICT"),
    "GAP_CLOSURE": ("b-blue", "GAP_CLOSURE"),
    "GAP_RESOLUTION": ("b-slate", "GAP_RES"),
}


# ---------------------------------------------------------------- loading


def load_json(path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def read_csv_rows(path):
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def esc(text):
    return html.escape("" if text is None else str(text))


def load_sources(repo):
    """Load all read-only data sources from the document repository."""
    worklist = load_json(repo / "reconciliation/e2e-inventory/domain-worklist.json") or {}
    manifest = load_json(repo / "reconciliation/canonical/manifest.json") or {}
    scanner = load_json(repo / "reconciliation/canonical/automatic-reconciliation.json") or {}

    domains = {d.get("e2e_code"): d for d in worklist.get("domains", []) if d.get("e2e_code")}

    doc_id_to_code = {}
    code_to_title = {}
    for doc in manifest.get("documents", []):
        code = doc.get("document_code")
        if not code:
            continue
        title = re.sub(r"^\s*PRD\s*[—–-]\s*", "", str(doc.get("original_title") or "")).strip()
        if title:
            code_to_title[code] = title
        primary = doc.get("primary_source_document_id")
        if primary:
            doc_id_to_code[primary] = code
        for rep in doc.get("source_representations") or []:
            rep_id = rep.get("document_id")
            if rep_id:
                doc_id_to_code[rep_id] = code

    scanner_by_e2e = {}
    for item in scanner.get("items", []):
        code = item.get("e2e_code")
        if not code:
            continue
        entry = scanner_by_e2e.setdefault(code, {"ALL": Counter(), "modes": {}})
        status = item.get("reconciliation_status") or "UNKNOWN"
        mode = item.get("reconciliation_mode") or "UNKNOWN"
        entry["ALL"][status] += 1
        entry["modes"].setdefault(mode, Counter())[status] += 1

    sessions = discover_sessions(repo / "reconciliation/workspaces")
    return domains, doc_id_to_code, code_to_title, scanner_by_e2e, sessions


def discover_sessions(workspaces_root):
    """Return {e2e_code: [session, ...]} from workspaces/<e2e>/sessions/<mode>/
    plus the legacy flat layout workspaces/<e2e>/session.json."""
    sessions = {}
    if not workspaces_root.is_dir():
        return sessions
    for e2e_dir in sorted(p for p in workspaces_root.iterdir() if p.is_dir()):
        e2e_code = e2e_dir.name
        found = []
        sessions_root = e2e_dir / "sessions"
        if sessions_root.is_dir():
            for mode_dir in sorted(p for p in sessions_root.iterdir() if p.is_dir()):
                session = load_json(mode_dir / "session.json")
                if session:
                    found.append(load_session_files(mode_dir, session))
        legacy = load_json(e2e_dir / "session.json")
        if legacy:
            found.append(load_session_files(e2e_dir, legacy))
        if found:
            sessions[e2e_code] = found
    return sessions


def load_session_files(session_dir, session):
    return {
        "meta": session,
        "decisions": read_csv_rows(session_dir / "decision-register.csv"),
        "interviews": read_csv_rows(session_dir / "interview-register.csv"),
        "defects": read_csv_rows(session_dir / "defect-register.csv"),
        "review_md": read_text(session_dir / "review-session.md"),
        "dir": session_dir.name,
    }


def read_text(path):
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


# ---------------------------------------------------------------- rendering helpers


def badge(css_class, label):
    return f'<span class="badge {css_class}">{esc(label)}</span>'


def status_badge(status):
    css, label = SESSION_BADGE.get(status, ("b-slate", status or "UNKNOWN"))
    return badge(css, label)


def kpi(num, label, color=None):
    style = f' style="color:var(--{color})"' if color else ""
    return f'<div class="kpi"><div class="num"{style}>{esc(num)}</div><div class="lbl">{label}</div></div>'


def parse_checklist(review_md):
    """Extract the '- [x] / - [ ]' items of the Baseline Readiness section."""
    match = re.search(r"^## Baseline Readiness\s*$", review_md, re.MULTILINE)
    if not match:
        return None
    items = []
    for line in review_md[match.end():].splitlines():
        if line.startswith("## "):
            break
        m = re.match(r"^- \[( |x|X)\]\s*(.+)$", line.strip())
        if m:
            items.append((m.group(1).lower() == "x", m.group(2).strip()))
    return items or None


def render_checklist(items):
    lis = "".join(
        f'<li class="{"done" if done else ""}">{esc(text)}</li>' for done, text in items
    )
    done_count = sum(1 for done, _ in items if done)
    return (
        '<div class="card"><h2>\U0001f6a6 Kesiapan Baseline</h2>'
        f'<div class="desc">{done_count} dari {len(items)} gate selesai (dari review-session.md)</div>'
        f'<ul class="checklist">{lis}</ul></div>'
    )


def render_version_bar(decisions):
    """A-vs-B tally from decisions whose chosen option explicitly follows a version."""
    a = sum(1 for d in decisions if "versi a" in (d.get("user_decision") or "").lower())
    b = sum(1 for d in decisions if "versi b" in (d.get("user_decision") or "").lower())
    if a + b == 0:
        return ""
    total = a + b
    pct_b = round(b / total * 100)
    pct_a = 100 - pct_b
    return (
        '<div class="card"><h2>\U0001f500 Konflik Versi A vs Versi B</h2>'
        f'<div class="desc">{total} keputusan memilih opsi yang eksplisit mengikuti salah satu versi representasi</div>'
        f'<div class="bar-row"><div class="k">Ikuti Versi B</div><div class="bar-track">'
        f'<div class="bar-fill" style="width:{pct_b}%;background:var(--green)">{b}</div></div>'
        f'<div class="v">{b}</div></div>'
        f'<div class="bar-row"><div class="k">Ikuti Versi A</div><div class="bar-track">'
        f'<div class="bar-fill" style="width:{max(pct_a, 4)}%;background:var(--blue)">{a}</div></div>'
        f'<div class="v">{a}</div></div></div>'
    )


def decision_type_cell(dtype):
    css, label = DECISION_TYPE_BADGE.get(dtype, ("b-slate", dtype or "-"))
    return badge(css, label)


def doc_label(code, code_to_title):
    """'PRD-RJ-005 — Pendaftaran Rawat Jalan (MERGED)' or the bare code."""
    title = (code_to_title or {}).get(code)
    return f"{code} — {title}" if title else str(code)


def render_decisions(decisions, doc_id_to_code, code_to_title):
    if not decisions:
        return '<div class="card"><h2>\U0001f9fe Register Keputusan</h2><div class="desc">Belum ada keputusan tercatat pada sesi ini.</div></div>'
    groups = {}
    for row in decisions:
        doc_ids = [p.strip() for p in (row.get("affected_documents") or "").split(";") if p.strip()]
        codes = [doc_id_to_code.get(i, i) for i in doc_ids]
        key = codes[0] if codes else "(tanpa dokumen)"
        groups.setdefault(key, []).append(row)

    type_counts = Counter(d.get("decision_type") or "UNKNOWN" for d in decisions)
    type_desc = " · ".join(f"{n} {t}" for t, n in sorted(type_counts.items()))
    parts = [
        '<div class="card"><h2>\U0001f9fe Register Keputusan (%d)</h2><div class="desc">%s</div>'
        % (len(decisions), esc(type_desc))
    ]
    for code in sorted(groups):
        rows = groups[code]
        parts.append(f'<div class="grp">\U0001f4c4 {esc(doc_label(code, code_to_title))} ({len(rows)} keputusan)</div>')
        parts.append(
            "<table><tr><th>ID</th><th>Pertanyaan</th><th>Keputusan</th><th>Tipe</th><th>Status</th></tr>"
        )
        for row in sorted(rows, key=lambda r: r.get("decision_id") or ""):
            parts.append(
                "<tr>"
                f'<td class="mono">{esc(row.get("decision_id"))}</td>'
                f"<td>{esc(row.get('question'))}</td>"
                f"<td>{esc(row.get('user_decision'))}</td>"
                f"<td>{decision_type_cell(row.get('decision_type'))}</td>"
                f"<td>{esc(row.get('status'))}</td>"
                "</tr>"
            )
        parts.append("</table>")
    parts.append("</div>")
    return "".join(parts)


def render_defects(defects, doc_id_to_code, code_to_title):
    if not defects:
        return '<div class="card"><h2>⚠️ Defect Register</h2><div class="desc">Tidak ada defect tercatat.</div></div>'
    parts = ['<div class="card"><h2>⚠️ Defect Register (%d)</h2><div class="desc">Defect terbuka tetap terlihat sampai ada disposisi resmi</div>' % len(defects)]
    for row in defects:
        status = (row.get("status") or "").strip()
        is_open = status.upper() == "OPEN"
        css = "b-amber" if is_open else "b-green"
        cls = "" if is_open else " closed"
        meta = []
        if row.get("defect_type"):
            meta.append(row["defect_type"])
        doc_ids = [p.strip() for p in (row.get("document_ids") or "").split(";") if p.strip()]
        doc_labels = [
            doc_label(doc_id_to_code.get(i, i), code_to_title) for i in doc_ids
        ]
        if doc_labels:
            meta.append("dok: " + "; ".join(doc_labels))
        if row.get("resolution_decision_id"):
            meta.append(f"ditutup via {row['resolution_decision_id']}")
        if row.get("evidence_references"):
            meta.append(row["evidence_references"])
        parts.append(
            f'<div class="def{cls}"><h3>{esc(row.get("defect_id"))} {badge(css, status or "UNKNOWN")}</h3>'
            f"<p>{esc(row.get('summary'))}</p>"
            f'<div class="meta">{esc(" · ".join(meta))}</div></div>'
        )
    parts.append("</div>")
    return "".join(parts)


def render_scanner_funnel(counts, scope_label):
    total = sum(counts.values())
    if total == 0:
        return ""
    resolved = counts.get("RESOLVED_BY_SOURCE_FACT", 0)
    excluded = counts.get("EXCLUDED_NON_ACTIVE_SOURCE_EVIDENCE", 0)
    human = counts.get("HUMAN_DECISION_REQUIRED", 0)
    other_open = sum(n for s, n in counts.items() if s in OPEN_SCANNER_STATUSES) - human
    other = total - resolved - excluded - human - other_open
    open_total = human + max(other_open, 0)
    open_color = "green" if open_total == 0 else "amber"

    def step(num, label, color=None):
        style = f' style="color:var(--{color})"' if color else ""
        return f'<div class="fstep"><div class="n"{style}>{num}</div><div class="t">{label}</div></div>'

    steps = [step(total, "Total kandidat"), '<div class="farrow">→</div>',
             step(resolved, "RESOLVED_BY_SOURCE_FACT", "green"),
             step(excluded, "EXCLUDED_NON_ACTIVE", None),
             step(human, "HUMAN_DECISION_REQUIRED", "amber" if human else None)]
    if other_open > 0:
        steps.append(step(other_open, "OPEN LAINNYA", "amber"))
    if other > 0:
        steps.append(step(other, "STATUS LAIN", None))
    return (
        '<div class="card"><h2>\U0001f50d Kandidat Scanner</h2>'
        f'<div class="desc">{esc(scope_label)} · status terbuka: <b style="color:var(--{open_color})">{open_total}</b></div>'
        f'<div class="funnel">{"".join(steps)}</div></div>'
    )


def render_timeline(session):
    meta = session["meta"]
    events = []
    started = meta.get("started_at")
    if started:
        events.append((started, "Sesi dimulai", ""))
    by_time = Counter(d.get("decided_at") for d in session["decisions"] if d.get("decided_at"))
    for ts, count in sorted(by_time.items()):
        if ts != started:
            events.append((ts, f"{count} keputusan tercatat", "v"))
    updated = meta.get("updated_at")
    status = meta.get("status")
    if updated and status:
        events.append((updated, f"Status akhir: {status}", "g" if status in DONE_SESSION_STATUSES else "a"))
    if not events:
        return ""
    items = "".join(
        f'<div class="tl-item {cls}"><div class="ts">{esc(ts)}</div>{esc(text)}</div>'
        for ts, text, cls in sorted(events, key=lambda e: e[0])
    )
    return f'<div class="card"><h2>\U0001f552 Timeline Sesi (UTC)</h2><div class="desc">&nbsp;</div><div class="tl">{items}</div></div>'


# ---------------------------------------------------------------- page renderers


def render_mode_block(e2e_code, session, doc_id_to_code, code_to_title, scanner_counts):
    meta = session["meta"]
    mode = meta.get("reconciliation_mode") or session["dir"].upper()
    mode_label = meta.get("reconciliation_mode_label") or ""
    status = meta.get("status") or "UNKNOWN"

    decisions = session["decisions"]
    interviews = session["interviews"]
    defects = session["defects"]
    confirmed = sum(1 for d in decisions if d.get("status") == "USER_CONFIRMED")
    answered = sum(1 for q in interviews if (q.get("status") or "").startswith("ANSWERED"))
    open_defects = sum(1 for d in defects if (d.get("status") or "").upper() == "OPEN")
    mode_scanner = scanner_counts.get(mode, Counter()) if scanner_counts else Counter()
    scanner_open = sum(n for s, n in mode_scanner.items() if s in OPEN_SCANNER_STATUSES)

    span = ""
    if meta.get("started_at"):
        span = f'{esc(meta["started_at"])} → {esc(meta.get("updated_at") or "?")} (UTC) · '
    versions = ""
    if meta.get("base_canonical_version"):
        versions = (
            f'base canonical <span class="mono">{esc(meta["base_canonical_version"])}</span>'
            f' → global <span class="mono">{esc(meta.get("base_global_version") or "UNRELEASED")}</span>'
        )

    kpis = "".join([
        kpi(len(decisions), f"Keputusan ({confirmed} USER_CONFIRMED)", "green" if confirmed == len(decisions) and decisions else "amber"),
        kpi(len(interviews), f"Pertanyaan interview ({answered} terjawab)", "blue"),
        kpi(open_defects, f"Defect OPEN (dari {len(defects)})", "amber" if open_defects else "green"),
        kpi(scanner_open, f"Kandidat scanner OPEN (mode ini)", "amber" if scanner_open else "green"),
    ])

    sections = [
        f'<div class="mode-block"><div class="mode-head">'
        f'<h2 style="font-size:18px">\U0001f4cb Sesi <span class="mono">{esc(meta.get("session_id") or "?")}</span> {status_badge(status)}</h2>'
        f'<div class="sub">Mode {badge("b-cyan", esc(mode) + (" — " + esc(mode_label) if mode_label else ""))}<br>{span}{versions}</div>'
        f"</div>",
        f'<div class="grid kpis">{kpis}</div>',
        render_version_bar(decisions),
        render_decisions(decisions, doc_id_to_code, code_to_title),
        '<div class="grid two">'
        + render_defects(defects, doc_id_to_code, code_to_title)
        + (render_scanner_funnel(mode_scanner, f"Register scanner untuk {esc(e2e_code)} mode {esc(mode)}") or '<div class="card"><h2>\U0001f50d Kandidat Scanner</h2><div class="desc">Tidak ada kandidat scanner tercatat untuk mode ini.</div></div>')
        + "</div>",
        '<div class="grid two">'
        + render_timeline(session)
        + (render_checklist(parse_checklist(session["review_md"])) or '<div class="card"><h2>\U0001f6a6 Kesiapan Baseline</h2><div class="desc">Tidak ada checklist Baseline Readiness di review-session.md.</div></div>')
        + "</div>",
        "</div>",
    ]
    return "".join(sections)


def render_e2e_page(e2e_code, domain, sessions, doc_id_to_code, code_to_title, scanner_counts, template, generated_at):
    title = (domain or {}).get("title") or (sessions[0]["meta"].get("e2e_title") if sessions else "") or e2e_code
    purpose = (domain or {}).get("purpose") or ""
    group = (domain or {}).get("domain_group") or ""

    head = (
        f"<header><h1>{esc(e2e_code)} — {esc(title)}</h1>"
        f'<div class="sub">{esc(purpose)}{(" · grup " + esc(group)) if group else ""}'
        f' · <a href="index.html">← kembali ke overview</a></div></header>'
    )
    if not sessions:
        body = head + (
            '<div class="card"><h2>Belum ada sesi rekonsiliasi tercatat</h2>'
            '<div class="desc">Workspace untuk E2E ini kosong — belum ada rekonsiliasi manusia yang tercatat. '
            "Output scanner saja bukan bukti progres rekonsiliasi.</div></div>"
        )
    else:
        body = head + "".join(
            render_mode_block(e2e_code, s, doc_id_to_code, code_to_title, (scanner_counts or {}).get("modes", {}))
            for s in sessions
        )

    page = template.replace("%%TITLE%%", f"{e2e_code} — Workspace Dashboard")
    page = page.replace("%%BODY%%", body)
    page = page.replace(
        "%%FOOTER%%",
        "Sumber: reconciliation/workspaces, canonical/automatic-reconciliation.json, "
        "canonical/manifest.json, e2e-inventory/domain-worklist.json",
    )
    page = page.replace("%%GENERATED_AT%%", generated_at)
    return page


def render_index(domains, sessions, scanner_by_e2e, template, generated_at, detail_codes):
    total_sessions = sum(len(v) for v in sessions.values())
    total_decisions = sum(len(s["decisions"]) for v in sessions.values() for s in v)
    open_defects = sum(
        1 for v in sessions.values() for s in v for d in s["defects"] if (d.get("status") or "").upper() == "OPEN"
    )
    scanner_open = sum(
        n for entry in scanner_by_e2e.values() for s, n in entry["ALL"].items() if s in OPEN_SCANNER_STATUSES
    )
    scanner_total = sum(sum(entry["ALL"].values()) for entry in scanner_by_e2e.values())

    kpis = "".join([
        kpi(len(domains), "E2E dalam worklist", "blue"),
        kpi(len(sessions), "E2E dengan sesi tercatat", "cyan"),
        kpi(total_sessions, "Sesi rekonsiliasi", None),
        kpi(total_decisions, "Keputusan tercatat", "green"),
        kpi(open_defects, "Defect OPEN", "amber" if open_defects else "green"),
        kpi(f"{scanner_open}/{scanner_total}", "Kandidat scanner OPEN / total", "amber" if scanner_open else "green"),
    ])

    cards = []
    for code in sorted(domains):
        domain = domains[code]
        e2e_sessions = sessions.get(code, [])
        entry = scanner_by_e2e.get(code, {"ALL": Counter()})
        s_open = sum(n for s, n in entry["ALL"].items() if s in OPEN_SCANNER_STATUSES)
        s_total = sum(entry["ALL"].values())

        mode_badges = " ".join(
            f'{esc(s["meta"].get("reconciliation_mode") or "?")}: {status_badge(s["meta"].get("status"))}'
            for s in e2e_sessions
        ) or '<span style="color:var(--mut)">belum ada sesi</span>'
        dec_count = sum(len(s["decisions"]) for s in e2e_sessions)
        def_open = sum(1 for s in e2e_sessions for d in s["defects"] if (d.get("status") or "").upper() == "OPEN")

        stats = (
            f"{mode_badges}<br>"
            f"Keputusan: <b>{dec_count}</b> · Defect OPEN: <b>{def_open}</b> · "
            f"Scanner OPEN: <b>{s_open}</b>/{s_total}"
        )
        if code in detail_codes:
            cards.append(
                f'<a class="e2e-card" href="workspace-{esc(code)}.html">'
                f"<h3>{esc(code)} — {esc(domain.get('title') or '')}</h3>"
                f'<div class="purpose">{esc(domain.get("purpose") or "")}</div>'
                f'<div class="stats">{stats}</div></a>'
            )
        else:
            cards.append(
                f'<div class="e2e-card plain"><h3>{esc(code)} — {esc(domain.get("title") or "")}</h3>'
                f'<div class="purpose">{esc(domain.get("purpose") or "")}</div>'
                f'<div class="stats">{stats}</div></div>'
            )

    body = (
        "<header><h1>\U0001f4ca Workspace Dashboard — Rekonsiliasi PRD</h1>"
        '<div class="sub">Overview seluruh E2E dari <span class="mono">reconciliation/workspaces</span> · '
        "klik kartu untuk detail per E2E</div></header>"
        f'<div class="grid kpis">{kpis}</div>'
        f'<div class="grid cards">{"".join(cards)}</div>'
    )
    page = template.replace("%%TITLE%%", "Workspace Dashboard — Rekonsiliasi PRD")
    page = page.replace("%%BODY%%", body)
    page = page.replace(
        "%%FOOTER%%",
        "Sumber: reconciliation/workspaces, canonical/automatic-reconciliation.json, "
        "canonical/manifest.json, e2e-inventory/domain-worklist.json",
    )
    page = page.replace("%%GENERATED_AT%%", generated_at)
    return page


# ---------------------------------------------------------------- main


def main():
    skill_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Generate HTML dashboard of reconciliation workspaces.")
    parser.add_argument("--repo", default="neurovi-prd", help="path to the document repository (default: neurovi-prd)")
    parser.add_argument("--e2e", help="render the detail page for this E2E code only")
    parser.add_argument("--out", default=str(skill_root / "output"), help="output directory (default: the skill's output/ folder)")
    args = parser.parse_args()

    repo = Path(args.repo)
    if not repo.is_dir():
        sys.exit(f"ERROR: document repository not found: {repo}")

    template_path = skill_root / "assets" / "dashboard-template.html"
    if not template_path.is_file():
        sys.exit(f"ERROR: template not found: {template_path}")
    template = template_path.read_text(encoding="utf-8")

    domains, doc_id_to_code, code_to_title, scanner_by_e2e, sessions = load_sources(repo)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    target_codes = sorted(sessions)
    if args.e2e:
        if args.e2e not in sessions and args.e2e not in domains:
            sys.exit(f"ERROR: unknown E2E code: {args.e2e}")
        target_codes = [args.e2e]

    written = []
    for code in target_codes:
        page = render_e2e_page(
            code, domains.get(code), sessions.get(code, []),
            doc_id_to_code, code_to_title, scanner_by_e2e.get(code), template, generated_at,
        )
        path = out_dir / f"workspace-{code}.html"
        path.write_text(page, encoding="utf-8")
        written.append(path)

    index = render_index(domains, sessions, scanner_by_e2e, template, generated_at, set(target_codes))
    index_path = out_dir / "index.html"
    index_path.write_text(index, encoding="utf-8")
    written.append(index_path)

    for path in written:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
