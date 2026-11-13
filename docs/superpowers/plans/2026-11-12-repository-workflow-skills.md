# Repository Workflow Skills Implementation Plan

> **For agentic workers:** Use executing-plans to implement this documentation plan. Track progress below.

**Goal:** Make repository workflows easy to find for people and coding assistants.
**Architecture:** Human quick start in README; task routing in AGENTS; four thin reference skills in `.agents/skills/`, linked to detailed guides.
**Tech Stack:** Markdown and Agent Skills YAML frontmatter.
**Spec:** `docs/superpowers/specs/2026-11-12-repository-workflow-skills-design.md`

## Constraints and review focus

Preserve existing rights, storage and publication rules. Do not touch unrelated
CONTRIBUTING.md edits. Commands must distinguish image builds from data builds,
quote PDF paths, require fresh outputs and keep build/consumer storage separate.
Skill links must work without assuming automatic harness discovery.

## Checklist

- [x] Baseline discovery scenario: reviewer found no local skills or routing for the four tasks.
- [x] Add each workflow skill and verify its read-only application scenario before proceeding to the next.
- [x] Rewrite README with purpose, prerequisites, PDF quick start, VS Code tasks and guide/skill links.
- [x] Add AGENTS task-to-skill routing without changing its policy sections.
- [x] Validate frontmatter, Markdown links, documented commands and whitespace; report checks honestly.

Skill validation checks: names match directories, descriptions start with
"Use when", commands match scripts/tasks, and a reader can identify required
inputs, safe execution and completion evidence without running operations.
No application tests or real model/image builds are needed for documentation-only changes.

## Verification record

Read-only scenario checks passed for each skill in sequence: image-only build
without credentials; quoted PDF path with missing permission/existing output;
signed release with container input paths and isolated experiment storage; and
private retrieval readiness, explicit updates and non-publishing verification.
The image scenario exposed inherited `REGISTRY` ambiguity; its command now
clears `REGISTRY` and sets `PUSH=0`, and the next check confirmed the correction.

Static validation passed for all four frontmatters, README/AGENTS skill links,
local Markdown links, referenced repository paths, exact VS Code task names,
and unchanged AGENTS safety/engineering sections. `git diff --check` passed.
No PDFs, private keys, Docker builds or operational services were accessed.
Existing CONTRIBUTING.md edits were left untouched. No commit or push requested.
