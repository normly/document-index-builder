# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors

import hashlib
import os
import uuid
from pathlib import Path

import pytest

from normly_core.pipeline.docling_extraction import extract_document

from .real_pdf_test_support import (
    ADAPTER_REGISTRY,
    AnnotationCase,
    assert_adapter_matches_annotations,
    assert_docling_matches_annotations,
    create_adapter,
    discover_annotation_cases,
)


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_REAL_PDF_TESTS") != "1",
    reason="private real-PDF tests are local-only; set RUN_REAL_PDF_TESTS=1",
)

RAW_DATA_ROOT = Path(__file__).resolve().parents[3] / "web-app-raw-data"


def pytest_generate_tests(metafunc):
    if "case" not in metafunc.fixturenames:
        return
    if os.environ.get("RUN_REAL_PDF_TESTS") != "1":
        metafunc.parametrize("case", [None], ids=["local-opt-in-required"])
        return
    cases = discover_annotation_cases(RAW_DATA_ROOT)
    if not cases:
        raise pytest.UsageError(
            f"no extraction annotations found under {RAW_DATA_ROOT / 'raw_data_test'}"
        )
    metafunc.parametrize(
        "case",
        cases,
        ids=[case.document["test_id"] for case in cases],
        scope="module",
    )


def _require_verified(case: AnnotationCase) -> None:
    document = case.document
    if (
        document.get("annotation_status") != "verified"
        or document.get("manual_review", {}).get("verified") is not True
    ):
        pytest.skip(
            f"{document.get('test_id', '<unknown>')}: annotations are draft; "
            "validate them against the rendered PDF before extraction assertions"
        )


@pytest.fixture(scope="module")
def parsed_document(case: AnnotationCase):
    _require_verified(case)
    document = case.document
    if not case.pdf_path.is_file():
        pytest.fail(
            f"{document['test_id']}: annotated source PDF is unavailable: {case.pdf_path}"
        )

    expected_hash = document.get("pdf_sha256")
    if not isinstance(expected_hash, str) or not expected_hash.strip():
        pytest.fail(f"{document['test_id']}: verified annotations must pin PDF SHA-256")
    actual_hash = hashlib.sha256(case.pdf_path.read_bytes()).hexdigest()
    if expected_hash.removeprefix("sha256:") != actual_hash:
        pytest.fail(f"{document['test_id']}: annotation PDF SHA-256 does not match source")

    for heading in document["headings"]:
        if type(heading.get("pdf_page")) is not int:
            pytest.fail(
                f"{document['test_id']}: verified headings need physical PDF page numbers"
            )
    for anchor in document["text_anchors"]:
        if type(anchor.get("pdf_page")) is not int:
            pytest.fail(
                f"{document['test_id']}: verified text anchors need physical PDF page numbers"
            )
    return extract_document(case.pdf_path)


def test_real_pdf_annotations_are_human_verified_before_extraction(case):
    document = case.document
    assert (
        document.get("annotation_status") == "verified"
        and document.get("manual_review", {}).get("verified") is True
    ), (
        f"{document.get('test_id', '<unknown>')}: annotation pending validation; "
        "verify headings, anchors, and physical PDF page positions first"
    )


def test_real_pdf_docling_properties_match_annotations(case, parsed_document):
    assert_docling_matches_annotations(parsed_document, case.document)


def test_real_pdf_registered_adapter_matches_annotations(
    case, parsed_document, tmp_path, monkeypatch
):
    adapter_data = case.document["adapter"]
    input_filename = adapter_data["input_filename"]
    if Path(input_filename).name != input_filename or not input_filename.lower().endswith(
        ".pdf"
    ):
        pytest.fail(
            f"{case.document['test_id']}: adapter input_filename must be a PDF basename"
        )

    (tmp_path / input_filename).symlink_to(case.pdf_path)
    registration = ADAPTER_REGISTRY[adapter_data["family"]]
    monkeypatch.setattr(
        registration.module,
        "extract_document",
        lambda _path: parsed_document,
    )
    adapter = create_adapter(
        case.document,
        directory=tmp_path,
        source_id=uuid.uuid4(),
    )
    records = list(adapter.fetch())

    assert_adapter_matches_annotations(adapter, records, case.document)
