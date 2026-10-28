import pymupdf


def make_gui_pdf(path):
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), 'GUI conversion test')
        doc.save(path)
    return path
