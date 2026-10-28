"""Assemble the Windows OCR runtime from a conda-forge environment and build ZIP."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
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
    # Bundle the PE dependency closure, not unrelated DLLs from the conda Python.
    import pefile
    available = {p.name.lower(): p for p in binaries.iterdir() if p.is_file()}
    selected = set()
    pending = ['tesseract.exe']
    while pending:
        name = pending.pop().lower()
        if name in selected:
            continue
        if name not in available:
            raise RuntimeError(f'Missing OCR binary: {name}')
        selected.add(name)
        path = available[name]
        with pefile.PE(str(path), fast_load=True) as pe:
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'], pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT']])
            for entry in list(getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])) + list(getattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT', [])):
                dependency = entry.dll.decode('ascii').lower()
                if dependency in available and dependency not in selected:
                    pending.append(dependency)
        shutil.copy2(path, destination / path.name)
    licenses = destination / 'LICENSES'
    licenses.mkdir()
    manifest = []
    for metadata in sorted((prefix / 'conda-meta').glob('*.json')):
        package = json.loads(metadata.read_text(encoding='utf-8'))
        # Only packages contributing files to the redistributed binary directory.
        if not any(f.lower().startswith('library/bin/') and f.rsplit('/', 1)[-1].lower() in selected for f in package.get('files', [])):
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
    import tomllib
    project_file = ROOT / 'pyproject.toml'
    app_version = tomllib.loads(project_file.read_text(encoding='utf-8'))['project']['version'] if project_file.exists() else 'unknown'
    (folder / 'BUILD-INFO.json').write_text(json.dumps({'app_version': app_version, 'source_commit': os.environ.get('GITHUB_SHA'), 'target': 'Windows x64', 'windows_1607_verified': False}, indent=2), encoding='utf-8')
    for filename in ('README.md',):
        shutil.copy2(ROOT / filename, folder / filename)
    shutil.copy2(ROOT / 'packaging' / 'README.md', folder / 'WINDOWS-KIADAS.md')
    # Include Python package license metadata in addition to PyInstaller runtime files.
    import importlib.metadata
    notices = folder / 'LICENSES' / 'python-packages'
    notices.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        python_root = Path(sys.base_prefix)
        required_notices = {
            'Python-LICENSE.txt': python_root / 'LICENSE.txt',
            'Tcl-license.terms': python_root / 'tcl' / 'tcl8.6' / 'license.terms',
            'Tk-license.terms': python_root / 'tcl' / 'tk8.6' / 'license.terms',
        }
        import tkinter
        tk = tkinter.Tk()
        tk.withdraw()
        try:
            versions = {'Tcl-license.terms': ('tcl', tk.tk.call('info', 'patchlevel')),
                        'Tk-license.terms': ('tk', tk.tk.call('package', 'provide', 'Tk'))}
        finally:
            tk.destroy()
        for name, source in required_notices.items():
            if source.is_file():
                shutil.copy2(source, notices.parent / name)
            elif name in versions:
                component, version = versions[name]
                tag = 'core-' + str(version).replace('.', '-')
                url = f'https://raw.githubusercontent.com/tcltk/{component}/{tag}/license.terms'
                with urllib.request.urlopen(url, timeout=60) as response:
                    (notices.parent / name).write_bytes(response.read())
            else:
                raise RuntimeError(f'Missing Python redistribution license: {name}')
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
    try:
        main()
    except Exception:
        # This build uses only public dependencies, no user documents or secrets.
        message = traceback.format_exc().replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::error title=Windows packaging failure::' + message, flush=True)
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a', encoding='utf-8') as report:
                report.write('## Windows packaging failure\n\n```text\n' + traceback.format_exc() + '\n```\n')
        raise
