# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

import json
import os
from pathlib import Path

import pytest

from .real_pdf_test_support import ADAPTER_REGISTRY, discover_annotation_cases


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_REAL_PDF_TESTS") != "1",
    reason="private real-PDF test data is local-only; set RUN_REAL_PDF_TESTS=1",
)

RAW_DATA_ROOT = Path(__file__).resolve().parents[3] / "web-app-raw-data"
TEMPLATE_PATH = RAW_DATA_ROOT / "extraction-test-template.json"


def pytest_generate_tests(metafunc):
    if "annotation_case" not in metafunc.fixturenames:
        return
    if os.environ.get("RUN_REAL_PDF_TESTS") != "1":
        metafunc.parametrize("annotation_case", [None], ids=["local-opt-in-required"])
        return
    cases = discover_annotation_cases(RAW_DATA_ROOT)
    if not cases:
        raise pytest.UsageError(
            f"no {('extraction-test-annotations.json')} files found under "
            f"{RAW_DATA_ROOT / 'raw_data_test'}"
        )
    metafunc.parametrize(
        "annotation_case",
        cases,
        ids=[case.document["test_id"] for case in cases],
        scope="module",
    )


def _assert_fields(actual, expected_fields: set[str], label: str) -> None:
    assert isinstance(actual, dict), f"{label} must be a JSON object"
    assert set(actual) == expected_fields, f"{label} fields differ from the template"


def test_annotation_case_matches_family_neutral_template(annotation_case):
    template_payload = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    annotations_payload = json.loads(
        annotation_case.annotation_path.read_text(encoding="utf-8")
    )
    assert template_payload["schema_version"] == 2
    assert annotations_payload["schema_version"] == template_payload["schema_version"]
    assert set(annotations_payload) == set(template_payload) == {
        "schema_version",
        "documents",
    }

    template_document = template_payload["documents"][0]
    document = annotation_case.document
    _assert_fields(document, set(template_document), "annotation document")
    assert document["annotation_status"] in {"draft", "verified"}
    assert document["manual_review"]["verified"] is (
        document["annotation_status"] == "verified"
    )
    assert document["source_pdf"].endswith(".pdf")
    assert document["pdf_sha256"] is None or isinstance(document["pdf_sha256"], str)
    assert set(document["metadata"]) == set(template_document["metadata"])
    assert set(document["scope"]) == set(template_document["scope"])
    assert set(document["manual_review"]) == set(template_document["manual_review"])

    adapter_template = template_document["adapter"]
    adapter = document["adapter"]
    _assert_fields(adapter, set(adapter_template), "adapter annotation")
    assert isinstance(adapter["family"], str)
    assert adapter["family"] in ADAPTER_REGISTRY
    assert Path(adapter["input_filename"]).name == adapter["input_filename"]
    assert adapter["input_filename"].lower().endswith(".pdf")
    assert isinstance(adapter["options"], dict)
    assert adapter["record_coverage"] in {"selected", "complete"}
    assert adapter["records"]

    record_template = adapter_template["records"][0]
    record_fields = set(record_template)
    section_fields = set(record_template["sections"][0])
    reference_fields = set(record_template["references"][0])
    for position, record in enumerate(adapter["records"], start=1):
        _assert_fields(record, record_fields, "expected adapter record")
        assert record["sequence"] == position
        assert record["full_text_present"] in {True, False}
        assert record["section_coverage"] in {"none", "selected", "complete"}
        assert record["reference_coverage"] in {"none", "selected", "complete"}
        assert (record["section_coverage"] == "none") is (not record["sections"])
        assert (record["reference_coverage"] == "none") is (not record["references"])
        assert all(set(section) == section_fields for section in record["sections"])
        assert all(set(reference) == reference_fields for reference in record["references"])

    heading_template = template_document["headings"][0]
    anchor_template = template_document["text_anchors"][0]
    boundary_template = template_document["section_boundaries"][0]
    assert document["headings"]
    assert document["text_anchors"]
    assert all(set(heading) == set(heading_template) for heading in document["headings"])
    assert all(set(anchor) == set(anchor_template) for anchor in document["text_anchors"])
    assert all(set(boundary) == set(boundary_template) for boundary in document["section_boundaries"])
    assert [heading["sequence"] for heading in document["headings"]] == list(
        range(1, len(document["headings"]) + 1)
    )
    assert all(
        heading["pdf_page"] is None or type(heading["pdf_page"]) is int
        for heading in document["headings"]
    )
    assert all(
        anchor["pdf_page"] is None or type(anchor["pdf_page"]) is int
        for anchor in document["text_anchors"]
    )
    assert all(
        heading["order_on_page"] is None
        or (type(heading["order_on_page"]) is int and heading["order_on_page"] > 0)
        for heading in document["headings"]
    )

    record_by_sequence = {record["sequence"]: record for record in adapter["records"]}
    anchor_ids = {anchor["id"] for anchor in document["text_anchors"]}
    assert len(anchor_ids) == len(document["text_anchors"])
    for anchor in document["text_anchors"]:
        record_sequence = anchor["expected_record_sequence"]
        section_sequence = anchor["expected_section_sequence"]
        assert record_sequence is None or record_sequence in record_by_sequence
        if section_sequence is not None:
            assert record_sequence is not None
            sections = record_by_sequence[record_sequence]["sections"]
            assert 1 <= section_sequence <= len(sections)
        elif record_sequence is not None:
            assert record_by_sequence[record_sequence]["full_text_present"], (
                f"anchor {anchor['id']!r} has no observable adapter text or section"
            )

    for boundary in document["section_boundaries"]:
        assert set(boundary) == set(boundary_template)
        record = record_by_sequence[boundary["adapter_record_sequence"]]
        sections = record["sections"]
        before = boundary["before_section_sequence"]
        after = boundary["after_section_sequence"]
        assigned = boundary["expected_section_sequence"]
        assert 1 <= before < after <= len(sections)
        assert assigned in {before, after}
        assert boundary["next_heading"] == sections[after - 1]["heading"]
