# Standard-Family-Agnostic Real-PDF Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace BAuA-specific real-PDF tests with one opt-in annotation-driven harness that runs the registered adapter for each private PDF case.

**Architecture:** Discover annotation JSON beneath `web-app-raw-data/raw_data_test/` only when `RUN_REAL_PDF_TESTS=1` is set. A generic support module validates each case and uses an explicit registry to construct BAuA, DGUV, or EUR-Lex adapters. Shared assertions compare selected Docling properties and annotated adapter records/sections; family differences stay in registry entries and JSON options.

**Tech Stack:** Python, pytest, standard-library JSON/path/hash tools, Docling, existing `SourceAdapter` implementations.

**Spec:** `docs/superpowers/specs/2026-11-17-docling-real-pdf-tests-design.md`

## Global Constraints

- Real PDFs and source-derived excerpts remain in the private raw-data submodule; real-PDF tests are never CI inputs.
- Real-PDF tests run only with `RUN_REAL_PDF_TESTS=1`; ordinary tests do not read private annotations or PDFs.
- Parse-derived TRGS-401 expectations remain `draft`; no adapter or Docling assertion may use them as truth.
- Do not compare full Docling serialization or incidental IDs; use selected annotated text, order, and physical page provenance.
- No LLM participates in pass/fail decisions; OCR, image recognition, and image descriptions remain out of scope.
- Keep changes made by this implementation unstaged and uncommitted as previously requested.

## Review Focus

1. Draft or inconsistent annotation state — explicit validation test fails before extraction; parsing/adapter tests skip before reading the PDF.
2. Missing source path, hash mismatch, invalid adapter key/options, or incompatible staged filename — fail clearly; never silently skip an opted-in case.
3. TOC/printed page mistaken for physical page — Docling provenance is matched only against `pdf_page`.
4. Selected versus exhaustive expectations — selected records/sections are ordered subsequences; complete coverage requires exact equality; empty lists cannot silently mean complete coverage.
5. Adapter with multiple records or no sections — expected record/section coverage and anchor assignments remain explicit and testable.

---

### Task 1: Build generic annotation discovery and adapter registry

**Files:**
- Create: `core/tests/pipeline/real_pdf_test_support.py`
- Create: `core/tests/pipeline/test_real_pdf_test_support.py`

**Interfaces:**
- `AnnotationCase`: frozen record with `annotation_path: Path`, `document: dict`, and resolved `pdf_path: Path`.
- `discover_annotation_cases(raw_data_root: Path) -> list[AnnotationCase]`: recursively loads `extraction-test-annotations.json`, validates source paths stay under the root, and returns cases sorted by `test_id`.
- `AdapterRegistration`: adapter class, adapter module, and required/allowed option names.
- `ADAPTER_REGISTRY`: explicit mappings for `baua`, `dguv`, and `eur_lex`.
- `create_adapter(document: dict, directory: Path, source_id: UUID) -> SourceAdapter`: constructs only registered adapters and rejects missing/unknown constructor options.
- `assert_section_boundary_assignment(...)`: generic `RawSection` assertion helper.

- [x] Write tests for recursive annotation discovery, path traversal rejection, registered adapter construction/options, unknown-family failure, and exclusive section-boundary assignment.
- [x] Run the support test module and confirm the missing support interfaces fail.
- [x] Implement the data class, discovery, registry, factory, and generic boundary helper.
- [x] Run the support test module and confirm it passes without opening real PDFs or requiring the opt-in flag.

### Task 2: Version the family-neutral annotation contract

**Files:**
- Modify: `web-app-raw-data/extraction-test-template.json`
- Modify: `web-app-raw-data/raw_data_test/BAuA/extraction-test-annotations.json`
- Create: `core/tests/pipeline/test_real_pdf_annotations.py`

**Interfaces:**
- Schema version `2`; each document has `adapter.family`, `adapter.input_filename`, `adapter.options`, `adapter.record_coverage`, and `adapter.records`.
- Each expected adapter record annotates `sequence`, raw designation/issuer/title/edition, full-text presence, section coverage/headings, and reference coverage/references.
- Each text anchor uses physical/printed page fields plus nullable `expected_record_sequence` and `expected_section_sequence`; section sequence is the one-based position in the annotated adapter-section list.
- The BAuA/TRGS-401 data gains a `baua` adapter annotation and adapter output expectations but stays `draft`, keeps PDF hash/page values null, and remains explicitly parse-derived.

- [x] Write opt-in schema tests that discover all annotation files, compare document/adapter/record/section/anchor/boundary keys to the template, validate coverage enums and cross-references, and permit `draft` → `verified` only when `manual_review.verified` agrees.
- [x] Run `RUN_REAL_PDF_TESTS=1 uv run --group dev --all-packages --all-extras python -m pytest core/tests/pipeline/test_real_pdf_annotations.py -q`; confirm the v1 annotation data fails the v2 contract.
- [x] Update the template and current BAuA draft to schema v2 without marking it verified or inventing physical positions/hash.
- [x] Re-run the opt-in annotation test and confirm it passes; run without opt-in and confirm private-data tests skip.

### Task 3: Replace family-specific real-PDF checks with the generic runner

