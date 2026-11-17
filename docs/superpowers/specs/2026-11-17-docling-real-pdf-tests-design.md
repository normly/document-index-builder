# Standard-family-agnostic real-PDF extraction tests

## Intent

Provide one opt-in, deterministic test harness for authorized real PDFs from
any supported standard family. It reads per-document expected values from JSON
stored beside the PDFs in the private `web-app-raw-data` submodule, runs shared
Docling extraction and the adapter selected for each annotation, and compares
only manually annotated outputs. The test oracle is explicit JSON, never an LLM.

## Proposed structure

- `web-app-raw-data/EXTRACTION_TESTS.md`: shared annotation rules, family
  registration/schema guidance, position conventions, and local-only run
  instructions.
- `web-app-raw-data/extraction-test-template.json`: a family-neutral schema
  template.
- `web-app-raw-data/raw_data_test/<family>/extraction-test-annotations.json`:
  per-family collections of document records. The existing BAuA/TRGS-401 entry
  remains a draft until a human checks it against the PDF.
- `core/tests/pipeline/real_pdf_test_support.py`: annotation discovery, schema
  and hash checks, an explicit adapter registry, temporary input staging, and
  shared assertion helpers.
- `core/tests/pipeline/test_real_pdf_annotations.py` and
  `test_real_pdf_extraction.py`: family-neutral tests, parameterized from all
  discovered annotation records only after `RUN_REAL_PDF_TESTS=1` is set.
- `docs/guide/verification.md`: repeatable verification procedure, prerequisites,
  and commands. It contains no run-specific results.
- `docs/verification-record.md`: implementation/run-specific evidence, results,
  deferred findings, and external checks, linked from the guide and README.
- `README.md`: links separately to the procedure and the current evidence record.

Each document record has an `adapter.family`, family-specific `adapter.options`,
an adapter-compatible temporary input filename, selected/complete coverage
declarations, expected adapter records and sections, Docling headings, and
short text anchors. The registry maps a family key to the existing adapter
class, its module (for reusing the parsed Docling document), and accepted
constructor options. Adding an annotation for a registered family requires no
new family-specific test module. Adding a new adapter requires one registry
entry and its constructor options, not duplicated assertions.

The JSON records annotation state. Parse-derived expectations stay `draft`; an
explicit run reports the pending human-review guard and does not use them as an
oracle. Missing physical page positions remain null. Printed page references
are never substituted for physical PDF provenance.

## Test contract

- Discover `extraction-test-annotations.json` files recursively below
  `raw_data_test/`, but do not read private annotations or PDFs unless the
  explicit local opt-in is enabled.
- Run the shared `extract_document()` once per source PDF. Compare annotated
  Docling item text, item order, and physical page provenance; do not compare a
  whole serialized document or incidental IDs.
- Run the registered adapter over that same `DoclingDocument` and compare
  annotated `RawRecord` identity/metadata, optional references, section
  headings/order, and anchor-to-record/section assignments. Coverage fields
  distinguish selected expectations from an exhaustive record/section list;
  this permits adapters such as EUR-Lex to yield many records and no sections.
- Keep family-specific differences in the adapter registry and JSON options,
  not in the test functions. No family is hard-coded into the discovery or
  assertion loops.
- Real-PDF tests are local-only, explicitly enabled, and never CI inputs.
  Ordinary CI remains synthetic-only. No LLM participates in pass/fail.
- Keep synthetic tests for algorithmic edge cases, but use invented fixture
  names/headings rather than real-source canary strings.

## Approaches considered

1. **One real-PDF test module per family:** rejected because discovery,
   annotation interpretation, Docling checks, and section assertions would
   drift or be duplicated as families are added.
2. **Dynamic plugin auto-discovery of adapters:** rejected for this small fixed
   set because implicit imports and capability conventions add indirection
   without removing the need to describe constructor options and expectations.
3. **Shared data-driven runner with an explicit adapter registry (chosen):**
   one set of assertions handles all families, while a narrow registry captures
   constructor differences and the JSON remains the authoritative expected
   value source. This is the approach requested by the user.

## Constraints and known limits

- PDFs and source-derived excerpts remain only in the private raw-data
  submodule; real-PDF tests are not CI inputs or public artifacts.
- Keep the JSON schema and detailed handling rules authoritative in the private
  raw-data submodule. Builder guidance explains the procedure; the verification
  record captures the outcome of a particular run.
- The current TRGS-401 values came from an existing inspection parse. They are
  not independent ground truth and must remain `draft` until human PDF review.
- `RawSection` has no source-page or coordinate field, so page-position checks
  apply to Docling items; adapter checks focus on records and section assignment.
- Text anchors stay short. OCR, image recognition, and image descriptions are
  outside this test contract.
- An annotation file can cover only registered adapter families. Adding an
  unsupported family fails with a clear registry error rather than silently
  skipping it.

## Approval state

The user requested execution of the standard-family-agnostic design on
2026-11-17: generic annotation discovery, shared deterministic checks, a small
adapter registry, updated documentation, and a separation between repeatable
verification guidance and run-specific evidence. Keep all changes uncommitted
as previously requested.
