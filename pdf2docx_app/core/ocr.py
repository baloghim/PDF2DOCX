import csv
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from PIL import Image, ImageOps
from .model import ConversionError, Cancelled, Page, Paragraph, Run


class Tesseract:
    def __init__(self, language='hun+eng'):
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
        bundled = base / 'ocr' / 'tesseract.exe'
        self.command = str(bundled) if bundled.exists() else shutil.which('tesseract')
        self.data = base / 'ocr' / 'tessdata' if bundled.exists() else None
        self.language = language

    def _run(self, arguments, cancel):
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            process = subprocess.Popen(arguments, stdout=out, stderr=err, creationflags=flags)
            try:
                import time
                deadline = time.monotonic() + 180
                while process.poll() is None:
                    if cancel.wait(.1):
                        raise Cancelled('A feldolgozás megszakadt.')
                    if time.monotonic() > deadline:
                        raise ConversionError('A szövegfelismerés túllépte az időkorlátot.')
                if process.returncode:
                    raise ConversionError('A szövegfelismerés nem sikerült.')
                out.seek(0)
                return out.read().decode('utf-8', errors='replace')
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()

    def recognize(self, page, cancel, clip=None):
        if not self.command:
            raise ConversionError('Az OCR-motor nem érhető el. Ehhez az oldalhoz Tesseract szükséges.')
        args = [self.command]
        data_args = ['--tessdata-dir', str(self.data)] if self.data else []
        languages = self._run(args + data_args + ['--list-langs'], cancel).splitlines()
        if any(lang not in languages for lang in self.language.split('+')):
            raise ConversionError('Hiányzik a magyar vagy angol OCR-nyelvi adat.')
        # Bound rendered image size to approximately 20 megapixels.
        area = (clip or page.rect).get_area()
        scale = min(300/72, (20_000_000 / max(area, 1)) ** .5)
        import pymupdf
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csGRAY, alpha=False, clip=clip)
        image = Image.frombytes('L', (pix.width, pix.height), pix.samples)
        # Mild contrast correction only when the dynamic range is narrow.
        lo, hi = image.getextrema()
        if hi-lo < 160:
            image = ImageOps.autocontrast(image)
        with tempfile.TemporaryDirectory(prefix='pdf2docx-') as tmp:
            source = Path(tmp)/'page.png'
            image.save(source, dpi=(300, 300))
            text = self._run(args + [str(source), 'stdout'] + data_args +
                             ['-l', self.language, '--dpi', '300', '-c', 'tessedit_create_tsv=1'], cancel)
        result = Page(ocr=True)
        groups = {}
        for row in csv.DictReader(io.StringIO(text), delimiter='\t', quoting=csv.QUOTE_NONE):
            word = row.get('text', '').strip()
            if row.get('level') != '5' or not word:
                continue
            try:
                conf = float(row['conf'])
            except (ValueError, KeyError):
                conf = 0
            result.uncertain_words += conf < 60
            key = (row['block_num'], row['par_num'])
            groups.setdefault(key, []).append(word)
        for words in groups.values():
            result.paragraphs.append(Paragraph([Run(' '.join(words))]))
        if not result.paragraphs:
            raise ConversionError('Az oldalról nem sikerült szöveget felismerni. Ellenőrizze a dokumentumot.')
        return result
