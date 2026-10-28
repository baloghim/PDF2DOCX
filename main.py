import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def main():
    folder = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'state')) / 'PDF2DOCX'
    try:
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(folder / 'application.log', maxBytes=200_000, backupCount=2, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger = logging.getLogger('pdf2docx')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    except OSError:
        pass
    from pdf2docx_app.gui.main_window import Application
    Application().run()


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-runtime':
        from pdf2docx_app.verification import verify
        raise SystemExit(verify(sys.argv[2]))
    main()
