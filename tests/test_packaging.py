import hashlib
from pathlib import Path
import runpy
import zipfile
import importlib.metadata


def test_release_zip_keeps_runtime_and_checksum(tmp_path, monkeypatch):
    module = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'packaging' / 'build_windows.py'))
    make_archive = module['archive']
    monkeypatch.setitem(make_archive.__globals__, 'ROOT', tmp_path)
    monkeypatch.setattr(importlib.metadata, 'distributions', lambda: [])
    app = tmp_path / 'dist' / 'PDF2DOCX'
    (app / '_internal' / 'ocr' / 'tessdata').mkdir(parents=True)
    (app / 'PDF2DOCX.exe').write_bytes(b'synthetic executable fixture')
    (app / '_internal' / 'ocr' / 'tessdata' / 'hun.traineddata').write_bytes(b'synthetic OCR fixture')
    (tmp_path / 'README.md').write_text('Instructions')
    (tmp_path / 'packaging').mkdir()
    (tmp_path / 'packaging' / 'README.md').write_text('Windows requirements')
    archive = Path(make_archive())
    with zipfile.ZipFile(archive) as package:
        names = package.namelist()
        assert 'PDF2DOCX/PDF2DOCX.exe' in names
        assert 'PDF2DOCX/_internal/ocr/tessdata/hun.traineddata' in names
        assert 'PDF2DOCX/README.md' in names
    assert Path(str(archive) + '.sha256').read_text().split()[0] == hashlib.sha256(archive.read_bytes()).hexdigest()
