# Windows kiadás – kötelező ellenőrzések

Windows x64 gépen, **64 bites Python 3.11** használatával:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m PyInstaller --clean --noconfirm packaging/PDF2DOCX.spec
```

A build előtt a `packaging/ocr/` könyvtárba másolandó egy jogszerűen terjeszthető,
Windows 1607-en ellenőrzött, hordozható Tesseract kiadás teljes futtatókörnyezete:
`tesseract.exe`, minden szükséges DLL, `tessdata/hun.traineddata`,
`tessdata/eng.traineddata`, és `LICENSES/` az összes komponens licencével,
szerzői jogi megjegyzéseivel és szükséges terjesztési anyagaival.
**Ilyen Windows bináriskészletet ez a repository nem tartalmaz, és nem minősít ellenőrzöttnek.**
A build szándékosan leáll, ha a kötelező erőforrások hiányoznak.
A spec a TkDnD adatokat és natív binárisokat is gyűjti; a Tesseract konzolja rejtett.

Terjesztés: a teljes `dist/PDF2DOCX/` mappát kell ZIP-be csomagolni.
Az EXE az `_internal` könyvtár nélkül nem használható. Nem kell MSI vagy adminjog.
A csomagolt alkalmazás elsőként az `_internal/ocr/tesseract.exe` fájlt használja.

## Kompatibilitási kiadási kapu

A rögzített verziók Python 3.11 alatt Linuxon teszteltek. A Windows 1607,
MSVC/UCRT, Tcl/Tk, TkDnD, MuPDF, Pillow, lxml és Tesseract natív DLL-ek
kompatibilitása **nincs igazolva**. A Windows kiadás mindaddig nem kész,
amíg az alábbiak nem teljesülnek valódi Windows 10 Enterprise 2016 LTSB
1607 build 14393.9512 gépen, normál felhasználóval:

- OS és processzorarchitektúra ellenőrzése (pl. PowerShell `Get-CimInstance Win32_OperatingSystem`).
- Indulás Python és külön Tesseract telepítése nélkül; nincs hiányzó DLL.
- Intézőből behúzás, magyar és szóközös fájlnevek, kattintásos tartalék.
- Szöveges, szkennelt, vegyes és korábbi OCR-réteges iratok, magyar OCR.
- Megnyitható/szerkeszthető Word-kimenet, kézi összevetés az eredetivel.
- Felülírás, zárolt Word-fájl, nincs írásjog, megszakítás, ismételt feldolgozás.
- A GUI és a háttérszál stabilitása; teljes terjesztési mappa másik gépre másolva.

Windows 11 teszt ezt nem helyettesíti. Windows EXE Linuxon nem készült.
A natív összetevőket csak hiteles forrásból, ellenőrzött aláírással/hash-sel vedd át;
a gépen ténylegesen induló kiadások adatait és ellenőrzőösszegeit archiváld a kiadáshoz.

## Licencek

A PyMuPDF/MuPDF AGPL-3.0 vagy kereskedelmi licencelésű: vállalati terjesztés előtt
válassz megfelelő licencelési módot; ez a projekt nem ad automatikus felmentést.
Tesseract és tessdata: Apache-2.0; a DLL-függőségeknek külön licenceik lehetnek.
Python, Tcl/Tk, TkDnD, python-docx (MIT), Pillow (HPND), lxml (BSD és natív
függőségek), PyInstaller (GPL bootloader kivétellel) licencanyagait is meg kell őrizni.
A ZIP a felhasznált conda-csomagok leltárát, az érintett natív könyvtárak,
a Python/Tcl/Tk és a Python-csomagok licencanyagait is tartalmazza.
Források: https://pymupdf.readthedocs.io/en/latest/about.html ,
https://github.com/tesseract-ocr/tesseract , https://github.com/tesseract-ocr/tessdata_fast ,
https://pyinstaller.org/en/v6.10.0/usage.html , https://www.python.org/downloads/windows/ .

## Automatizált ZIP és GitHub-letöltés

A `.github/workflows/windows-release.yml` a `main` ág frissítésekor, illetve kézzel
indítva Windows 2022 runneren dolgozik. Python 3.11.9-et és conda-forge Tesseract
5.3.3-at telepít, összegyűjti a natív DLL-eket és licenceket, majd ellenőrzött hashű
magyar nyelvi adatot ad hozzá. A conda a saját csomagellenőrzését használja.
Hiányzó OCR, angol modell vagy natív licencszöveg esetén a build leáll.

A `packaging/build_windows.py` előállítja a PyInstaller onedir csomagot, a teljes
`PDF2DOCX-Windows-x64.zip` fájlt és annak SHA-256 ellenőrzőösszegét. A Windows
pytest után a `packaging/smoke_windows.py` egy külön mappába kibontja a ZIP-et,
és a becsomagolt EXE-n ellenőrzi a natív TkDnD-t, a digitális PDF-konvertálást és
a magyar OCR-t. Ekkor a fejlesztői Python/OCR elérési útjai nem használhatók.

Csak sikeres build és tesztek után kerülnek a fájlok a `windows-preview`
előzetes GitHub Release mellékletei közé. A README állandó letöltési linkje ide mutat.
A build workflow tokenjének `contents: write` jogosultság szükséges a kiadási jobban.
A [Windows build és közzététel sikeresen lefutott](https://github.com/baloghim/PDF2DOCX/actions/runs/40658728166);
a ZIP a README-ből letölthető. A Windows Server 2022 teszt nem helyettesíti
a kötelező Windows 1607 célgépes tesztet; ezt a kiadás előzetes jelölése is tükrözi.
