# Neurovi Document Reconciliator

Repository tools untuk inventarisasi, scanning gap, rekonsiliasi PRD terkontrol,
versioning global dokumen, serta adapter Discord. Source truth dokumen berada di
repository `neurovi-prd`, yang dipasang sebagai Git submodule pada
`./neurovi-prd`.

## Struktur

- `.codex/skills/`: skill rekonsiliasi, scanner, dan penampil dokumen.
- `scripts/`: generator dan validator deterministik repository dokumen.
- `src/`: package command service dan Discord adapter.
- `tests/`: test capability, help, dan konfigurasi.
- `neurovi-prd/`: submodule repository dokumen PRD.

## Setup

```bash
git clone --recurse-submodules <tools-repository-url>
python3 -m venv .venv
.venv/bin/pip install ".[discord]"
.venv/bin/neurovi-doc-reconciliator health --deep
```

Validasi source document repository:

```bash
python3 scripts/build_structure.py validate \
  --source neurovi-prd/source/original \
  --target neurovi-prd
```

Server Discord dan kontrak writable agent gateway dijelaskan di
`docs/server-deployment.md`.
