# Global Git Versioning Policy

## Objective

Use one global Git version to answer two questions reliably:

1. Which exact repository state was approved?
2. Which documents changed, and what changed, since the previous approved version?

Use annotated tags with this format:

```text
v<major>.<minor>.<patch>
```

Start the first approved repository baseline at `v0.0.1`. Do not assign independent release versions to individual PRDs or E2Es. A document keeps a stable document code, provenance, and checksum.

## Release Artifacts

Every approved version produces:

```text
reconciliation/releases/v0.0.2/
├── manifest.json
└── changes.md
```

`manifest.json` is machine-readable. It contains the complete active canonical inventory plus a structured list of changed documents.

`changes.md` is human-readable. It explains which PRDs, E2E contexts, relationships, decisions, and defects changed from the previous version.

Do not copy full documents into the release directory. Git stores their historical content.

## Version Classes

- `PATCH`: approved format, naming, provenance, link, index, or metadata changes without functional meaning changes.
- `MINOR`: approved source-backed context, relationship, case, condition, logical data trace, or canonical document additions without changing primary scope.
- `MAJOR`: formal user-approved changes to scope, business behavior, process boundary, data ownership, identifier semantics, or lifecycle.

During the pre-1.0 reconciliation phase, versions may progress as `v0.0.1`, `v0.0.2`, and so on when the user wants simple controlled checkpoints. The release report must still record the applicable change class. The user approves the version number.

## Change Types

Classify every changed artifact as one of:

- `ADDED`
- `MODIFIED`
- `RENAMED`
- `REMOVED`
- `RELATION_CHANGED`
- `FORMAT_ONLY`
- `DECISION_ONLY`

For PRDs, include changed sections when they can be located mechanically or identified by a confirmed decision. Do not claim a semantic change based only on model interpretation.

## Sources of the Change Report

Build the release report from two evidence classes:

1. Git diff supplies file status, paths, rename detection, and exact textual differences.
2. Confirmed decision and defect registers supply the approved semantic reason, affected scope, and resolution.

If Git shows a changed file but no source or decision explains the semantic change, mark it `UNEXPLAINED_CHANGE` and block baseline approval.

Use these commands for inspection:

```bash
git diff --find-renames --name-status v0.0.1..v0.0.2
git diff --word-diff v0.0.1..v0.0.2 -- <document-path>
git show v0.0.1:<document-path>
```

Use `scripts/version_diff.py` for a normalized file-level report.

## What Does Not Create a Version

Do not create a release tag for:

- mechanical candidate regeneration;
- unconfirmed document or E2E selection;
- format and defect scans;
- open decision questions;
- working reconciliation sessions;
- references that have not changed the approved canonical baseline.

Normal working commits may exist but remain `UNRELEASED`.

## Baseline Gate

Before creating a version:

1. Confirm every baseline change has source evidence or a `USER_CONFIRMED` decision.
2. Generate the proposed `manifest.json` and `changes.md` against the previous tag.
3. Block release when any changed canonical file is marked `UNEXPLAINED_CHANGE`.
4. Keep unresolved defects visible without mixing them into approved requirements.
5. Regenerate derived indexes and Graphify navigation.
6. From the tools repository, run `python3 scripts/build_structure.py validate --source neurovi-prd/source/original --target neurovi-prd`.
7. Show the version, changed documents, section summaries, decisions, and open defects to the user.
8. Obtain explicit `BASELINE_APPROVAL` for the complete global version.
9. Commit the approved release artifacts and repository state.
10. Create an annotated tag pointing to that commit.

Do not create a commit or tag merely because an individual document decision was approved.

## Tag and Commit Integrity

- Never reuse a version number.
- Never move, delete, replace, or force-update an approved tag.
- If a release is wrong, create a later version that supersedes it.
- Do not store the release commit SHA inside a file committed by that same release; that creates a circular hash dependency.
- Resolve the release commit from the tag with `git rev-list -n 1 <version>`.
- Ensure the annotated tag message references the baseline decision ID.

## Human Change Report

For every changed document, `changes.md` must show:

- document code and title;
- old and new path when renamed;
- change type;
- changed sections or relationship fields;
- concise approved change description;
- source references;
- decision IDs;
- affected E2Es;
- functional scope impact: `NONE`, `CONTEXT_ONLY`, or `FORMAL_CHANGE`;
- related resolved and open defects.

The initial `v0.0.1` report treats every canonical document as `ADDED` and records that no previous version exists.

## Consumer Lock

Designer, developer, and QA must consume one global version:

```yaml
repository_version: "v0.0.2"
release_commit: "resolved with git rev-list -n 1 v0.0.2"
release_manifest: "reconciliation/releases/v0.0.2/manifest.json"
```

Do not mix documents from different tags. Mark downstream role artifacts stale when a newer version changes one of their locked PRDs, E2E contexts, relationships, or decisions.
