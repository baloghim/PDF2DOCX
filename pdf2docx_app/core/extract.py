"""Conservative layout heuristics; never rewrite spelling or identifiers."""
import re
import unicodedata
from .model import Paragraph, Run, Page

LIST = re.compile(r'^\s*(?:[•●▪–-]|\d+[.)]|[a-zA-Z][.)])\s+')


def usable(text):
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return False
    bad = sum(c == '\ufffd' or unicodedata.category(c).startswith('C') for c in chars)
    return bad / len(chars) < .05 and any(c.isalnum() for c in chars)


def extract(page):
    result = Page()
    # Tables are kept editable. Exclude their spans from the normal text stream.
    table_boxes = []
    try:
        for table in page.find_tables().tables:
            rows = [[cell or '' for cell in row] for row in table.extract()]
            if rows:
                result.tables.append(rows)
                table_boxes.append(table.bbox)
    except (ValueError, RuntimeError):
        pass
    for block in page.get_text('dict', sort=True)['blocks']:
        if block['type'] != 0:
            continue
        paragraph = None
        previous = None
        for line in block['lines']:
            spans = [s for s in line['spans'] if not any(
                box[0] <= (s['bbox'][0]+s['bbox'][2])/2 <= box[2] and
                box[1] <= (s['bbox'][1]+s['bbox'][3])/2 <= box[3] for box in table_boxes)]
            text = ''.join(s['text'] for s in spans).strip()
            if not text:
                continue
            height = line['bbox'][3]-line['bbox'][1]
            heading = max(s['size'] for s in spans) >= 15
            new = (paragraph is None or LIST.match(text) or heading or
                   (previous and line['bbox'][1]-previous[3] > height * .65))
            if new:
                paragraph = Paragraph([], heading, bool(LIST.match(text)))
                result.paragraphs.append(paragraph)
            elif paragraph.runs:
                # Only explicit soft hyphens are safely removed; literal '-' is preserved.
                if paragraph.runs[-1].text.endswith('\u00ad'):
                    paragraph.runs[-1].text = paragraph.runs[-1].text[:-1]
                else:
                    paragraph.runs.append(Run(' '))
            for s in spans:
                paragraph.runs.append(Run(s['text'], bool(s['flags'] & 16), bool(s['flags'] & 2)))
            previous = line['bbox']
    # Preserve small raster logos/signatures, never full-page scan images.
    for image in page.get_images(full=True):
        for rect in page.get_image_rects(image[0]):
            if 0 < rect.get_area() < page.rect.get_area() * .25:
                data = page.parent.extract_image(image[0])
                if data and data['ext'] in ('png', 'jpeg', 'jpg'):
                    result.images.append(data['image'])
                break
    return result
