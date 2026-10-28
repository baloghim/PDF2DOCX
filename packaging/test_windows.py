"""Run Windows release checks and expose actionable public annotations."""
from pathlib import Path
import subprocess
import os
import traceback
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
os.environ['PYTHONIOENCODING'] = 'utf-8'


def annotation(message):
    message = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=Windows release test::' + message, flush=True)


def main():
    report = Path('windows-tests.xml')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', f'--junitxml={report}'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    print(result.stdout, flush=True)
    if result.returncode:
        if report.exists():
            for case in ET.parse(report).iter('testcase'):
                for kind in ('failure', 'error'):
                    for failure in case.findall(kind):
                        annotation(case.get('name', '') + '\n' + (failure.text or failure.get('message', ''))[-6000:])
        else:
            annotation(result.stdout[-6000:])
        return result.returncode
    result = subprocess.run([sys.executable, 'packaging/smoke_windows.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    print(result.stdout, flush=True)
    if result.returncode:
        annotation(result.stdout[-6000:])
    return result.returncode


if __name__ == '__main__':
    try:
        code = main()
    except Exception:
        annotation(traceback.format_exc())
        code = 1
    raise SystemExit(code)
