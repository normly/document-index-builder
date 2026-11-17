# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from normly_core.pipeline.adapters import baua, dguv, eur_lex
from normly_core.pipeline.adapters.baua import BauaAdapter
from normly_core.pipeline.adapters.dguv import DguvAdapter
from normly_core.pipeline.adapters.eur_lex import EurLexAdapter
from normly_core.pipeline.domain import RawSection, SourceAdapter


ANNOTATION_FILENAME = "extraction-test-annotations.json"


@dataclass(frozen=True)
class AnnotationCase:
    annotation_path: Path
    document: dict[str, Any]
    pdf_path: Path


@dataclass(frozen=True)
class AdapterRegistration:
    adapter_type: type[SourceAdapter]
    module: ModuleType
    required_options: frozenset[str] = frozenset()
    allowed_options: frozenset[str] = frozenset()


ADAPTER_REGISTRY: dict[str, AdapterRegistration] = {
    "baua": AdapterRegistration(BauaAdapter, baua),
    "dguv": AdapterRegistration(DguvAdapter, dguv),
    "eur_lex": AdapterRegistration(
        EurLexAdapter,
        eur_lex,
        required_options=frozenset({"legislation_reference"}),
        allowed_options=frozenset({"legislation_reference"}),
    ),
}


def discover_annotation_cases(raw_data_root: Path) -> list[AnnotationCase]:
    """Load annotation records beneath the private raw-data root.

    This is structural discovery only. The opt-in tests separately validate
    annotation fields and require verified status before reading a source PDF.
    """
    root = raw_data_root.resolve()
    if not root.is_dir():
        raise ValueError(f"raw-data root does not exist or is not a directory: {root}")
    test_root = root / "raw_data_test"
    if not test_root.is_dir():
        return []

    cases: list[AnnotationCase] = []
    seen_test_ids: set[str] = set()
    for annotation_path in sorted(test_root.rglob(ANNOTATION_FILENAME)):
        resolved_annotation_path = annotation_path.resolve()
        if not resolved_annotation_path.is_relative_to(test_root):
            raise ValueError(
                f"annotation file must remain inside raw_data_test: {annotation_path}"
            )
        try:
            payload = json.loads(resolved_annotation_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"cannot read annotation file {annotation_path}: {error}") from error

        if not isinstance(payload, dict) or not isinstance(payload.get("documents"), list):
            raise ValueError(f"annotation file must contain a documents array: {annotation_path}")

        for document in payload["documents"]:
            if not isinstance(document, dict):
                raise ValueError(f"annotation documents must be objects: {annotation_path}")
            test_id = document.get("test_id")
            source_pdf = document.get("source_pdf")
            if not isinstance(test_id, str) or not test_id.strip():
                raise ValueError(f"annotation document has no stable test_id: {annotation_path}")
            if test_id in seen_test_ids:
                raise ValueError(f"duplicate extraction test_id: {test_id}")
            if not isinstance(source_pdf, str) or not source_pdf.strip():
                raise ValueError(f"annotation {test_id!r} has no source_pdf path")

            pdf_path = (root / source_pdf).resolve()
            if not pdf_path.is_relative_to(test_root):
                raise ValueError(
                    f"source PDF for {test_id!r} must remain inside raw_data_test"
                )
            if pdf_path.suffix.lower() != ".pdf":
                raise ValueError(f"source PDF for {test_id!r} must have a .pdf suffix")

            seen_test_ids.add(test_id)
            cases.append(
                AnnotationCase(
                    annotation_path=resolved_annotation_path,
                    document=document,
                    pdf_path=pdf_path,
                )
            )

    return sorted(cases, key=lambda case: case.document["test_id"])


