from dataclasses import dataclass, field


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass
class Paragraph:
    runs: list[Run]
    heading: bool = False
    list_item: bool = False

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


class ConversionError(Exception):
    """Safe Hungarian message suitable for the UI."""


class Cancelled(ConversionError):
    pass
