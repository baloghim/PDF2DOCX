"""Geometry-based paragraph reconstruction shared by PDF and OCR extraction."""
from dataclasses import dataclass, replace
from statistics import median
import re
from .model import Paragraph, Run

LIST = re.compile(r'^\s*(?:[•●▪–-]|\d+[.)]|[a-zA-Z][.)])\s+')


@dataclass
class Line:
    runs: list[Run]
    bbox: tuple[float, float, float, float]
    baseline: float | None = None

    @property
    def text(self):
        return ''.join(r.text for r in self.runs)

    @property
    def size(self):
        values = [r.size for r in self.runs if r.size and r.text.strip()]
        return median(values) if values else 11


def bounds(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def paragraphs_from_blocks(blocks, page_width):
    lines = [line for block in blocks for line in block if line.text.strip()]
    if not lines:
        return []
    body_size = median([line.size for line in lines for _ in range(min(100, max(1, len(line.text))))])
    body_left = min(line.bbox[0] for line in lines)
    body_right = max(line.bbox[2] for line in lines)
    body_width = max(body_right-body_left, page_width * .5)
    output = []
    for block in blocks:
        groups = []
        for line in block:
            if not line.text.strip():
                continue
            heading = line.size >= max(13, body_size * 1.2)
            if (not groups or LIST.match(line.text) or
                abs(line.size-groups[-1][-1].size) > 1.5 or
                line.bbox[1]-groups[-1][-1].bbox[3] > line.size * .7):
                groups.append([])
            groups[-1].append(line)
        for group in groups:
            box = bounds([line.bbox for line in group])
            p = Paragraph([], any(line.size >= max(13, body_size*1.2) for line in group), bool(LIST.match(group[0].text)), bbox=box)
            width = max(line.bbox[2]-line.bbox[0] for line in group)
            centered = all(abs((line.bbox[0]+line.bbox[2])/2-page_width/2) < 12 for line in group)
            if centered and width < body_width * .85 and not p.list_item:
                p.alignment = 'center'
            elif all(abs(line.bbox[2]-body_right) < 10 for line in group) and box[0] > body_left+body_width*.4 and width < body_width*.7:
                p.alignment = 'right'
            elif len(group) >= 3 and width >= body_width*.8 and all(abs(line.bbox[2]-box[2]) < 10 for line in group[:-1]):
                p.alignment = 'justify'
            for index, line in enumerate(group):
                if index:
                    previous = group[index-1]
                    if p.runs and p.runs[-1].text.endswith('\u00ad'):
                        p.runs[-1].text = p.runs[-1].text[:-1]
                    else:
                        wrap = ((width >= page_width*.45 and previous.bbox[2]-previous.bbox[0] >= width*.72) or (len(group) <= 2 and p.alignment == 'left' and not p.heading and not p.list_item))
                        p.runs.append(replace(p.runs[-1],text=' ' if wrap else '\n'))
                p.runs.extend(line.runs)
            if len(group) > 1:
                if width >= page_width*.45:
                    p.right_edge = box[2]
                rest_left = median(line.bbox[0] for line in group[1:])
                p.first_line_indent = group[0].bbox[0]-rest_left
                p.body_left = rest_left
                intervals = [(b.baseline or b.bbox[3])-(a.baseline or a.bbox[3]) for a,b in zip(group,group[1:])]
                positive_intervals = [v for v in intervals if v > 0]
                if positive_intervals:
                    p.line_height = max(max(line.size for line in group)*1.1, median(positive_intervals))
                factors = [v / max(body_size, 1) for v in intervals if v > 0]
                p.line_spacing = max(1, min(1.8, median(factors))) if factors else 1
            else:
                p.body_left = box[0]
            output.append(p)
    return output
