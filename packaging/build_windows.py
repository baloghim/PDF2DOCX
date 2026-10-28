"""Assemble the Windows OCR runtime from a conda-forge environment and build ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def download(url, target, expected):
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError(f'Checksum mismatch: {target.name}')
    target.write_bytes(data)


def assemble(prefix, caches):
    destination = ROOT / 'packaging' / 'ocr'
    if destination.exists():
        raise RuntimeError('OCR staging directory already exists; use a clean checkout.')
    destination.mkdir()
    binaries = prefix / 'Library' / 'bin'
    for path in binaries.iterdir():
        if path.suffix.lower() == '.dll' or path.name.lower() == 'tesseract.exe':
            shutil.copy2(path, destination / path.name)
    if not (destination / 'tesseract.exe').is_file():
        raise RuntimeError('Conda environment does not contain tesseract.exe')
    licenses = destination / 'LICENSES'
    licenses.mkdir()
    manifest = []
    for metadata in sorted((prefix / 'conda-meta').glob('*.json')):
        package = json.loads(metadata.read_text(encoding='utf-8'))
        # Only packages contributing files to the redistributed binary directory.
        if not any(f.lower().startswith('library/bin/') and f.lower().endswith(('.dll', '/tesseract.exe')) for f in package.get('files', [])):
            continue
        key = metadata.stem
        found = False
        for cache in caches:
            source = cache / key / 'info' / 'licenses'
            if source.is_dir() and any(source.rglob('*')):
                shutil.copytree(source, licenses / key, dirs_exist_ok=True)
                found = True
                break
        if not found:
            raise RuntimeError(f'Missing redistribution license files for {key}')
        manifest.append({k: package.get(k) for k in ('name', 'version', 'build', 'channel', 'url', 'sha256', 'md5', 'license')})
    (licenses / 'conda-packages.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    data = destination / 'tessdata'
    data.mkdir()
    download('https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/hun.traineddata', data / 'hun.traineddata',
             '35067e7cfe102dcdc953f9a758fdfaa6296b17a1ee6d874ee780fa306430b9fb')
    # Reuse the conda-provided English model, verified by conda's package checksums.
    candidates = list(prefix.rglob('eng.traineddata'))
    if len(candidates) != 1:
        raise RuntimeError('Expected exactly one conda English OCR model')
    shutil.copy2(candidates[0], data / 'eng.traineddata')
    # License accompanying the pinned Hungarian tessdata model.
    with urllib.request.urlopen('https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/LICENSE', timeout=60) as response:
        (licenses / 'tessdata_fast-LICENSE.txt').write_bytes(response.read())
    subprocess.run([str(destination / 'tesseract.exe'), '--tessdata-dir', str(data), '--list-langs'], check=True)
    return destination


def archive():
    folder = ROOT / 'dist' / 'PDF2DOCX'
    for filename in ('README.md',):
        shutil.copy2(ROOT / filename, folder / filename)
    shutil.copy2(ROOT / 'packaging' / 'README.md', folder / 'WINDOWS-KIADAS.md')
    # Include Python package license metadata in addition to PyInstaller runtime files.
    import importlib.metadata
    notices = folder / 'LICENSES' / 'python-packages'
    notices.mkdir(parents=True, exist_ok=True)
    for dist in importlib.metadata.distributions():
        for item in dist.files or []:
            if '.dist-info/' in str(item) and any(x in item.name.lower() for x in ('license', 'copying', 'notice', 'metadata')):
                source = Path(dist.locate_file(item))
                target = notices / str(item)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    output = shutil.make_archive(str(ROOT / 'dist' / 'PDF2DOCX-Windows-x64'), 'zip', folder.parent, folder.name)
    checksum = hashlib.sha256(Path(output).read_bytes()).hexdigest()
    Path(output + '.sha256').write_text(f'{checksum}  {Path(output).name}\n', encoding='ascii')
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ocr-prefix', required=True, type=Path)
    parser.add_argument('--conda-info', required=True, type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        raise SystemExit('This build must run on Windows.')
    info = json.loads(args.conda_info.read_text(encoding='utf-8-sig'))
    assemble(args.ocr_prefix, [Path(p) for p in info['pkgs_dirs']])
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', 'packaging/PDF2DOCX.spec'], cwd=ROOT, check=True)
    print(archive())


if __name__ == '__main__':
    main()
