# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

import importlib
import importlib.util
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from normly_core.graph.domain import EdgeType
from normly_core.pipeline.adapters.baua import BauaAdapter
from normly_core.pipeline.adapters.dguv import DguvAdapter
from normly_core.pipeline.adapters.eur_lex import EurLexAdapter
from normly_core.pipeline.domain import RawRecord, RawReference, RawSection


SUPPORT_MODULE = "core.tests.pipeline.real_pdf_test_support"


def _support_function(name):
    spec = importlib.util.find_spec(SUPPORT_MODULE)
    assert spec is not None, "generic real-PDF test support module is missing"
    module = importlib.import_module(SUPPORT_MODULE)
    function = getattr(module, name, None)
    assert callable(function), f"generic support function {name!r} is missing"
    return function


def _write_annotation(root: Path, family: str, test_id: str, source_pdf: str) -> None:
    annotation_dir = root / "raw_data_test" / family
    annotation_dir.mkdir(parents=True)
    (annotation_dir / "extraction-test-annotations.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "documents": [{"test_id": test_id, "source_pdf": source_pdf}],
            }
        ),
        encoding="utf-8",
    )


def _record(
    designation: str,
    *,
    title: str | None = None,
    full_text: str | None = None,
    references: list[RawReference] | None = None,
) -> RawRecord:
    return RawRecord(
        source_id=uuid.uuid4(),
        content_hash=f"sha256:{designation}",
        raw_designation=designation,
        raw_issuer="TEST",
        raw_title=title,
        full_text=full_text,
        language="en",
        raw_references=references or [],
    )


def _expected_record(
    sequence: int,
    designation: str,
    *,
    title: str | None = None,
    reference_coverage: str = "none",
    references: list[dict] | None = None,
) -> dict:
    return {
        "sequence": sequence,
        "raw_designation": designation,
        "raw_issuer": "TEST",
        "raw_title": title,
        "edition": None,
        "full_text_present": False,
        "section_coverage": "none",
        "sections": [],
        "reference_coverage": reference_coverage,
        "references": references or [],
    }


def test_discovery_loads_nested_annotations_in_stable_test_id_order(tmp_path):
    _write_annotation(tmp_path, "FamilyB", "b-case", "raw_data_test/FamilyB/b.pdf")
    _write_annotation(tmp_path, "FamilyA", "a-case", "raw_data_test/FamilyA/a.pdf")

    cases = _support_function("discover_annotation_cases")(tmp_path)

    assert [case.document["test_id"] for case in cases] == ["a-case", "b-case"]
    assert cases[0].annotation_path == (
        tmp_path / "raw_data_test" / "FamilyA" / "extraction-test-annotations.json"
    )
    assert cases[0].pdf_path == tmp_path / "raw_data_test" / "FamilyA" / "a.pdf"


def test_discovery_rejects_source_paths_outside_raw_data_root(tmp_path):
    _write_annotation(tmp_path, "FamilyA", "escape", "../../outside.pdf")

    with pytest.raises(ValueError, match="must remain inside raw_data_test"):
        _support_function("discover_annotation_cases")(tmp_path)


def test_discovery_ignores_annotations_outside_raw_data_test(tmp_path):
    _write_annotation(tmp_path, "FamilyA", "expected", "raw_data_test/FamilyA/a.pdf")
    (tmp_path / "extraction-test-annotations.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "documents": [
                    {"test_id": "not-a-test-case", "source_pdf": "raw_data_test/FamilyA/a.pdf"}
                ],
            }
        ),
        encoding="utf-8",
    )

    cases = _support_function("discover_annotation_cases")(tmp_path)

    assert [case.document["test_id"] for case in cases] == ["expected"]


@pytest.mark.parametrize(
    ("family", "options", "adapter_type"),
    [
        ("baua", {}, BauaAdapter),
        ("dguv", {}, DguvAdapter),
        ("eur_lex", {"legislation_reference": "2006/42/EC"}, EurLexAdapter),
    ],
)
def test_registry_constructs_registered_adapter_families(
    tmp_path, family, options, adapter_type
):
    adapter = _support_function("create_adapter")(
        {"adapter": {"family": family, "options": options}},
        directory=tmp_path,
        source_id=uuid.uuid4(),
    )

    assert isinstance(adapter, adapter_type)


