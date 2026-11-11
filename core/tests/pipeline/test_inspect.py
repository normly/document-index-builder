# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import hashlib
import json
import warnings

import pytest


def inspection_inputs(tmp_path):
    pdf = tmp_path / "single document.pdf"
    pdf.write_bytes(b"%PDF-synthetic-test-input")
    config = tmp_path / "configuration.json"
    data = {
        "source": "baua",
        "input_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "rights": {
            "jurisdiction": "DE",
            "may_process": True,
            "legal_basis_reference": "Authorized synthetic local test",
        },
        "docling": {"table_structure_mode": "fast", "accelerator_threads": 2},
    }
    config.write_text(json.dumps(data))
    return pdf, config, data


def test_direct_inspection_rejects_authorized_hash_matched_html(tmp_path, monkeypatch):
    from docling.document_converter import DocumentConverter
    from normly_core.pipeline import docling_extraction
    from normly_core.pipeline.inspect import inspect_pdf

    _, config, data = inspection_inputs(tmp_path)
    html = tmp_path / "not-a-pdf.html"
    html.write_text("<html><body>Invented HTML fixture</body></html>")
    data["input_sha256"] = hashlib.sha256(html.read_bytes()).hexdigest()
    config.write_text(json.dumps(data))
    monkeypatch.setattr(DocumentConverter, "initialize_pipeline", lambda *a: None)
    docling_extraction._converters.clear()
    try:
        with pytest.raises(docling_extraction.DocumentExtractionError):
            inspect_pdf(
                source="baua",
                input_path=html,
                config_path=config,
                output_dir=tmp_path / "html-output",
            )
        assert not (tmp_path / "html-output").exists()
    finally:
        docling_extraction._converters.clear()


def test_inspect_writes_markdown_native_json_effective_config_and_report_without_database(
    tmp_path, monkeypatch
):
    from docling_core.types.doc import DoclingDocument, DocItemLabel
    from normly_core.pipeline import inspect as inspector
    from normly_core.pipeline.docling_config import current_pdf_config

    pdf, config, _ = inspection_inputs(tmp_path)
    doc = DoclingDocument(name="Synthetic")
    doc.add_text(label=DocItemLabel.TEXT, text="Original synthetic inspection text")

    def extract(path):
        assert path == pdf
        assert current_pdf_config().table_structure_mode == "fast"
        warnings.warn("synthetic inspection warning", UserWarning)
        return doc

    def no_database(*args, **kwargs):
        raise AssertionError("inspection attempted database access")

    monkeypatch.setattr(inspector, "extract_document", extract)
    monkeypatch.setattr("sqlalchemy.create_engine", no_database)
    out = inspector.inspect_pdf(
        source="baua",
        input_path=pdf,
        config_path=config,
        output_dir=tmp_path / "output",
    )
    assert {p.name for p in out.iterdir()} == {
        "document.md",
        "document.json",
        "configuration.json",
        "report.json",
    }
    assert "Original synthetic inspection text" in (out / "document.md").read_text()
    assert (
        DoclingDocument.model_validate_json((out / "document.json").read_text()).name
        == "Synthetic"
    )
    assert (
        json.loads((out / "configuration.json").read_text())["docling"][
            "table_structure_mode"
        ]
        == "fast"
    )
    report = json.loads((out / "report.json").read_text())
    assert report["input_sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert report["versions"]["docling"]
    assert (
        report["model_revisions"]["layout"]
        == "8f39ad3c0b4c58e9c2d2c84a38465abf757272d8"
    )
    assert any(
        "synthetic inspection warning" in warning["message"]
        for warning in report["warnings"]
    )
    assert current_pdf_config().table_structure_mode == "accurate"


@pytest.mark.parametrize("damage", ["permission", "classification", "hash", "source"])
def test_inspect_rejects_missing_or_mismatched_processing_authorization(
    tmp_path, damage
):
    from normly_core.pipeline.inspect import inspect_pdf

    pdf, config, data = inspection_inputs(tmp_path)
    if damage == "permission":
        data["rights"]["may_process"] = False
    elif damage == "classification":
        data.pop("rights")
    elif damage == "hash":
        data["input_sha256"] = "0" * 64
    else:
        data["source"] = "dguv"
    config.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        inspect_pdf(
            source="baua",
            input_path=pdf,
            config_path=config,
            output_dir=tmp_path / "output",
        )
    assert not (tmp_path / "output").exists()


def test_inspect_rejects_existing_output_and_cleans_partial_output(
    tmp_path, monkeypatch
):
    from normly_core.pipeline import inspect as inspector

    pdf, config, _ = inspection_inputs(tmp_path)
    out = tmp_path / "existing"
    out.mkdir()
    (out / "keep.txt").write_text("existing user work")
    with pytest.raises(FileExistsError):
        inspector.inspect_pdf(
            source="baua", input_path=pdf, config_path=config, output_dir=out
        )
    assert (out / "keep.txt").read_text() == "existing user work"

    def broken(path):
        raise RuntimeError("synthetic extraction failure")

    monkeypatch.setattr(inspector, "extract_document", broken)
    with pytest.raises(RuntimeError):
        inspector.inspect_pdf(
            source="baua",
            input_path=pdf,
            config_path=config,
            output_dir=tmp_path / "failed",
        )
    assert not (tmp_path / "failed").exists()
