# Repository Rules

- Treat `neurovi-prd/` as a Git submodule and the document source truth.
- Never edit files under `neurovi-prd/source/original/`.
- Preserve source facts exactly; do not correct, remove, or add document claims.
- Keep application, scripts, skills, and deployment files in this tools repository.
- Keep document baselines, reconciliation artifacts, and global document tags in the submodule repository.
- Run `python3 scripts/build_structure.py validate --source neurovi-prd/source/original --target neurovi-prd` after regeneration.

## Repository Skills

- For controlled E2E PRD reconciliation, read and follow `.codex/skills/neurovi-prd-reconciler/SKILL.md` completely.
- For read-only E2E and PRD gap scanning, read and follow `.codex/skills/neurovi-gap-scanner/SKILL.md` completely.
- For displaying immutable original PRDs, read and follow `.codex/skills/neurovi-show-prd/SKILL.md` completely.
- For displaying the read-only E2E inventory, read and follow `.codex/skills/neurovi-show-e2e/SKILL.md` completely.
