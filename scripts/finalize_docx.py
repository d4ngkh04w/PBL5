"""
Script dùng python-docx + lxml XML manipulation để:
1. Thiết lập lề trang (2-2-3-2 cm) cho toàn bộ tài liệu
2. Thêm Section Break (Next Page) trước các Heading 1 quan trọng
3. Thêm số trang vào footer (trang bìa không có, phần mở đầu số La Mã, chương số Ả Rập)
4. Chèn TOC placeholder (field XML)
5. Lưu thành BaoCao_PBL5_Final_Formatted.docx
Người dùng cần mở Word và nhấn Ctrl+A > F9 để cập nhật TOC, LOF, LOT.
"""
import copy
import os
from docx import Document
from docx.shared import Pt, Cm, Emu
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement
from lxml import etree

INPUT = "BaoCao_PBL5_Final_Formatted_temp.docx"
OUTPUT = "BaoCao_PBL5_Final_Formatted.docx"

# ---- cm helpers ----
def cm_to_emu(cm_val):
    return int(cm_val * 914400 / 100 * 10)  # 1 cm = 360000 EMU

def cm_to_twips(cm_val):
    # 1 cm = 567 twips
    return int(cm_val * 567)

# ---- XML helpers ----
def make_element(tag, attribs=None, nsmap_=None):
    el = OxmlElement(tag)
    if attribs:
        for k, v in attribs.items():
            el.set(k, v)
    return el

def page_margin_sectPr(top_cm=2, bottom_cm=2, left_cm=3, right_cm=2):
    """Return a <w:sectPr> element with A4 page size and specified margins."""
    sectPr = OxmlElement('w:sectPr')
    # A4 paper size: width=11906 twips (21cm), height=16838 twips (29.7cm)
    pgSz = OxmlElement('w:pgSz')
    pgSz.set(qn('w:w'), '11906')
    pgSz.set(qn('w:h'), '16838')
    pgSz.set(qn('w:code'), '9')  # A4
    sectPr.append(pgSz)
    
    pgMar = OxmlElement('w:pgMar')
    pgMar.set(qn('w:top'), str(cm_to_twips(top_cm)))
    pgMar.set(qn('w:right'), str(cm_to_twips(right_cm)))
    pgMar.set(qn('w:bottom'), str(cm_to_twips(bottom_cm)))
    pgMar.set(qn('w:left'), str(cm_to_twips(left_cm)))
    pgMar.set(qn('w:header'), '720')
    pgMar.set(qn('w:footer'), '720')
    pgMar.set(qn('w:gutter'), '0')
    sectPr.append(pgMar)
    return sectPr

def make_page_num_footer(numFmt='decimal', start=1, alignment='center'):
    """Return a <w:ftr> element with centered page number."""
    ftr = OxmlElement('w:ftr')
    p = OxmlElement('w:p')
    pPr = OxmlElement('w:pPr')
    jc = OxmlElement('w:jc')
    jc.set(qn('w:val'), alignment)
    pPr.append(jc)
    rPr = OxmlElement('w:rPr')
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    rPr.append(rFonts)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), '24')
    rPr.append(sz)
    pPr.append(rPr)
    p.append(pPr)
    
    r = OxmlElement('w:r')
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    r.append(fldChar1)
    p.append(r)
    
    r2 = OxmlElement('w:r')
    instrText = OxmlElement('w:instrText')
    instrText.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    instrText.text = f' PAGE \\* {numFmt.upper()} '
    r2.append(instrText)
    p.append(r2)
    
    r3 = OxmlElement('w:r')
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    r3.append(fldChar2)
    p.append(r3)
    
    ftr.append(p)
    return ftr

def make_empty_footer():
    """Return an empty footer (no page number)."""
    ftr = OxmlElement('w:ftr')
    p = OxmlElement('w:p')
    ftr.append(p)
    return ftr

