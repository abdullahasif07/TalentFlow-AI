"""A tiny text-only PDF writer used for demo resumes; no third-party dependency."""

from __future__ import annotations

import textwrap


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 56
LINE_HEIGHT = 14
WRAP_COLUMNS = 92


def _escape(text: str) -> str:
    safe = text.encode("latin-1", "replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _layout(lines: list[str]) -> list[list[tuple[str, bool]]]:
    """Wrap lines and split them into pages. Lines starting with '# ' render bold."""

    wrapped: list[tuple[str, bool]] = []
    for line in lines:
        bold = line.startswith("# ")
        content = line[2:] if bold else line
        if not content.strip():
            wrapped.append(("", False))
            continue
        for part in textwrap.wrap(content, WRAP_COLUMNS, subsequent_indent="  ") or [""]:
            wrapped.append((part, bold))

    per_page = (PAGE_HEIGHT - 2 * MARGIN) // LINE_HEIGHT
    return [wrapped[index : index + per_page] for index in range(0, len(wrapped), per_page)] or [
        []
    ]


def build_text_pdf(lines: list[str]) -> bytes:
    pages = _layout(lines)
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    catalog_id = add(b"")  # Filled in once the page tree exists.
    pages_id = add(b"")
    regular_font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    bold_font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    page_ids: list[int] = []
    for page in pages:
        commands = ["BT", f"{MARGIN} {PAGE_HEIGHT - MARGIN} Td", f"{LINE_HEIGHT} TL"]
        for text, bold in page:
            commands.append(f"/{'F2' if bold else 'F1'} {12 if bold else 10} Tf")
            commands.append(f"({_escape(text)}) '")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        content_id = add(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_ids.append(
            add(
                (
                    f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} "
                    f"{PAGE_HEIGHT}] /Resources << /Font << /F1 {regular_font} 0 R /F2 "
                    f"{bold_font} 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode()
            )
        )

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_offset = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode()
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    return bytes(output)
