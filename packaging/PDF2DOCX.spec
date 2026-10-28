# Run on Windows from the repository root: pyinstaller packaging/PDF2DOCX.spec
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

if sys.platform != 'win32':
    raise SystemExit('Windows EXE build requires Windows.')
root = Path(SPECPATH).parent
ocr = root / 'packaging' / 'ocr'
required = ['tesseract.exe', 'tessdata/hun.traineddata', 'tessdata/eng.traineddata', 'LICENSES']
for item in required:
    if not (ocr / item).exists():
        raise SystemExit(f'Missing vetted OCR redistribution resource: {item}')
datas, binaries, hiddenimports = collect_all('tkinterdnd2')
# Include every native OCR dependency from the vetted portable distribution.
for item in ocr.rglob('*'):
    if item.is_file():
        destination = str(Path('ocr') / item.parent.relative_to(ocr))
        if item.suffix.lower() in ('.dll', '.exe'):
            binaries.append((str(item), destination))
        else:
            datas.append((str(item), destination))
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=binaries,
             datas=datas, hiddenimports=hiddenimports, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PDF2DOCX',
          debug=False, strip=False, upx=False, console=False, uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='PDF2DOCX')