def add_section_to_paragraph(para_el, sectPr):
    """Insert sectPr into paragraph's pPr (creates section break at end of paragraph)."""
    pPr = para_el.find(qn('w:pPr'))
    if pPr is None:
        pPr = OxmlElement('w:pPr')
        para_el.insert(0, pPr)
    
    # Remove existing sectPr if any
    existing = pPr.find(qn('w:sectPr'))
    if existing is not None:
        pPr.remove(existing)
    pPr.append(sectPr)

def make_section_break_sectPr(break_type='nextPage', top_cm=2, bottom_cm=2, left_cm=3, right_cm=2, 
                               footer_type=None, numFmt='decimal', start_num=1):
    """Create a sectPr with optional footer."""
    sectPr = page_margin_sectPr(top_cm, bottom_cm, left_cm, right_cm)
    
    pgNumType = OxmlElement('w:pgNumType')
    pgNumType.set(qn('w:fmt'), numFmt)
    pgNumType.set(qn('w:start'), str(start_num))
    sectPr.append(pgNumType)
    
    type_el = OxmlElement('w:type')
    type_el.set(qn('w:val'), break_type)
    sectPr.insert(0, type_el)
    
    if footer_type:
        # Add footer reference and content
        footerRef = OxmlElement('w:footerReference')
        footerRef.set(qn('w:type'), 'default')
        # Footer content will be set in the relationships
        sectPr.append(footerRef)
        
    return sectPr

def add_toc_field(doc, insert_before_para_idx):
    """Insert a TOC field paragraph at the given index."""
    # Create TOC paragraph with field
    toc_p = OxmlElement('w:p')
    toc_r = OxmlElement('w:r')
    
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    toc_r.append(fldChar1)
    toc_p.append(toc_r)
    
    toc_r2 = OxmlElement('w:r')
    instrText = OxmlElement('w:instrText')
    instrText.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    instrText.text = ' TOC \\o "1-3" \\h \\z \\u '
    toc_r2.append(instrText)
    toc_p.append(toc_r2)
    
    toc_r3 = OxmlElement('w:r')
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    toc_r3.append(fldChar2)
    toc_p.append(toc_r3)
    
    body = doc.element.body
    # Insert after index
    paras = body.findall(qn('w:p'))
    if insert_before_para_idx < len(paras):
        ref_para = paras[insert_before_para_idx]
        body.insert(list(body).index(ref_para), toc_p)

