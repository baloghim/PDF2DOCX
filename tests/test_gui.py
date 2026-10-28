"""Real Tk widgets; dialogs are intercepted so tests are noninteractive."""
import os
import time
from types import SimpleNamespace
import pytest
from pdf2docx_app.gui.main_window import Application
from tests_helpers import make_gui_pdf

pytestmark = pytest.mark.skipif(not os.environ.get('DISPLAY') and os.name != 'nt', reason='Graphical display required')


def test_gui_drop_worker_reset_and_errors(tmp_path, monkeypatch):
    messages = []
    monkeypatch.setattr('pdf2docx_app.gui.main_window.messagebox.showinfo', lambda *a, **kw: messages.append(('info', a[1])))
    monkeypatch.setattr('pdf2docx_app.gui.main_window.messagebox.showerror', lambda *a, **kw: messages.append(('error', a[1])))
    app = Application()
    try:
        app.root.update()
        if os.name == 'nt':
            assert app.dnd, 'Native TkDnD did not initialize'
        source = make_gui_pdf(tmp_path/'Árvíz teszt (1).pdf')
        app.drop(SimpleNamespace(data=app.root.tk.call('list', str(source))))
        assert app.busy
        app.accept([tmp_path/'nonexistent.pdf'])  # ignored while busy
        deadline = time.monotonic() + 10
        while app.busy and time.monotonic() < deadline:
            app.root.update()
            time.sleep(.01)
        assert not app.busy
        assert source.with_suffix('.docx').exists()
        assert messages[0][0] == 'info' and len(messages) == 1
        app.drop(SimpleNamespace(data='{a.pdf} {b.pdf}'))
        assert messages[-1][0] == 'error'
        assert not app.busy
        bad = tmp_path/'bad.txt'
        bad.write_text('not PDF')
        app.accept([bad])
        assert 'fájltípus' in messages[-1][1]
        # Ready for a second successful conversion after both errors.
        second = make_gui_pdf(tmp_path/'second.pdf')
        app.accept([second])
        deadline = time.monotonic()+10
        while app.busy and time.monotonic() < deadline:
            app.root.update()
            time.sleep(.01)
        assert not app.busy and second.with_suffix('.docx').exists()
    finally:
        app.root.destroy()