def create_adapter(
    document: dict[str, Any], *, directory: Path, source_id: uuid.UUID
) -> SourceAdapter:
    """Construct a registered family adapter with only its declared options."""
    adapter_data = document.get("adapter")
    if not isinstance(adapter_data, dict):
        raise ValueError("annotation document must define an adapter object")
    family = adapter_data.get("family")
    if not isinstance(family, str) or family not in ADAPTER_REGISTRY:
        raise ValueError(f"adapter family {family!r} is not registered")

    registration = ADAPTER_REGISTRY[family]
    options = adapter_data.get("options", {})
    if not isinstance(options, dict):
        raise ValueError(f"adapter options for {family!r} must be an object")
    option_names = set(options)
    missing = registration.required_options - option_names
    if missing:
        raise ValueError(
            f"missing required adapter options for {family!r}: {sorted(missing)}"
        )
    unknown = option_names - registration.allowed_options
    if unknown:
        raise ValueError(
            f"unsupported adapter options for {family!r}: {sorted(unknown)}"
        )
    if any(not isinstance(name, str) for name in option_names):
        raise ValueError(f"adapter option names for {family!r} must be strings")

    return registration.adapter_type(
        directory=directory,
        source_id=source_id,
        **options,
    )


def assert_section_boundary_assignment(
    sections: list[RawSection],
    *,
    anchor: str,
    before_heading: str,
    after_heading: str,
    assigned_heading: str,
) -> None:
    """Assert that an annotated boundary anchor belongs only to its section."""
    def normalize(text: str) -> str:
        return " ".join(text.replace("\u00ad", "").split())

    expected_anchor = normalize(anchor)
    assert expected_anchor, "boundary anchor must not be empty"
    before = [
        (index, section)
        for index, section in enumerate(sections)
        if section.heading == before_heading
    ]
    after = [
        (index, section)
        for index, section in enumerate(sections)
        if section.heading == after_heading
    ]
    assigned = [
        (index, section)
        for index, section in enumerate(sections)
        if section.heading == assigned_heading
    ]

    assert len(before) == 1, f"expected one section headed {before_heading!r}"
    assert len(after) == 1, f"expected one section headed {after_heading!r}"
    assert len(assigned) == 1, f"expected one assigned section headed {assigned_heading!r}"
    assert before[0][0] < after[0][0], "after-boundary section must follow before-boundary section"
    assert assigned_heading in {before_heading, after_heading}, (
        "assigned section must be one of the annotated boundary sections"
    )
    assert normalize(assigned[0][1].text).count(expected_anchor) == 1, (
        "boundary anchor must occur exactly once in its assigned section"
    )

    containing_sections = [
        section for section in sections if expected_anchor in normalize(section.text)
    ]
    assert len(containing_sections) == 1 and containing_sections[0] is assigned[0][1], (
        "boundary anchor must not appear in another section"
    )


def _normalise_text(text: str) -> str:
    return " ".join(text.replace("\u00ad", "").split())


def _item_pages(item: object) -> set[int]:
    provenance = getattr(item, "prov", None) or []
    return {
        page_no
        for entry in provenance
        if type(page_no := getattr(entry, "page_no", None)) is int
    }


