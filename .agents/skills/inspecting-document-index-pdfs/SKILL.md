---
name: inspecting-document-index-pdfs
description: Use when a contributor wants to inspect a single PDF as Markdown or Docling JSON, use the PDF inspection VS Code task, or tune PDF parsing settings in this repository.
---

# Inspect one PDF

Use the builder image and the existing wrapper. Inspection needs no database,
embeddings, full ingestion or publication.

## Steps

1. Read `AGENTS.md` and `docs/guide/inspecting-pdfs.md`. Confirm the user has
   authorized the source and storage location. Do not send source text or
   generated outputs to external tools or AI prompts.
2. Ensure the builder image exists; use `building-document-index-images` if not.
3. Copy `configs/docling.example.json` into ignored local storage, without
   overwriting an existing configuration:

   ```sh
   mkdir -p .local
   cp -n configs/docling.example.json .local/inspection-config.json
   sha256sum -- '/path/with spaces/example.pdf'
   ```

4. Enter that digest, the matching registered source and documented rights
   classification. The example deliberately has `may_process: false`. Only
   change it when processing is actually permitted; selecting an adapter does
   not grant permission. Missing authorization is a blocker, not a test failure
   to bypass. Keep supported parser settings in the `docling` object.
5. Choose a fresh output directory and run from the repository root:

   ```sh
   bash scripts/inspect-pdf '/path/with spaces/example.pdf' \
     .local/inspection-config.json baua .local/inspection/example-01
   ```

   Replace `baua` with the matching `dguv` or `eur-lex` source when appropriate.
   VS Code equivalent: **Terminal → Run Task → Document Index: Inspect PDF**.
6. Require successful exit and all four outputs: `document.md`, `document.json`,
   `configuration.json`, `report.json`. Review locally; humans can open Markdown
   with **Markdown: Open Preview to the Side**. Report failures and warnings
   without exposing document text.

## Common mistakes

| Situation | Correct action |
|---|---|
| Existing output directory | Choose a new one; preserve user work. |
| Missing rights, wrong hash or source | Correct the authorized configuration; never disable checks. |
| Non-PDF input or OCR requested | PDF only; OCR is unsupported by prepared models. |
| Comparing parser experiments | Use separate outputs; do not create destinations concurrently. |

Input/configuration mounts are read-only; the wrapper creates writable temporary
output with host ownership. Keep generated text in permitted ignored local
storage. Never commit it or attach it to public CI/issues.
