# Reconciliation Interview - <E2E Code>

## Interview Control

| Field | Value |
|---|---|
| Session ID | `<REC_ID>` |
| E2E | `<E2E_CODE>` |
| Base global version | `<VERSION_OR_UNRELEASED>` |
| Interview status | `IN_PROGRESS` |

The user may answer, modify, skip, defer, or state that an answer is unknown.

## Current Question

| Field | Value |
|---|---|
| Question ID | `<QUESTION_ID>` |
| Related defects | `<DEFECT_IDS>` |
| Affected documents | `<DOCUMENT_IDS>` |
| Flow/handoff | `<FLOW_OR_HANDOFF>` |
| Why this matters | `<FLOW_OR_DATA_INTEGRITY_REASON>` |
| Question | `<NEUTRAL_QUESTION>` |

Available responses: `ANSWER`, `SKIP`, `DEFER`, `UNKNOWN`.

## Answer

| User response | Evidence/reference supplied | Status |
|---|---|---|
|  |  | `PENDING` |

## Related-Answer Correlation

> A correlation is a proposal until the user confirms it.

| Source answer | Target question/gap | Correlation basis | Supporting evidence | Contradicting evidence | Status |
|---|---|---|---|---|---|
|  |  |  |  |  | `CANDIDATE` |

## Gap Closure Options

| Option | Functional resolution | Flow continuity | Logical data integrity | Scope impact | Evidence | Tradeoff |
|---|---|---|---|---|---|---|
| A |  |  |  |  |  |  |
| B |  |  |  |  |  |  |
| Keep open | Preserve the gap pending more evidence |  |  | `NONE` |  |  |

Recommended option: `PROPOSED_RESOLUTION: <OPTION>`

Reason: `<EVIDENCE_BACKED_REASON>`

User decision: `CONFIRM`, `MODIFY`, `REJECT`, `SKIP`, or `DEFER`.

## Unresolved Questions

| Question ID | Question | Status | New evidence available | Revisit condition |
|---|---|---|---|---|
|  |  |  |  |  |