def assert_docling_matches_annotations(document: object, annotations: dict[str, Any]) -> None:
    """Compare only annotated item text/order and physical PDF page provenance."""
    items = [
        (index, item)
        for index, (item, _level) in enumerate(document.iterate_items())
        if getattr(item, "text", None)
    ]
    test_id = annotations["test_id"]
    headings = sorted(annotations["headings"], key=lambda heading: heading["sequence"])
    matched_positions: list[int] = []

    for expected in headings:
        expected_text = _normalise_text(expected["text"])
        page_no = expected["pdf_page"]
        assert type(page_no) is int, (
            f"{test_id}: verified heading {expected['sequence']} needs a physical PDF page"
        )
        matches = [
            (index, item)
            for index, item in items
            if _normalise_text(item.text) == expected_text and page_no in _item_pages(item)
        ]
        occurrence = expected.get("order_on_page")
        if occurrence is not None:
            assert type(occurrence) is int and occurrence > 0, (
                f"{test_id}: order_on_page must be a positive one-based occurrence"
            )
            assert len(matches) >= occurrence, (
                f"{test_id}: heading {expected_text!r} occurrence {occurrence} was not "
                f"found on physical PDF page {page_no}"
            )
            matches = [matches[occurrence - 1]]
        assert len(matches) == 1, (
            f"{test_id}: heading {expected['sequence']} {expected_text!r} should occur "
            f"once on physical PDF page {page_no}; annotate order_on_page if repeated"
        )
        matched_positions.append(matches[0][0])

    assert matched_positions == sorted(matched_positions), (
        f"{test_id}: annotated headings must appear in source order in Docling's item sequence"
    )

    anchor_positions: list[tuple[int, int]] = []
    for anchor in annotations["text_anchors"]:
        page_no = anchor["pdf_page"]
        assert type(page_no) is int, (
            f"{test_id}: verified text anchor {anchor['id']!r} needs a physical PDF page"
        )
        page_text = _normalise_text(
            " ".join(
                item.text
                for _index, item in items
                if page_no in _item_pages(item)
            )
        )
        anchor_text = _normalise_text(anchor["text"])
        assert page_text.count(anchor_text) == 1, (
            f"{test_id}: anchor {anchor['id']!r} should occur once on physical PDF page "
            f"{page_no}"
        )
        anchor_positions.append((page_no, page_text.index(anchor_text)))
    assert anchor_positions == sorted(anchor_positions), (
        f"{test_id}: annotated text anchors must appear in the expected document order"
    )


def _expected_record_matches(record: Any, expected: dict[str, Any]) -> bool:
    return all(
        getattr(record, field_name) == expected[field_name]
        for field_name in ("raw_designation", "raw_issuer", "raw_title", "edition")
    )


def _actual_references(record: Any) -> list[tuple[str, str, str]]:
    return [
        (
            reference.target_issuer,
            reference.target_designation,
            getattr(reference.edge_type, "value", reference.edge_type),
        )
        for reference in record.raw_references
    ]