**Files:**
- Create: `core/tests/pipeline/test_real_pdf_extraction.py`
- Delete: `core/tests/pipeline/test_baua_real_docling.py`
- Delete: `core/tests/pipeline/test_baua_annotation_data.py`
- Modify: `core/tests/pipeline/real_pdf_test_support.py`

**Interfaces:**
- `pytest_generate_tests` parameterizes from discovered annotation cases only under explicit opt-in; default collection performs no private-data reads.
- A session/module-scoped `parsed_document(case)` checks verified status, source presence, SHA-256 and required physical pages before calling shared `extract_document()` once per PDF.
- Generic Docling assertions compare annotated headings/anchors by exact text, item order, and `pdf_page` provenance.
- Generic adapter assertions stage the PDF under `adapter.input_filename`, patch only the registered adapter module’s extraction function to reuse the parsed `DoclingDocument`, invoke `fetch()`, and compare selected/complete record, section, reference, and anchor expectations.

- [x] Write generic tests for: clear explicit draft guard; Docling heading/anchor text, order and page matching; adapter record/section/reference outputs; and anchor assignment/leakage checks.
- [x] Run the explicit real-PDF module against the current draft and confirm the guard fails before extraction while Docling/adapter checks skip.
- [x] Implement opt-in case parameterization, source/hash/status checks, Docling assertions, and registry-driven adapter assertions.
- [x] Add regression checks that selected adapter records/references preserve annotated order and duplicate counts.
- [x] Reject an adapter anchor assignment when neither full text nor an annotated section makes the assignment observable.
- [x] Run the generic module without opt-in and confirm all private cases skip; run annotation-shape checks with opt-in and confirm they pass.
- [x] Keep the validated extraction path unexecuted until the user verifies TRGS-401 against its PDF and prepares offline Docling artifacts.

### Task 4: Remove source-derived canaries from synthetic BAuA test support

**Files:**
- Modify: `core/tests/pipeline/test_baua_adapter.py`
- Delete: `core/tests/pipeline/baua_test_support.py`
- Modify: `docs/guide/extraction-map.md`

- [x] Replace `BAUA_REAL_DOCUMENT_HEADING_CANARIES` inputs with invented synthetic designation/title/heading values and assert the generated PDF adapter path directly.
- [x] Remove the family-specific support module once only the generic boundary helper remains in `real_pdf_test_support.py`.
- [x] Run BAuA adapter tests and confirm synthetic coverage still passes without real-source heading strings.
- [x] Update the extraction inventory statement so it no longer claims public real-document heading canaries are retained.

### Task 5: Update user-facing and architecture documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/guide/verification.md`
- Modify: `docs/adr/README.md`
- Modify: `web-app-raw-data/EXTRACTION_TESTS.md`
- Modify: `docs/superpowers/specs/2026-11-17-docling-real-pdf-tests-design.md`
- Modify: this plan

- [x] Replace README references to the removed Markdown annotation sheet and “to be extended” text with the JSON-driven family-neutral workflow.
- [x] Document recursive discovery, family registry, per-case adapter configuration, coverage modes, local command, draft status, and no-CI boundary in the private raw-data guide.
- [x] Update verification guidance/status to generic test names and accurately state that current TRGS-401 remains draft and the validated path has not run.
- [x] Add a concise accepted ADR entry describing the test harness as data-driven with an explicit registry and private annotations.
- [x] Search documentation for stale BAuA-only test names, old Markdown annotation paths, and claims about source-derived canaries; update all in-scope references.

### Task 6: Final verification

- [x] Run focused annotation/support/adapter/Docling regression tests; report warnings and environment-limited checks honestly.
- [x] Run the full default suite and record any unavailable embedding-model failures without claiming a full pass.
- [x] Run `git diff --check` and verify changes from this implementation are not staged or committed.
- [x] Confirm unrelated user-owned documentation and private PDFs remain untouched.

### Task 7: Separate verification procedure from run evidence

**Files:**
- Move: `docs/guide/verification.md` → `docs/verification-record.md`
- Create: `docs/guide/verification.md`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/superpowers/specs/2026-11-17-docling-real-pdf-tests-design.md`
- Modify: this plan

**Interfaces:**
- `docs/guide/verification.md` is the stable procedure: prerequisites, commands,
  safety boundary, and how to report unavailable checks.
- `docs/verification-record.md` preserves run-specific evidence and results.

- [x] Move the existing extraction verification record without losing historical evidence; adjust its relative links.
- [x] Write procedural verification guidance using the repository's existing model-preparation, test, image, and local real-PDF commands.
- [x] Link separately to the procedure and the current evidence record from README; link CONTRIBUTING's test instructions to the procedure.
- [x] Update the design/spec and plan wording so run-specific status is not assigned to a guide.
- [x] Verify links and search for stale references to the old report role; run `git diff --check`.

## Execution notes

- Execute inline in the existing worktree; do not stage or commit.
- The TRGS-401 PDF exists locally but was not read or parsed; the draft guard ran first. No inspection or page annotation is authorized by this plan.
- Preserve the unrelated user-owned `docs/guide/ingestion-data-flow.md` and `docs/guide/ingestion-data-model.md` files.
