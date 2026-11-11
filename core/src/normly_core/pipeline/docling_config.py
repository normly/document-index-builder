# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""One validated PDF configuration for inspection and production extraction."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class DoclingPdfConfig:
    do_ocr: bool = False
    do_table_structure: bool = True
    table_structure_mode: str = "accurate"
    accelerator_device: str = "cpu"
    accelerator_threads: int = 4


DOCLING_PDF_CONFIG = DoclingPdfConfig()
_active = ContextVar("docling_pdf_config", default=DOCLING_PDF_CONFIG)


def parse_pdf_config(value: object) -> DoclingPdfConfig:
    fields = set(DoclingPdfConfig.__dataclass_fields__)
    if not isinstance(value, dict) or set(value) - fields:
        raise ValueError("unknown Docling configuration fields")
    config = DoclingPdfConfig(**value)
    if config.do_ocr is not False:
        raise ValueError("OCR is not supported by the prepared offline model set")
    if type(config.do_table_structure) is not bool:
        raise ValueError("do_table_structure must be boolean")
    if (
        config.table_structure_mode not in ("fast", "accurate")
        or config.accelerator_device != "cpu"
    ):
        raise ValueError("unsupported table mode or accelerator")
    if (
        type(config.accelerator_threads) is not int
        or not 1 <= config.accelerator_threads <= 64
    ):
        raise ValueError("accelerator_threads must be an integer from 1 to 64")
    return config


def current_pdf_config() -> DoclingPdfConfig:
    return _active.get()


@contextmanager
def use_pdf_config(config: DoclingPdfConfig):
    token = _active.set(config)
    try:
        yield
    finally:
        _active.reset(token)