def _expected_references(expected: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [
        (reference["target_issuer"], reference["target_designation"], reference["edge_type"])
        for reference in expected["references"]
    ]


def _assert_ordered_subsequence(actual: list[Any], expected: list[Any], message: str) -> None:
    actual_position = 0
    for expected_value in expected:
        try:
            actual_position = actual.index(expected_value, actual_position) + 1
        except ValueError as error:
            raise AssertionError(message) from error


def assert_adapter_matches_annotations(
    adapter: SourceAdapter,
    records: list[Any],
    annotations: dict[str, Any],
) -> None:
    """Compare annotated adapter records, sections, references, and assignments."""
    adapter_annotations = annotations["adapter"]
    expected_records = adapter_annotations["records"]
    test_id = annotations["test_id"]
    coverage = adapter_annotations["record_coverage"]
    actual_for_expected: dict[int, Any] = {}

    if coverage == "complete":
        assert len(records) == len(expected_records), (
            f"{test_id}: adapter record count differs from complete annotations"
        )
        actual_for_expected = {
            expected["sequence"]: actual
            for expected, actual in zip(expected_records, records, strict=True)
        }
    elif coverage == "selected":
        last_matched_index = -1
        for expected in expected_records:
            matches = [
                (index, record)
                for index, record in enumerate(records)
                if _expected_record_matches(record, expected)
            ]
            assert len(matches) == 1, (
                f"{test_id}: selected adapter record {expected['raw_designation']!r} "
                f"must match exactly once"
            )
            matched_index, actual = matches[0]
            assert matched_index > last_matched_index, (
                f"{test_id}: selected adapter records must occur in annotated order"
            )
            last_matched_index = matched_index
            actual_for_expected[expected["sequence"]] = actual
    else:
        raise AssertionError(f"{test_id}: unsupported record coverage {coverage!r}")

    sections_by_record: dict[int, list[RawSection]] = {}
    for expected in expected_records:
        record_sequence = expected["sequence"]
        record = actual_for_expected[record_sequence]
        assert _expected_record_matches(record, expected), (
            f"{test_id}: adapter record {record_sequence} identity/metadata mismatch"
        )
        assert (record.full_text is not None) is expected["full_text_present"], (
            f"{test_id}: adapter record {record_sequence} full-text presence mismatch"
        )

        actual_references = _actual_references(record)
        expected_references = _expected_references(expected)
        if expected["reference_coverage"] == "none":
            assert not actual_references, f"{test_id}: unexpected adapter references"
        elif expected["reference_coverage"] == "complete":
            assert actual_references == expected_references, (
                f"{test_id}: complete adapter reference list differs"
            )
        elif expected["reference_coverage"] == "selected":
            _assert_ordered_subsequence(
                actual_references,
                expected_references,
                f"{test_id}: selected adapter references must preserve order and count",
            )
        else:
            raise AssertionError(
                f"{test_id}: unsupported reference coverage "
                f"{expected['reference_coverage']!r}"
            )

        sections = adapter.extract_structure(record)
        sections_by_record[record_sequence] = sections
        actual_headings = [section.heading for section in sections]
        expected_headings = [section["heading"] for section in expected["sections"]]
        if expected["section_coverage"] == "none":
            assert not sections, f"{test_id}: unexpected adapter sections"
        elif expected["section_coverage"] == "complete":
            assert actual_headings == expected_headings, (
                f"{test_id}: complete adapter section headings/order differ"
            )
        elif expected["section_coverage"] == "selected":
            _assert_ordered_subsequence(
                actual_headings,
                expected_headings,
                f"{test_id}: selected adapter section headings/order differ",
            )
        else:
            raise AssertionError(
                f"{test_id}: unsupported section coverage {expected['section_coverage']!r}"
            )

    for anchor in annotations["text_anchors"]:
        record_sequence = anchor["expected_record_sequence"]
        section_sequence = anchor["expected_section_sequence"]
        if record_sequence is None:
            continue
        record = actual_for_expected[record_sequence]
        anchor_text = _normalise_text(anchor["text"])
        if section_sequence is None:
            if record.full_text is not None:
                assert _normalise_text(record.full_text).count(anchor_text) == 1, (
                    f"{test_id}: anchor {anchor['id']!r} should occur once in adapter text"
                )
            else:
                raise AssertionError(
                    f"{test_id}: anchor {anchor['id']!r} has no observable adapter text or section"
                )
            continue

        expected_record = expected_records[record_sequence - 1]
        expected_sections = expected_record["sections"]
        expected_heading = expected_sections[section_sequence - 1]["heading"]
        sections = sections_by_record[record_sequence]
        matching_sections = [
            section for section in sections if section.heading == expected_heading
        ]
        assert len(matching_sections) == 1, (
            f"{test_id}: expected one adapter section headed {expected_heading!r} "
            f"for anchor {anchor['id']!r}"
        )
        assert _normalise_text(matching_sections[0].text).count(anchor_text) == 1, (
            f"{test_id}: anchor {anchor['id']!r} should occur once in "
            f"section {expected_heading!r}"
        )
        assert not [
            section
            for section in sections
            if section is not matching_sections[0]
            and anchor_text in _normalise_text(section.text)
        ], f"{test_id}: anchor {anchor['id']!r} leaked into another section"

    for boundary in annotations["section_boundaries"]:
        record_sequence = boundary["adapter_record_sequence"]
        expected_record = expected_records[record_sequence - 1]
        expected_sections = expected_record["sections"]
        before_heading = expected_sections[
            boundary["before_section_sequence"] - 1
        ]["heading"]
        after_heading = expected_sections[
            boundary["after_section_sequence"] - 1
        ]["heading"]
        assert boundary["next_heading"] == after_heading, (
            f"{test_id}: annotated next_heading differs from the expected after-section"
        )
        assigned_heading = expected_sections[
            boundary["expected_section_sequence"] - 1
        ]["heading"]
        assert_section_boundary_assignment(
            sections_by_record[record_sequence],
            anchor=boundary["preceding_anchor"],
            before_heading=before_heading,
            after_heading=after_heading,
            assigned_heading=assigned_heading,
        )
