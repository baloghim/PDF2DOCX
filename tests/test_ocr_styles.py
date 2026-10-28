import io
import csv
import threading
from PIL import Image, ImageDraw, ImageFont
import pytest
from pdf2docx_app.resources import asset_path
from pdf2docx_app.core.ocr_styles import estimate_styles
from pdf2docx_app.core.ocr import parse_tsv
from pdf2docx_app.core.extract import font_emphasis
from pdf2docx_app.core.model import Cancelled


def synthetic_words():
    image = Image.new('L',(1800,600),255)
    draw = ImageDraw.Draw(image)
    records = []
    for line, y, bold, words in [(0,40,False,['Normal','document','regular','reading']),
                                (1,180,True,['Important','heading','emphasis']),
                                (2,340,False,['Accents','glyphs','descenders','together'])]:
        font=ImageFont.truetype(str(asset_path('fonts','Carlito-Bold.ttf' if bold else 'Carlito-Regular.ttf')),50)
        x=50
        for text in words:
            box=draw.textbbox((x,y),text,font=font)
            draw.text((x,y),text,font=font,fill=0)
            records.append(dict(text=text,pixels=(box[0],box[1],box[2]-box[0],box[3]-box[1]),
                                confidence=95,paragraph_key=(line,1),line_key=(line,1,1)))
            x=box[2]+35
    return image,records


def test_ocr_weight_and_size_from_word_images():
    image,records=synthetic_words()
    styles=estimate_styles(records,image,4)
    for record,(size,bold) in zip(records,styles):
        assert abs(size-12.5)<=.5
        assert bold == (record['paragraph_key'][0]==1)


def test_tilt_does_not_inflate_word_font_size():
    image,records=synthetic_words()
    # The paragraph's words follow a tilted baseline; union height is misleading.
    tilted=Image.new('L',image.size,255)
    for i,record in enumerate(records):
        x,y,w,h=record['pixels']
        shift=(i%4)*7
        tilted.paste(image.crop((x,y,x+w,y+h)),(x,y+shift))
        record['pixels']=(x,y+shift,w,h)
    stream=io.StringIO()
    fields=['level','page_num','block_num','par_num','line_num','word_num','left','top','width','height','conf','text']
    writer=csv.DictWriter(stream,fieldnames=fields,delimiter='\t')
    writer.writeheader()
    for i,r in enumerate(records):
        x,y,w,h=r['pixels']; block=r['paragraph_key'][0]+1
        writer.writerow(dict(zip(fields,[5,1,block,1,1,i+1,x,y,w,h,95,r['text']])))
    page=parse_tsv(stream.getvalue(),450,200,4,image=tilted)
    assert all(abs(r.size-12.5)<=.5 for p in page.paragraphs for r in p.runs if r.text.strip())
    assert any(r.bold for p in page.paragraphs for r in p.runs)


def test_style_analysis_is_cancellable():
    image,records=synthetic_words()
    cancel=threading.Event();cancel.set()
    with pytest.raises(Cancelled):
        estimate_styles(records,image,4,cancel)


def test_pdf_font_name_recovers_missing_emphasis_flags():
    assert font_emphasis('ABCDEF+Arial-BoldItalicMT',0)==(True,True)
    assert font_emphasis('TimesNewRomanPS-Semibold',0)==(True,False)
    assert font_emphasis('ArialMT',0)==(False,False)
    assert font_emphasis('Unknown',18)==(True,True)


def test_mixed_line_keeps_only_the_emphasized_word_bold():
    image=Image.new('L',(1800,150),255)
    draw=ImageDraw.Draw(image)
    records=[]
    x=30
    for i,text in enumerate(['Regular','words','include','emphasis','inside','paragraph']):
        bold=i==3
        font=ImageFont.truetype(str(asset_path('fonts','Carlito-Bold.ttf' if bold else 'Carlito-Regular.ttf')),50)
        box=draw.textbbox((x,30),text,font=font)
        draw.text((x,30),text,font=font,fill=0)
        records.append(dict(text=text,pixels=(box[0],box[1],box[2]-box[0],box[3]-box[1]),confidence=95,paragraph_key=(1,1),line_key=(1,1,1)))
        x=box[2]+30
    result=estimate_styles(records,image,4)
    assert [bold for size,bold in result]==[False,False,False,True,False,False]
