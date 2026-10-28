"""Conservative offline style estimates from word images, not whole tilted lines."""
from functools import lru_cache
from statistics import median
from PIL import Image, ImageDraw, ImageFont
from ..resources import asset_path
from .model import Cancelled


@lru_cache(maxsize=2)
def reference_font(bold=False):
    return ImageFont.truetype(str(asset_path('fonts', 'Carlito-Bold.ttf' if bold else 'Carlito-Regular.ttf')), 96)


def percentile(histogram, fraction):
    target = sum(histogram)*fraction
    count = 0
    for value, frequency in enumerate(histogram):
        count += frequency
        if count >= target:
            return value
    return 255


def reference_density(text, size, bold):
    font = reference_font(bold)
    box = font.getbbox(text)
    if box[2] <= box[0] or box[3] <= box[1]:
        return 0
    mask = Image.new('L', (box[2]-box[0], box[3]-box[1]), 0)
    ImageDraw.Draw(mask).text((-box[0],-box[1]),text,fill=255,font=font)
    mask = mask.resize(size, Image.Resampling.BILINEAR)
    return sum(mask.histogram()[128:])/(size[0]*size[1])


def estimate_styles(records, image, scale, cancel=None):
    """Return per-word (point size, bold); uncertain words use page/line consensus.

    Carlito is metrically compatible with the Calibri output font. Matching word
    widths avoids line tilt and accent/descender-induced size changes. Weight is
    estimated against regular/bold raster references with page-specific bias.
    This estimates appearance; it cannot recover original font metadata.
    """
    sizes, scores = [], []
    for record in records:
        if cancel is not None and cancel.is_set():
            raise Cancelled('A feldolgozás megszakadt.')
        text, (x,y,w,h), confidence = record['text'], record['pixels'], record['confidence']
        letters = sum(c.isalpha() for c in text)
        credible = letters >= 3 and len(text) <= 128 and confidence >= 60 and w > 3 and h > 8
        if not credible:
            sizes.append(None)
            scores.append(None)
            continue
        box = reference_font().getbbox(text)
        point_size = w/scale * 96/max(1,box[2]-box[0])
        sizes.append(point_size if 6 <= point_size <= 48 else None)
        crop = image.crop((x,y,x+w,y+h)).convert('L')
        hist = crop.histogram()
        low, high = percentile(hist,.08), percentile(hist,.95)
        if high-low < 30:
            scores.append(None)
            continue
        threshold = int(low+(high-low)*.55)
        density = sum(hist[:threshold+1])/(w*h)
        regular = reference_density(text,(w,h),False)
        bold = reference_density(text,(w,h),True)
        scores.append((density-regular)/max(.025,bold-regular))
    reliable_scores = [s for s in scores if s is not None]
    bias = median(reliable_scores) if reliable_scores else 0
    threshold = max(.6,bias+.55)
    weights = [score is not None and score > threshold for score in scores]
    # Short words inherit bold only from an overwhelmingly bold source line.
    lines = {}
    for i, record in enumerate(records):
        lines.setdefault(record['line_key'], []).append(i)
    for indices in lines.values():
        measured = [i for i in indices if scores[i] is not None]
        total = sum(len(records[i]['text']) for i in measured)
        bold_chars = sum(len(records[i]['text']) for i in measured if weights[i])
        if total and bold_chars/total >= .8:
            for i in indices:
                if scores[i] is None:
                    weights[i] = True
    # Correct the width estimate for words classified as bold.
    for i, is_bold in enumerate(weights):
        if is_bold and sizes[i]:
            text = records[i]['text']
            box = reference_font(True).getbbox(text)
            sizes[i] = records[i]['pixels'][2]/scale * 96/max(1,box[2]-box[0])
    reliable_sizes = [v for v in sizes if v is not None]
    if reliable_sizes:
        # Find the dominant half-point size, allowing normal scan stretch/noise.
        clusters = {}
        for value in reliable_sizes:
            clusters.setdefault(round(value*2)/2,[]).append(value)
        mode = max(clusters, key=lambda v: len(clusters[v]))
        body = round(median(v for v in reliable_sizes if abs(v-mode) <= .6)*2)/2
    else:
        body = 11
    paragraphs = {}
    for i, record in enumerate(records):
        if sizes[i] is not None:
            paragraphs.setdefault(record['paragraph_key'], []).append(sizes[i])
    paragraph_sizes = {}
    for key, values in paragraphs.items():
        size = median(values)
        if abs(size-body) <= max(.6,body*.08):
            size = body
        paragraph_sizes[key] = max(6,min(48,round(size*2)/2))
    return [(paragraph_sizes.get(record['paragraph_key'],body), weights[i]) for i,record in enumerate(records)]