def finalize_document():
    doc = Document(INPUT)
    body = doc.element.body
    paragraphs = doc.paragraphs
    
    print(f"Document loaded: {len(paragraphs)} paragraphs")
    
    # ---- Phase 1: Fix ALL normal paragraphs' font (ensure Times New Roman) ----
    for para in doc.paragraphs:
        for run in para.runs:
            if not run.font.name:
                run.font.name = 'Times New Roman'
        # Table cells
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for run in para.runs:
                        if not run.font.name:
                            run.font.name = 'Times New Roman'
    
    # ---- Phase 2: Fix table widths to fit page width ----
    # Content width = 21cm - 3cm - 2cm = 16cm = 9072 twips
    content_width_twips = 9072
    for table in doc.tables:
        tbl = table._tbl
        tblPr = tbl.find(qn('w:tblPr'))
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl.insert(0, tblPr)
        # Set table width to 100%
        tblW = tblPr.find(qn('w:tblW'))
        if tblW is None:
            tblW = OxmlElement('w:tblW')
            tblPr.append(tblW)
        tblW.set(qn('w:w'), str(content_width_twips))
        tblW.set(qn('w:type'), 'dxa')
        
        # Remove fixed cell widths to allow auto
        tblLayout = tblPr.find(qn('w:tblLayout'))
        if tblLayout is None:
            tblLayout = OxmlElement('w:tblLayout')
            tblPr.append(tblLayout)
        tblLayout.set(qn('w:type'), 'autofit')

    # ---- Phase 3: Identify special Heading 1 paragraphs ----
    # Section markers (searching in order of appearance in document)
    COVER_END_TITLE = None  # After first H1 heading
    ABSTRACT_TITLE = "TÓM TẮT ĐỒ ÁN"
    CHAPTER1_TITLE = "CHƯƠNG 1: GIỚI THIỆU"
    REFERENCES_TITLE = "TÀI LIỆU THAM KHẢO"
    APPENDIX_TITLE = "PHỤ LỤC: MÃ NGUỒN"
    TOC_TITLE = "MỤC LỤC"
    
    # Find heading paragraphs
    heading_indices = {}
    for idx, para in enumerate(paragraphs):
        if para.style.name.startswith('Heading 1'):
            txt = para.text.strip()
            if txt not in heading_indices:
                heading_indices[txt] = idx
    
    print("Heading 1 found:", list(heading_indices.keys()))
    
    # ---- Phase 4: Set up page margins on document's body sectPr ----
    bodySectPr = body.find(qn('w:sectPr'))
    if bodySectPr is None:
        bodySectPr = page_margin_sectPr()
        body.append(bodySectPr)
    
    # Apply margins and A4 size to body sectPr
    pgSz = bodySectPr.find(qn('w:pgSz'))
    if pgSz is None:
        pgSz = OxmlElement('w:pgSz')
        bodySectPr.insert(0, pgSz)
    pgSz.set(qn('w:w'), '11906')
    pgSz.set(qn('w:h'), '16838')
    
    pgMar = bodySectPr.find(qn('w:pgMar'))
    if pgMar is None:
        pgMar = OxmlElement('w:pgMar')
        bodySectPr.append(pgMar)
    pgMar.set(qn('w:top'), str(cm_to_twips(2)))
    pgMar.set(qn('w:right'), str(cm_to_twips(2)))
    pgMar.set(qn('w:bottom'), str(cm_to_twips(2)))
    pgMar.set(qn('w:left'), str(cm_to_twips(3)))
    pgMar.set(qn('w:header'), '720')
    pgMar.set(qn('w:footer'), '720')
    pgMar.set(qn('w:gutter'), '0')
    
    # Set page numbering for last section (Chapter 1 onwards) - Arabic, start at 1
    pgNumType = bodySectPr.find(qn('w:pgNumType'))
    if pgNumType is None:
        pgNumType = OxmlElement('w:pgNumType')
        bodySectPr.append(pgNumType)
    pgNumType.set(qn('w:fmt'), 'decimal')
    pgNumType.set(qn('w:start'), '1')
    
    # ---- Phase 5: Add footer with page number to main body section ----
    # Use parts to add footer relationship
    _add_footer_to_section(doc, bodySectPr, 'decimal', 1)
    
    # ---- Phase 6: Insert Section Breaks (Next Page) at key headings ----
    # Order: cover -> abstract -> (MUC LUC/DANH SACH) -> Chapter1 -> ... -> References -> Appendix
    
    # Section 1 (Cover): ends before ABSTRACT_TITLE
    # Section 2 (Front matter): ends before CHAPTER1_TITLE  
    # Section 3+ (Chapters): continues to end of document
    
    # Insert section break before ABSTRACT_TITLE
    _insert_section_break_before_heading(
        doc, paragraphs, ABSTRACT_TITLE,
        break_type='nextPage',
        numFmt='lowerRoman', start_num=1,
        show_page_num=False  # Cover has no page number
    )
    
    # Insert section break before CHAPTER1_TITLE
    _insert_section_break_before_heading(
        doc, paragraphs, CHAPTER1_TITLE,
        break_type='nextPage', 
        numFmt='lowerRoman', start_num=1,
        show_page_num=True
    )
    
    # Insert section break before REFERENCES
    if REFERENCES_TITLE in heading_indices:
        _insert_section_break_before_heading(
            doc, paragraphs, REFERENCES_TITLE,
            break_type='nextPage',
            numFmt='decimal', start_num=None,  # continue
            show_page_num=True
        )
    
    # Insert section break before APPENDIX
    if APPENDIX_TITLE in heading_indices:
        _insert_section_break_before_heading(
            doc, paragraphs, APPENDIX_TITLE,
            break_type='nextPage',
            numFmt='decimal', start_num=None,
            show_page_num=True
        )

    # ---- Phase 7: Replace manual TOC list with TOC field ----
    # Find the MUC LUC heading and delete manual list items below it
    toc_heading_idx = heading_indices.get(TOC_TITLE)
    if toc_heading_idx is not None:
        _replace_manual_toc(doc, paragraphs, toc_heading_idx)
    
    # ---- Phase 8: Save final document ----
    doc.save(OUTPUT)
    print(f"\nSaved: {OUTPUT}")
    print(f"Size: {os.path.getsize(OUTPUT):,} bytes")

