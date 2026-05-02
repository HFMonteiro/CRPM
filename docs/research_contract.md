# CRPM Research Contract

## First-Event Direct Workflow Rule

CRPM production discovery, DFG, conformance, variant, and operational-flow views use a first-event direct workflow gate. The default cohort is not an arbitrary incident-anchor cohort. A case enters the production workflow when its first recorded event matches the selected first-event gate.

This rule keeps the first discovery analysis aligned with the observed screening pathway as recorded in the event log. It prevents a secondary anchor choice from silently changing the denominator, trace shape, and directly-follows structure used for the primary workflow.

## Valid Exceptions

Explicit anchor semantics are allowed only as secondary analysis:

- Follow-up horizon studies that censor each case after a fixed observation window.
- Cohort comparability checks where the same first-event gate is preserved and the horizon is varied.
- Sensitivity analysis that is labelled as secondary and not presented as the primary production discovery mode.

## Implementation Contract

- `workflow_cohort_policy` defaults to `first_event_direct`.
- The UI labels the production control as `First-event workflow gate`.
- Follow-up horizon mode requires a selected first-event gate.
- Date filters may restrict the cohort or clip events, but they must not replace the first-event workflow gate.
- Conformance workspaces use the same evaluation log used for conformance metrics, including train/test runs.
- Run metadata is privacy-safe: source type, source kind, size, validation status, and a redacted display name may be shown; local paths, uploaded filenames, raw case IDs, and raw records must not be displayed in error messages.

## Non-Clinical Scope

CRPM is a research and operational monitoring workbench. It is not clinical decision support, and its outputs require local governance review before operational action.

## Security References

- OWASP Input Validation Cheat Sheet
- OWASP XSS Prevention Cheat Sheet
- OWASP Logging Cheat Sheet
- W3C/WAI WCAG contrast and accessibility guidance
