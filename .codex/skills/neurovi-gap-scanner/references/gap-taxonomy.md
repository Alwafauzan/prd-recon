# Neurovi Two-Scanner Taxonomy

## Evidence Classes

- `SOURCE_EXPLICIT_GAP`: source-explicit conflict or unresolved statement.
- `USER_CONFIRMED_GAP`: recorded semantic gap or unresolved user decision.
- `MECHANICAL_GAP_CANDIDATE`: inferred from inventory checks, missing context
  families, or incomplete indexed evidence.
- `MECHANICAL_STRUCTURE_EVIDENCE`: a heading or literal term mechanically
  indicates that a context family is present.

Only source-explicit and user-confirmed findings may be described as known gaps.
Mechanical findings require source review.

## Scanner 1: Main Business Flow

### Scope

- `trigger_input`
- `sequence`
- `handoff`
- `output`
- `status_transition`
- source-explicit `ENTRY_POINT_TO`, `PRODUCES`, `HANDOFF_TO`, and `ACTIVATES`
  relations
- cross-domain continuation and source-explicit flow conflicts

### Finding Types

- `TRIGGER_INPUT_REVIEW_REQUIRED`
- `SEQUENCE_REVIEW_REQUIRED`
- `HANDOFF_REVIEW_REQUIRED`
- `OUTPUT_REVIEW_REQUIRED`
- `STATUS_TRANSITION_REVIEW_REQUIRED`
- `UNDEFINED_FLOW_HANDOFF_CONTEXT`
- `CONFLICTING_FLOW_CONTEXT`

`REFERENCES` rows without trigger, input, output, status, or condition evidence
are supporting context. Do not report every unverified reference as a broken
handoff.

### Excluded Detail Families

- `OUT_OF_SCOPE`
- `ALTERNATE_FLOW`
- `ERROR_EXCEPTION`
- `CASES_CONDITIONS`
- `BUSINESS_RULES`
- `VALIDATION_BEHAVIOR`
- `ACCEPTANCE_CRITERIA`

## Scanner 2: Detailed Business Cases

### Context Families

- `OUT_OF_SCOPE`: excluded cases and feature boundaries.
- `ALTERNATE_FLOW`: non-primary but valid paths.
- `ERROR_EXCEPTION`: failures, exceptions, and recovery behavior.
- `CASES_CONDITIONS`: scenario branches, preconditions, and case conditions.
- `BUSINESS_RULES`: business constraints and decisions.
- `VALIDATION_BEHAVIOR`: required values, invalid conditions, and validation response.
- `ACCEPTANCE_CRITERIA`: observable completion or acceptance conditions.

### Statuses

- `SECTION_PRESENT`: matching context appears under a detected heading.
- `CONTEXT_PRESENT_UNSTRUCTURED`: matching literal terms exist without a detected
  standard heading.
- `CONTEXT_GAP_CANDIDATE`: neither a matching heading nor the configured literal
  context terms were detected.
- `EXPLICIT_GAP_MARKER_CANDIDATE`: source text contains an unresolved marker.

A missing family is a structural/context candidate. It does not prove that the
business behavior is absent, because the PRD may express it using other wording.

### Excluded Main-Flow Families

- `PURPOSE_BACKGROUND`
- `SCOPE`
- `ACTORS_STAKEHOLDERS`
- `TRIGGER_PRECONDITIONS`
- `MAIN_FLOW`
- `LOGICAL_DATA_FLOW`
- `STATUS_LIFECYCLE`
- `DEPENDENCIES_INTEGRATION`

## Severity

- `HIGH`: source-explicit or user-confirmed conflict affecting flow, status, data,
  validation, or patient/service continuation.
- `MEDIUM`: mechanical missing handoff, scenario, rule, validation, error, or
  acceptance context requiring review.
- `LOW`: nonstandard structure or weak lexical evidence.

Severity prioritizes review only and never authorizes a document change.

## Resolution Boundary

The scanners identify and map. `$neurovi-prd-reconciler` interviews the user,
correlates answers, recommends options, records decisions, and changes derived
baselines only after approval.
