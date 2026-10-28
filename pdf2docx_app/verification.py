"""Offline packaged-runtime verification used by the Windows build pipeline."""
import io
import json
import os
from pathlib import Path
import tempfile
import pymupdf
from docx import Document
from PIL import Image, ImageDraw, ImageFont
from .core.converter import convert
from .gui.main_window import Application


def verify(report):
    result = {'ok': False}
    try:
        if os.name != 'nt':
            raise RuntimeError('Windows verification requires Windows')
        app = Application()
        try:
            app.root.withdraw()
            app.root.update()
            if not app.dnd:
                raise RuntimeError('Native TkDnD failed to initialize')
        finally:
            app.root.destroy()
        reference = 'Árvíztűrő tükörfúrógép.'
        with tempfile.TemporaryDirectory(prefix='pdf2docx-check-') as tmp:
            path = Path(tmp) / 'Árvíz teszt.pdf'
            image = Image.new('RGB', (1800, 700), 'white')
            font = ImageFont.truetype(str(Path(os.environ['WINDIR']) / 'Fonts' / 'arial.ttf'), 60)
            ImageDraw.Draw(image).text((100, 100), reference, fill='black', font=font)
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            with pymupdf.open() as pdf:
                page = pdf.new_page()
                page.insert_text((50, 50), 'Digital test')
                page = pdf.new_page(width=600, height=233.33)
                page.insert_image(page.rect, stream=buffer.getvalue())
                pdf.save(path)
            output = convert(path)
            content = '\n'.join(p.text for p in Document(output.path).paragraphs)
            if reference not in content or 'Digital test' not in content or output.ocr_pages != 1:
                raise RuntimeError('Bundled digital/OCR conversion reference mismatch')
        result = {'ok': True, 'native_tkdnd': True, 'digital_pdf': True, 'hungarian_ocr': True}
    except Exception as error:
        result['error_category'] = type(error).__name__
    Path(report).write_text(json.dumps(result), encoding='utf-8')
    return 0 if result['ok'] else 1
