# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 normly contributors
"""Generate PDF fixtures from invented text; never copy publisher PDFs into CI."""
from pathlib import Path
from tempfile import TemporaryDirectory

_temporary = None


def fixture_directory() -> Path:
    global _temporary
    if _temporary is not None:
        return Path(_temporary.name)
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A2, landscape
    from reportlab.pdfgen import canvas
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    _temporary = TemporaryDirectory(prefix="document-index-synthetic-")
    directory = Path(_temporary.name)
    pdf = canvas.Canvas(str(directory / "dguv_sample_vorschrift.pdf"), invariant=True)
    lines = [
        "DGUV Vorschrift 1", "Grundsätze der Prävention", "",
        "§ 1 Geltungsbereich", "Diese Vorschrift gilt ausschließlich als synthetischer Test.", "",
        "§ 2 Pflichten des Unternehmers", "Erfundener Text für den zweiten Testabschnitt.", "",
        "§ 3 Pflichten der Versicherten", "Erfundener Text für den dritten Testabschnitt.",
    ]
    # Keep metadata out of the page-header band: it is document content, not
    # repeating furniture. This makes the generated fixture unambiguous.
    y = 700
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 20
    pdf.save()

    headers = ["Legislation", "ESO (B)", "Standard reference", "Title", "Type", "Column5", "Publication", "Column7", "Column8", "Column9", "Column10", "Withdrawal"]
    rows = [headers]
    references = [
        ("EN ISO 12100:2010", "SYNTHETIC-NEW", "-"),
        ("EN ISO 12100-1:2003, EN ISO 12100-1:2003/A1:2009", "SYNTHETIC-OLD-1", "SYNTHETIC-NEW"),
        ("EN ISO 12100-2:2003, EN ISO 12100-2:2003/A1:2009", "SYNTHETIC-OLD-2", "SYNTHETIC-NEW"),
        ("EN ISO 14121-1:2007", "SYNTHETIC-OLD-3", "SYNTHETIC-NEW"),
        ("EN 349:1993+A1:2008", "SYNTHETIC-OLD-4", "SYNTHETIC-MISSING"),
        ("EN 547-1:1996+A1:2008", "SYNTHETIC-OTHER", "-"),
        ("EN 99999:2026", "SYNTHETIC-INVENTED", "-"),
    ]
    for designation, publication, withdrawal in references:
        rows.append(["2006/42/EC", "CEN", designation, "Invented test title", "A", "FIVE", publication, "SEVEN", "EIGHT", "NINE", "TEN", withdrawal])
    table = Table(rows, colWidths=[80, 60, 380, 140, 60, 60, 140, 60, 60, 60, 60, 140], rowHeights=50)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    SimpleDocTemplate(str(directory / "eur_lex_machinery_summary.pdf"), pagesize=landscape(A2),
                      leftMargin=35, rightMargin=35).build([table])
    return directory
