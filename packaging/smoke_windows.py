"""Test the executable after unpacking the actual release ZIP."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

if os.name != 'nt':
    raise SystemExit('Windows is required.')
root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='PDF2DOCX ZIP teszt ') as tmp:
    tmp = Path(tmp)
    with zipfile.ZipFile(root / 'dist' / 'PDF2DOCX-Windows-x64.zip') as archive:
        archive.extractall(tmp)
    report = tmp / 'verification.json'
    # Remove development OCR/Python paths: the executable must use its own bundle.
    environment = dict(os.environ)
    for key in ('TESSDATA_PREFIX', 'PYTHONPATH', 'PYTHONHOME'):
        environment.pop(key, None)
    environment['PATH'] = os.path.join(os.environ['WINDIR'], 'System32')
    executable = tmp / 'PDF2DOCX' / 'PDF2DOCX.exe'
    result = subprocess.run([str(executable), '--verify-runtime', str(report)], env=environment, cwd=tmp, timeout=180)
    if result.returncode or not report.exists():
        raise SystemExit('Packaged executable verification failed')
    data = json.loads(report.read_text(encoding='utf-8'))
    if not data.get('ok'):
        raise SystemExit(f'Packaged verification failed: {data}')
    print('Packaged EXE: TkDnD, digital PDF and Hungarian OCR passed.')
