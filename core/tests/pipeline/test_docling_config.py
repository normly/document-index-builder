# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
import pytest


def test_default_configuration_retains_production_parser_settings():
    from normly_core.pipeline.docling_config import parse_pdf_config

    config = parse_pdf_config({})
    assert config.do_ocr is False
    assert config.do_table_structure is True
    assert config.table_structure_mode == "accurate"
    assert config.accelerator_device == "cpu"
    assert config.accelerator_threads == 4


@pytest.mark.parametrize("value", [
    {"unknown": True}, {"do_ocr": True}, {"do_table_structure": "yes"},
    {"accelerator_threads": 0}, {"accelerator_threads": True},
    {"table_structure_mode": "imaginary"}, {"accelerator_device": "cuda"},
])
def test_unsupported_or_unsafe_configuration_is_refused(value):
    from normly_core.pipeline.docling_config import parse_pdf_config

    with pytest.raises(ValueError):
        parse_pdf_config(value)