def test_registry_rejects_unknown_family_and_invalid_options(tmp_path):
    create_adapter = _support_function("create_adapter")

    with pytest.raises(ValueError, match="not registered"):
        create_adapter(
            {"adapter": {"family": "unknown", "options": {}}},
            directory=tmp_path,
            source_id=uuid.uuid4(),
        )
    with pytest.raises(ValueError, match="unsupported adapter options"):
        create_adapter(
            {"adapter": {"family": "baua", "options": {"unexpected": True}}},
            directory=tmp_path,
            source_id=uuid.uuid4(),
        )
    with pytest.raises(ValueError, match="missing required adapter options"):
        create_adapter(
            {"adapter": {"family": "eur_lex", "options": {}}},
            directory=tmp_path,
            source_id=uuid.uuid4(),
        )


def test_boundary_assertion_rejects_anchor_leaking_to_another_section():
    correct_sections = [
        RawSection(1, "1 Scope", "A short boundary anchor belongs here."),
        RawSection(2, "2 Definitions", "The next section starts here."),
    ]
    assert_boundary = _support_function("assert_section_boundary_assignment")

    assert_boundary(
        correct_sections,
        anchor="A short boundary anchor belongs here.",
        before_heading="1 Scope",
        after_heading="2 Definitions",
        assigned_heading="1 Scope",
    )
    assert_boundary(
        [
            RawSection(1, "1 Scope", "Body before the boundary."),
            RawSection(2, "2 Definitions", "A short boundary anchor belongs here."),
        ],
        anchor="A short boundary anchor belongs here.",
        before_heading="1 Scope",
        after_heading="2 Definitions",
        assigned_heading="2 Definitions",
    )

    leaking_sections = [
        correct_sections[0],
        RawSection(
            2,
            "2 Definitions",
            "A short boundary anchor belongs here. The next section starts here.",
        ),
    ]
    with pytest.raises(AssertionError, match="must not appear in another section"):
        assert_boundary(
            leaking_sections,
            anchor="A short boundary anchor belongs here.",
            before_heading="1 Scope",
            after_heading="2 Definitions",
            assigned_heading="1 Scope",
        )


def test_docling_assertion_checks_heading_text_order_and_physical_page():
    document = SimpleNamespace(
        iterate_items=lambda: iter(
            [
                (SimpleNamespace(text="1 Scope", prov=[SimpleNamespace(page_no=2)]), 0),
                (SimpleNamespace(text="Short source anchor.", prov=[SimpleNamespace(page_no=2)]), 0),
                (SimpleNamespace(text="2 Definitions", prov=[SimpleNamespace(page_no=3)]), 0),
            ]
        )
    )
    annotation = {
        "test_id": "synthetic-docling-case",
        "headings": [
            {"sequence": 1, "text": "1 Scope", "pdf_page": 2, "order_on_page": None},
            {
                "sequence": 2,
                "text": "2 Definitions",
                "pdf_page": 3,
                "order_on_page": None,
            },
        ],
        "text_anchors": [
            {"id": "body", "text": "Short source anchor.", "pdf_page": 2}
        ],
    }

    _support_function("assert_docling_matches_annotations")(document, annotation)

    annotation["headings"][0]["pdf_page"] = 1
    with pytest.raises(AssertionError, match="physical PDF page 1"):
        _support_function("assert_docling_matches_annotations")(document, annotation)