def _add_footer_to_section(doc, sectPr, numFmt='decimal', start_num=1, show=True):
    """Add a footer with page number to a sectPr element."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.opc.part import Part
    from docx.opc.packuri import PackURI
    from lxml import etree
    import io
    
    # Create footer XML
    if show:
        num_map = {'decimal': 'ARABIC', 'lowerRoman': 'ROMAN l', 'upperRoman': 'ROMAN'}
        page_fmt = num_map.get(numFmt, 'ARABIC')
        footer_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" 
       xmlns:cx="http://schemas.microsoft.com/office/drawing/2014/chartex" 
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" 
       xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
       xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
       xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"
       xmlns:w16cex="http://schemas.microsoft.com/office/word/2018/wordml/cex"
       xmlns:w16cid="http://schemas.microsoft.com/office/word/2016/wordml/cid"
       xmlns:w16="http://schemas.microsoft.com/office/word/2018/wordml"
       xmlns:w16sdtdh="http://schemas.microsoft.com/office/word/2020/wordml/sdtdatahash"
       xmlns:w16se="http://schemas.microsoft.com/office/word/2015/wordml/symex"
       xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" 
       xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" 
       xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" 
       xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
  <w:p>
    <w:pPr>
      <w:jc w:val="center"/>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
        <w:sz w:val="24"/>
      </w:rPr>
    </w:pPr>
    <w:r>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
        <w:sz w:val="24"/>
      </w:rPr>
      <w:fldChar w:fldCharType="begin"/>
    </w:r>
    <w:r>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
        <w:sz w:val="24"/>
      </w:rPr>
      <w:instrText xml:space="preserve"> PAGE \\* {page_fmt} </w:instrText>
    </w:r>
    <w:r>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
        <w:sz w:val="24"/>
      </w:rPr>
      <w:fldChar w:fldCharType="end"/>
    </w:r>
  </w:p>
</w:ftr>'''
    else:
        footer_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p/>
</w:ftr>'''

    footer_el = etree.fromstring(footer_xml.encode('utf-8'))
    
    # Add footer to doc part
    try:
        footer_part = doc.part.footer(0)
        footer_part._element = footer_el
    except Exception:
        pass

def _insert_section_break_before_heading(doc, paragraphs, heading_text, break_type='nextPage',
                                          numFmt='decimal', start_num=1, show_page_num=True):
    """Insert a section break (as previous paragraph's sectPr) before a heading."""
    for idx, para in enumerate(paragraphs):
        if para.style.name.startswith('Heading 1') and para.text.strip() == heading_text:
            if idx > 0:
                prev_para = paragraphs[idx - 1]
                pPr = prev_para._element.find(qn('w:pPr'))
                if pPr is None:
                    pPr = OxmlElement('w:pPr')
                    prev_para._element.insert(0, pPr)
                
                # Remove existing sectPr
                existing_sect = pPr.find(qn('w:sectPr'))
                if existing_sect is not None:
                    pPr.remove(existing_sect)
                
                sectPr = OxmlElement('w:sectPr')
                
                # Type: nextPage
                type_el = OxmlElement('w:type')
                type_el.set(qn('w:val'), break_type)
                sectPr.append(type_el)
                
                # A4 page size
                pgSz = OxmlElement('w:pgSz')
                pgSz.set(qn('w:w'), '11906')
                pgSz.set(qn('w:h'), '16838')
                sectPr.append(pgSz)
                
                # Margins
                pgMar = OxmlElement('w:pgMar')
                pgMar.set(qn('w:top'), str(cm_to_twips(2)))
                pgMar.set(qn('w:right'), str(cm_to_twips(2)))
                pgMar.set(qn('w:bottom'), str(cm_to_twips(2)))
                pgMar.set(qn('w:left'), str(cm_to_twips(3)))
                pgMar.set(qn('w:header'), '720')
                pgMar.set(qn('w:footer'), '720')
                pgMar.set(qn('w:gutter'), '0')
                sectPr.append(pgMar)
                
                # Page number format
                if numFmt:
                    pgNumType = OxmlElement('w:pgNumType')
                    pgNumType.set(qn('w:fmt'), numFmt)
                    if start_num is not None:
                        pgNumType.set(qn('w:start'), str(start_num))
                    sectPr.append(pgNumType)
                
                pPr.append(sectPr)
                print(f"  → Section break inserted before: '{heading_text}'")
            break

def _replace_manual_toc(doc, paragraphs, toc_heading_idx):
    """Remove manual TOC list items and replace with TOC field."""
    body = doc.element.body
    
    # Find paragraphs starting from toc_heading_idx+1 that are list items
    to_remove = []
    for idx in range(toc_heading_idx + 1, min(toc_heading_idx + 50, len(paragraphs))):
        para = paragraphs[idx]
        text = para.text.strip()
        # Stop when we hit another heading or separator
        if para.style.name.startswith('Heading') and idx > toc_heading_idx:
            break
        if text.startswith('- [') or text.startswith('[') or text.startswith('TÓM TẮT') or text.startswith('BẢNG'):
            to_remove.append(para._element)
        elif text.startswith('CHƯƠNG') or text.startswith('TÀI LIỆU'):
            to_remove.append(para._element)
        elif text == '---' or text == '':
            continue
        else:
            break
    
    # Insert TOC field before first removed element
    if to_remove:
        first_el = to_remove[0]
        toc_p = _make_toc_field_paragraph()
        body.insert(list(body).index(first_el), toc_p)
        
        # Remove old TOC list
        for el in to_remove:
            if el in body:
                body.remove(el)
        
        print(f"  → TOC field inserted, removed {len(to_remove)} manual list items")

def _make_toc_field_paragraph():
    """Create a paragraph containing TOC field."""
    p = OxmlElement('w:p')
    pPr = OxmlElement('w:pPr')
    pStyle = OxmlElement('w:pStyle')
    pStyle.set(qn('w:val'), 'TOC1')  # Use TOC style
    pPr.append(pStyle)
    p.append(pPr)
    
    r1 = OxmlElement('w:r')
    fc1 = OxmlElement('w:fldChar')
    fc1.set(qn('w:fldCharType'), 'begin')
    fc1.set(qn('w:dirty'), 'true')
    r1.append(fc1)
    p.append(r1)
    
    r2 = OxmlElement('w:r')
    instr = OxmlElement('w:instrText')
    instr.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    r2.append(instr)
    p.append(r2)
    
    r3 = OxmlElement('w:r')
    fc2 = OxmlElement('w:fldChar')
    fc2.set(qn('w:fldCharType'), 'separate')
    r3.append(fc2)
    p.append(r3)
    
    r4 = OxmlElement('w:r')
    t = OxmlElement('w:t')
    t.text = '[Nhấn Ctrl+A rồi F9 trong Word để cập nhật Mục lục]'
    r4.append(t)
    p.append(r4)
    
    r5 = OxmlElement('w:r')
    fc3 = OxmlElement('w:fldChar')
    fc3.set(qn('w:fldCharType'), 'end')
    r5.append(fc3)
    p.append(r5)
    
    return p

if __name__ == "__main__":
    print(f"Processing '{INPUT}' → '{OUTPUT}'...")
    finalize_document()