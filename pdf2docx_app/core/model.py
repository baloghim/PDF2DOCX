from dataclasses import dataclass, field


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    size: float | None = None
    font: str | None = None
    color: int = 0
    superscript: bool = False


@dataclass
class Paragraph:
    runs: list[Run]
    heading: bool = False
    list_item: bool = False
    bbox: tuple[float, float, float, float] | None = None
    alignment: str = "left"
    first_line_indent: float = 0
    body_left: float | None = None
    line_spacing: float = 1.05

    @property
    def text(self):
        return ''.join(r.text for r in self.runs)


@dataclass
class Page:
    paragraphs: list[Paragraph] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    images: list[bytes] = field(default_factory=list)
    ocr: bool = False
    uncertain_words: int = 0
    width: float = 595.28
    height: float = 841.89
    table_boxes: list[tuple] = field(default_factory=list)
    table_columns: list[list[float]] = field(default_factory=list)
    image_boxes: list[tuple] = field(default_factory=list)


class ConversionError(Exception):
    """Safe Hungarian message suitable for the UI."""


class Cancelled(ConversionError):
    pass