def test_adapter_assertion_checks_records_sections_and_anchor_assignment():
    source_id = uuid.uuid4()
    record = RawRecord(
        source_id=source_id,
        content_hash="sha256:synthetic",
        raw_designation="SYNTHETIC 1",
        raw_issuer="TEST",
        raw_title="Synthetic publication",
        full_text="1 Scope\nShort source anchor.\n\n2 Definitions\nOther body.",
        language="en",
    )
    sections = [
        RawSection(1, "1 Scope", "Short source anchor."),
        RawSection(2, "2 Definitions", "Other body."),
    ]
    adapter = SimpleNamespace(extract_structure=lambda _record: sections)
    annotation = {
        "test_id": "synthetic-adapter-case",
        "adapter": {
            "record_coverage": "complete",
            "records": [
                {
                    "sequence": 1,
                    "raw_designation": "SYNTHETIC 1",
                    "raw_issuer": "TEST",
                    "raw_title": "Synthetic publication",
                    "edition": None,
                    "full_text_present": True,
                    "section_coverage": "complete",
                    "sections": [
                        {"heading": "1 Scope"},
                        {"heading": "2 Definitions"},
                    ],
                    "reference_coverage": "none",
                    "references": [],
                }
            ],
        },
        "text_anchors": [
            {
                "id": "body",
                "text": "Short source anchor.",
                "expected_record_sequence": 1,
                "expected_section_sequence": 1,
            }
        ],
        "section_boundaries": [
            {
                "adapter_record_sequence": 1,
                "before_section_sequence": 1,
                "after_section_sequence": 2,
                "expected_section_sequence": 1,
                "preceding_anchor": "Short source anchor.",
                "next_heading": "2 Definitions",
            }
        ],
    }

    _support_function("assert_adapter_matches_annotations")(
        adapter, [record], annotation
    )

    leaking_sections = [
        sections[0],
        RawSection(2, "2 Definitions", "Short source anchor. Other body."),
    ]
    adapter.extract_structure = lambda _record: leaking_sections
    with pytest.raises(AssertionError, match="leaked into another section"):
        _support_function("assert_adapter_matches_annotations")(
            adapter, [record], annotation
        )


def test_selected_adapter_records_must_preserve_annotated_order():
    expected = [
        _expected_record(1, "SYNTHETIC A"),
        _expected_record(2, "SYNTHETIC B"),
    ]
    annotation = {
        "test_id": "selected-record-order",
        "adapter": {"record_coverage": "selected", "records": expected},
        "text_anchors": [],
        "section_boundaries": [],
    }
    adapter = SimpleNamespace(extract_structure=lambda _record: [])

    with pytest.raises(AssertionError, match="selected adapter records must occur in annotated order"):
        _support_function("assert_adapter_matches_annotations")(
            adapter,
            [_record("SYNTHETIC B"), _record("SYNTHETIC A")],
            annotation,
        )


@pytest.mark.parametrize(
    ("expected_references", "actual_references"),
    [
        (
            [
                {"target_issuer": "A", "target_designation": "1", "edge_type": "references"},
                {"target_issuer": "B", "target_designation": "2", "edge_type": "replaces"},
            ],
            [
                RawReference("B", "2", EdgeType.REPLACES),
                RawReference("A", "1", EdgeType.REFERENCES),
            ],
        ),
        (
            [
                {"target_issuer": "A", "target_designation": "1", "edge_type": "references"},
                {"target_issuer": "A", "target_designation": "1", "edge_type": "references"},
            ],
            [RawReference("A", "1", EdgeType.REFERENCES)],
        ),
    ],
    ids=["order", "duplicate-count"],
)
def test_selected_references_preserve_order_and_duplicate_count(
    expected_references, actual_references
):
    expected = _expected_record(
        1,
        "SYNTHETIC RECORD",
        reference_coverage="selected",
        references=expected_references,
    )
    annotation = {
        "test_id": "selected-reference-order",
        "adapter": {"record_coverage": "complete", "records": [expected]},
        "text_anchors": [],
        "section_boundaries": [],
    }
    adapter = SimpleNamespace(extract_structure=lambda _record: [])

    with pytest.raises(AssertionError, match="selected adapter references must preserve order and count"):
        _support_function("assert_adapter_matches_annotations")(
            adapter,
            [_record("SYNTHETIC RECORD", references=actual_references)],
            annotation,
        )


def test_anchor_assignment_without_adapter_text_or_section_is_rejected():
    expected = _expected_record(1, "SYNTHETIC RECORD")
    annotation = {
        "test_id": "unobservable-anchor-assignment",
        "adapter": {"record_coverage": "complete", "records": [expected]},
        "text_anchors": [
            {
                "id": "anchor",
                "text": "Not present in any adapter output",
                "expected_record_sequence": 1,
                "expected_section_sequence": None,
            }
        ],
        "section_boundaries": [],
    }
    adapter = SimpleNamespace(extract_structure=lambda _record: [])

    with pytest.raises(AssertionError, match="has no observable adapter text or section"):
        _support_function("assert_adapter_matches_annotations")(
            adapter, [_record("SYNTHETIC RECORD")], annotation
        )
