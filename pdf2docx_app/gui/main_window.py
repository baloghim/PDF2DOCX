import logging
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ..core.converter import convert, validate_input
from ..core.model import ConversionError, Cancelled


class Application:
    def __init__(self):
        try:
            # The shipped native extension is supported here only on the target OS.
            # Loading it into static Linux Tcl builds can abort the interpreter.
            if os.name != 'nt':
                raise ImportError('Windows native drag-and-drop')
            from tkinterdnd2 import TkinterDnD, DND_FILES
            self.root = TkinterDnD.Tk()
            self.dnd = DND_FILES
        except (ImportError, tk.TclError, RuntimeError):
            if tk._default_root is not None:
                tk._default_root.destroy()
            self.root = tk.Tk()
            self.dnd = None
        self.root.title('PDF2DOCX')
        w, h = 500, 300
        self.root.geometry(f'{w}x{h}+{(self.root.winfo_screenwidth()-w)//2}+{(self.root.winfo_screenheight()-h)//2}')
        self.root.minsize(450, 280)
        self.root.configure(bg='#f5f7fa')
        self.busy = False
        self.closing = False
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.canvas = tk.Canvas(self.root, bg='white', highlightthickness=0, cursor='hand2')
        self.canvas.pack(fill='both', expand=True, padx=24, pady=(24, 10))
        self.canvas.bind('<Configure>', self.draw)
        self.canvas.bind('<Button-1>', self.choose)
        if self.dnd:
            self.canvas.drop_target_register(self.dnd)
            self.canvas.dnd_bind('<<Drop>>', self.drop)
            self.canvas.dnd_bind('<<DropEnter>>', lambda e: self.highlight(True))
            self.canvas.dnd_bind('<<DropLeave>>', lambda e: self.highlight(False))
        self.status = tk.StringVar(value='Egyszerre egy PDF-dokumentum dolgozható fel.')
        ttk.Label(self.root, textvariable=self.status, anchor='center').pack(fill='x', padx=12)
        self.bar = ttk.Progressbar(self.root, mode='determinate')
        self.bar.pack(fill='x', padx=24, pady=(8, 20))
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(100, self.poll)

    def draw(self, event=None):
        c = self.canvas
        c.delete('all')
        w, h = c.winfo_width(), c.winfo_height()
        c.create_rectangle(3, 3, w-3, h-3, dash=(6, 4), outline='#8a9bb0', width=2, tags='border')
        c.create_text(w/2, h/2-25, text='▤', font=('Segoe UI', 30), fill='#3565a1')
        c.create_text(w/2, h/2+25, text='Konvertálás folyamatban…' if self.busy else 'Húzza ide a konvertálandó PDF-fájlt!', font=('Segoe UI', 13), width=w-24, justify='center')

    def highlight(self, active):
        if not self.busy:
            self.canvas.itemconfigure('border', outline='#2563eb' if active else '#8a9bb0')
        return 'copy' if not self.busy else 'refuse_drop'

    def choose(self, event=None):
        if not self.busy:
            path = filedialog.askopenfilename(parent=self.root, title='PDF kiválasztása', filetypes=[('PDF-dokumentum', '*.pdf')])
            if path:
                self.accept([path])

    def drop(self, event):
        if not self.busy:
            try:
                self.accept(self.root.tk.splitlist(event.data))
            except tk.TclError:
                messagebox.showerror('PDF2DOCX', 'A fájllista nem értelmezhető.', parent=self.root)
        return 'copy'

    def confirm_overwrite(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('PDF2DOCX')
        dialog.transient(self.root)
        dialog.resizable(False, False)
        ttk.Label(dialog, text='Ebben a mappában már létezik ilyen nevű Word-dokumentum.\nSzeretné felülírni?', padding=20).pack()
        answer = [False]
        def finish(value):
            answer[0] = value
            dialog.destroy()
        row = ttk.Frame(dialog, padding=12)
        row.pack()
        ttk.Button(row, text='Felülírás', command=lambda: finish(True)).pack(side='left', padx=6)
        ttk.Button(row, text='Mégse', command=lambda: finish(False)).pack(side='left', padx=6)
        dialog.bind('<Escape>', lambda e: finish(False))
        dialog.grab_set()
        self.root.wait_window(dialog)
        return answer[0]

    def accept(self, paths):
        if self.busy:
            return
        try:
            source = validate_input(paths)
        except ConversionError as error:
            messagebox.showerror('PDF2DOCX', str(error), parent=self.root)
            return
        # Gate before modal dialogs to prevent reentrant drops.
        self.busy = True
        overwrite = source.with_suffix('.docx').exists()
        if overwrite and not self.confirm_overwrite():
            self.reset()
            return
        self.cancel.clear()
        self.draw()
        self.status.set('Dokumentum elemzése…')
        def work():
            try:
                result = convert(source, overwrite=overwrite, cancel=self.cancel,
                                 progress=lambda *args: self.events.put(('progress', args)))
                self.events.put(('done', result))
            except ConversionError as error:
                logging.getLogger('pdf2docx').warning('conversion_failure category=%s', type(error).__name__)
                self.events.put(('error', error))
            except Exception as error:
                logging.getLogger('pdf2docx').error('worker_failure category=%s', type(error).__name__)
                self.events.put(('error', ConversionError('Váratlan feldolgozási hiba történt.')))
        threading.Thread(target=work, daemon=False).start()

    def reset(self):
        self.busy = False
        self.bar['value'] = 0
        self.status.set('Egyszerre egy PDF-dokumentum dolgozható fel.')
        self.draw()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'progress':
                    stage, current, total = value
                    self.status.set(f'{stage} {current} / {total} oldal feldolgozva')
                    self.bar['maximum'], self.bar['value'] = total, current
                else:
                    if self.closing:
                        self.root.destroy()
                        return
                    if kind == 'done':
                        warning = '\nAz OCR eredményét ellenőrizze.' if value.ocr_pages else ''
                        if value.uncertain_words:
                            warning += f' {value.uncertain_words} bizonytalan szó.'
                        messagebox.showinfo('PDF2DOCX', 'A konvertálás sikeresen befejeződött!\n\nA szerkeszthető Word-dokumentumot az eredeti PDF-fájl mellé mentettük.\n' + value.path.name + warning, parent=self.root)
                    elif not isinstance(value, Cancelled):
                        messagebox.showerror('PDF2DOCX', str(value), parent=self.root)
                    self.reset()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def close(self):
        if self.busy:
            if messagebox.askokcancel('PDF2DOCX', 'Megszakítja a feldolgozást és bezárja az alkalmazást?', parent=self.root):
                self.closing = True
                self.cancel.set()
                self.status.set('Feldolgozás leállítása…')
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()
