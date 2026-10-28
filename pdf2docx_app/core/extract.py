"""Extract editable content and its logical formatting without rewriting text."""
import re
import unicodedata
from .model import Run, Page
from .layout import Line, paragraphs_from_blocks


def usable(text):
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return False
    bad = sum(c == '\ufffd' or unicodedata.category(c).startswith('C') for c in chars)
    return bad / len(chars) < .05 and any(c.isalnum() for c in chars)


def font_family(name, flags=0):
    name = re.sub(r'^[A-Z]{6}\+', '', name).lower()
    for key, family in [('times', 'Times New Roman'), ('cambria', 'Cambria'), ('courier', 'Courier New'), ('consolas', 'Consolas'), ('calibri', 'Calibri'), ('arial', 'Arial'), ('helvetica', 'Arial'), ('dejavusans', 'Arial'), ('verdana', 'Verdana'), ('tahoma', 'Tahoma'), ('georgia', 'Georgia')]:
        if key in name:
            return family
    return 'Courier New' if flags & 8 else ('Times New Roman' if flags & 4 else 'Calibri')


def extract(page):
    result = Page(width=page.rect.width, height=page.rect.height)
    try:
        for table in page.find_tables().tables:
            rows = [[cell or '' for cell in row] for row in table.extract()]
            if rows:
                result.tables.append(rows)
                result.table_boxes.append(tuple(table.bbox))
                cells = table.rows[0].cells if table.rows else []
                result.table_columns.append([cell[2]-cell[0] if cell else 0 for cell in cells])
    except (ValueError, RuntimeError):
        pass
    blocks = []
    for block in page.get_text('dict', sort=True)['blocks']:
        if block['type'] != 0:
            continue
        lines = []
        for line in block['lines']:
            spans = [s for s in line['spans'] if not any(
                box[0] <= (s['bbox'][0]+s['bbox'][2])/2 <= box[2] and
                box[1] <= (s['bbox'][1]+s['bbox'][3])/2 <= box[3] for box in result.table_boxes)]
            if not any(s['text'].strip() for s in spans):
                continue
            runs = [Run(s['text'], bool(s['flags'] & 16), bool(s['flags'] & 2),
                        s['size'], font_family(s['font'], s['flags']), s.get('color', 0), bool(s['flags'] & 1)) for s in spans]
            lines.append(Line(runs, tuple(line['bbox']), spans[0].get('origin', (0, line['bbox'][3]))[1]))
        if lines:
            blocks.append(lines)
    result.paragraphs = paragraphs_from_blocks(blocks, result.width)
    seen = set()
    for image in page.get_images(full=True):
        for rect in page.get_image_rects(image[0]):
            key = (image[0], tuple(rect))
            if key in seen:
                continue
            seen.add(key)
            if 0 < rect.get_area() < page.rect.get_area() * .25:
                data = page.parent.extract_image(image[0])
                if data and data['ext'] in ('png', 'jpeg', 'jpg'):
                    result.images.append(data['image'])
                    result.image_boxes.append(tuple(rect))
    return result
