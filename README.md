# PDF2DOCX

## Windows-csomag letöltése

**0.2.0 – formázásmegőrző frissítés.**

**[PDF2DOCX Windows x64 ZIP letöltése](https://github.com/baloghim/PDF2DOCX/releases/download/windows-preview/PDF2DOCX-Windows-x64.zip)**

A teljes, OCR-motort és magyar nyelvi adatokat is tartalmazó csomag körülbelül **57 MB**.
Állapot: [Windows ZIP build](https://github.com/baloghim/PDF2DOCX/actions/workflows/windows-release.yml).

1. Töltse le a ZIP-et és bontsa ki a **teljes** tartalmát egy írható mappába.
2. Nyissa meg a `PDF2DOCX` mappát és indítsa el a `PDF2DOCX.exe` fájlt.
3. Húzza az ablakba a PDF-et. A Word-fájl az eredeti PDF mellé kerül.

Nem kell Python, külön OCR-telepítés, MSI vagy rendszergazdai jogosultság.
Az `_internal` mappát ne törölje, és az EXE-t ne másolja ki önmagában.
Ez **előzetes kiadás**: a Windows 10 Enterprise 2016 LTSB 1607 kompatibilitása
még nincs igazolva. A ZIP mellett [SHA-256 ellenőrzőösszeg](https://github.com/baloghim/PDF2DOCX/releases/download/windows-preview/PDF2DOCX-Windows-x64.zip.sha256) is készül.


Magyar nyelvű, helyben működő Python/Tkinter asztali alkalmazás. Egy PDF behúzása
után szerkeszthető Word-bekezdéseket hoz létre az eredeti fájl mellé. Nincs szerver,
adatbázis, külső OCR/API, telemetria vagy dokumentumfeltöltés.

## Használat

Indítás → PDF behúzása (vagy kattintás a fogadóterületre) → feldolgozás → DOCX → OK.
Egyszerre egy dokumentum fogadható. A cél azonos nevű `.docx`; meglévő fájlhoz
felülírási engedély szükséges. Az új dokumentum ellenőrzött ideiglenes fájlból,
atomikusan kerül a helyére; sikertelen mentés nem cseréli le a régi dokumentumot.
Bezáráskor a feldolgozás megszakítható, az OCR-folyamat leáll, az átmeneti fájl törlődik.

## Fejlesztői telepítés

Python **3.11**, Tcl/Tk **8.6** grafikus környezet, x64 az elsődleges tervezett architektúra.
A célgépek tényleges architektúrája külön ellenőrizendő.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python main.py
```

Linuxon ugyanez `python3.11 -m venv .venv`, majd `.venv/bin/python` használatával.
A GUI-hoz grafikus munkamenet kell. A felhőkörnyezet Python 3.11.17/Tk 9-et használ (kattintásos fájlválasztó);
a legújabb uv Python 3.11.17/Tk 9 alatt a TkDnD nem töltődött be.
Windows alatt hivatalos Python 3.11/Tk 8.6 kiadással kell buildelni. Ha a TkDnD nem tölthető be, a kattintásos
fájlválasztó továbbra is rendelkezésre áll. A projekt belső csomagneve
`pdf2docx_app`, így nem ütközik a külső `pdf2docx` csomaggal.

Fejlesztéskor Tesseract 5 szükséges a PATH-on, magyar és angol nyelvi adatokkal.
Linuxon a disztribúció `tesseract-ocr`, `tesseract-ocr-hun`, `tesseract-ocr-eng`
csomagjai használhatók. Ellenőrzés: `tesseract --list-langs` (`hun`, `eng`).
Alternatív adatkönyvtárhoz fejlesztéskor `TESSDATA_PREFIX` állítható be.
A végfelhasználói Windows csomagban mindez beágyazott; nincs külön telepítés.
A Windows build leírása: [packaging/README.md](packaging/README.md).

## Feldolgozás és minőségi korlátok

- A motor a GUI nélkül használható: `from pdf2docx_app.core.converter import convert`;
  `result = convert('irat.pdf')`. `overwrite=True` kizárólag tudatos engedély után.
- Oldalanként közvetlen szövegkinyerés vagy 300 DPI körüli, legfeljebb 20 MP OCR.
- Heurisztika: az üres/alphanumerikus jelet nem tartalmazó, illetve legalább 5%
  helyettesítő vagy vezérlőkaraktert tartalmazó szövegréteg helyett OCR történik.
  Ez nem nyelvi minőségellenőrzés: egy hibás, de olvasható OCR-réteg átcsúszhat.
- Magyar+angol OCR, szó-konfidenciákból belső bizonytalanságszám. Nincs tartalmi átírás,
  szótáras javítás vagy generatív AI. Az eredményt mindig össze kell vetni az eredetivel.
- Közeli sorok blokkon belül összeolvadnak; nagyobb térköz, címsor vagy listajel új
  bekezdés. A literális kötőjelek megmaradnak; csak explicit lágy elválasztás egyesül.
- A 0.2.0 változat átveszi a PDF betűméreteit, a szokásos betűcsaládok megfelelőjét,
  a félkövér/dőlt kiemeléseket, színeket és felső indexeket. A középre, jobbra,
  balra és sorkizártan igazított bekezdéseket geometriai heurisztikákkal ismeri fel.
- A behúzások, első sorok, sorközök, bekezdésközök, rövid címzésblokkok sortörései,
  oldalméretek és a PDF-oldalak közötti törések megmaradnak. Normál Word-bekezdések
  készülnek; nincsenek soronkénti szövegdobozok vagy a szöveget helyettesítő oldalképek.
- A számozott és pontozott listák Word-listaként készülnek, a forrás kezdőszámával.
  Az egyéb listajelek és összetett számozások szövegként maradnak meg.
- Az egyszerű rácsos táblák a megfelelő helyre kerülnek, oszlopszélességükkel együtt.
  A kis raszteres képek, logók a szöveghez viszonyított sorrendet és méretet követik.
- Az OCR is felhasználja a felismert sorok és szavak helyét: igazítást, behúzást,
  térközt és becsült betűméretet állít vissza. A szkennelt képből a betűcsalád,
  félkövér/dőlt kiemelés és táblázatszerkezet jelenleg nem állítható vissza megbízhatóan.
- A formázás helyreállítása heurisztikus. Összetett hasábok, fejlécek/láblécek,
  vektoros grafikák, szegélyek és összetett táblák további kézi javítást igényelhetnek.
  A PDF-től eltérő Word-fontmetrikák miatt a tördelés és oldalszám eltérhet.
- Szöveges oldalon a legalább 25% oldalterületű, meglévő szöveggel nem átfedő képek
  külön OCR-t kapnak. Az átfedő vagy kisebb képekben lévő további szöveg kimaradhat.
  Üres/szöveg nélkül maradó OCR-oldal hibát jelez; nem hagyja ki csendben.
- A DOCX visszanyitása szerkezeti ellenőrzés, nem igazolja a szöveg pontosságát.
- Egy OCR-hívás 180 másodperc után leáll. Nagy PDF feldolgozása memóriaigényes lehet;
  a Word-modell a feldolgozás végéig memóriában marad.

## Adatvédelem

A bemeneti PDF változatlan. OCR-képek rendszer-ideiglenes könyvtárban, végső DOCX
átmeneti fájlja a célkönyvtárban keletkezik; normál hibánál és megszakításnál törlődnek.
Áramkimaradás/folyamatkilövés után rendszer-ideiglenes maradvány előfordulhat.
A rotált napló helye Windows alatt `%LOCALAPPDATA%/PDF2DOCX/application.log`;
csak hibakategória és időpont kerül bele, dokumentumszöveg, útvonal, OCR stderr nem.

## Tesztek

```sh
.venv/bin/python -m pytest -q
```

Az integrációs tesztek valódi Tesseractot, `hun`+`eng` nyelvet és a repositoryban mellékelt DejaVu Sans
betűtípust használják (`tests/assets`, licenccel együtt). A személyes adat nélküli PDF-ek futáskor készülnek.
A tesztfont helyét a `PDF2DOCX_TEST_FONT` környezeti változóval lehet megadni.
Szöveges/többoldalas/vegyes PDF, magyar ékezetek, számozás, szerkeszthető DOCX,
forrás hash, jelszó, hibás bemenet, mentési hiba, felülírás, versenyhelyzet,
megszakítás és Tcl-fájllista szerepelnek a tesztek között.
A szintetikus, jó minőségű magyar OCR-mintán a `hun` és `hun+eng` eredményét
azonos referenciaszöveghez hasonlítjuk; ez nem reprezentatív hivatalos iratkorpusz.

**Állapot:** letölthető Windows x64 előzetes kiadás. Linux/Python 3.11 alatt is tesztelt motor.
A virtuális Linux kijelzőn a GUI munkafolyamata tesztelt. A TkDnD natív betöltése
a hordozható Linux Tcl környezetben nem működött, ezért Linuxon kizárólag
a kattintásos fájlválasztó aktív. A drag-and-drop natív része Windowsra korlátozott;
a fájllista és drop-esemény kezelése automatikusan tesztelt.
A [sikeres Windows Server 2022 buildben](https://github.com/baloghim/PDF2DOCX/actions/runs/40658728166)
22 automatizált teszt, valamint a ZIP-ből kibontott EXE natív TkDnD-, digitális PDF-
és magyar OCR-ellenőrzése is sikerült.
Az Intézőből történő tényleges behúzás kézi tesztje és a Windows 10 Enterprise
2016 LTSB 1607 build 14393.9512 kompatibilitási teszt továbbra is hátravan.
A Windows Server 2022 eredménye nem igazolja a Windows 1607 kompatibilitását.
A Windows kiadási ellenőrzőlista és a licenckövetelmények a csomagolási leírásban vannak.

A jelenlegi felhőkörnyezetben a teljes GUI-teszt virtuális kijelzővel:
` .venv/bin/python /workspace/pdf2docx-tools/run-tests.py ` (a repository gyökeréből).
A runner csak a saját Xvfb-folyamatát indítja és állítja le.
