from pathlib import Path
import re

import markdown
from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(r"C:\Users\Lenovo\Downloads\documentacion")
PRIMARY = RGBColor(0x1F, 0x3A, 0x5F)
ACCENT = RGBColor(0x2E, 0x74, 0xB5)
MUTED = RGBColor(0x5A, 0x5A, 0x5A)
CODE_RED = RGBColor(0x9C, 0x1C, 0x1C)
LINK_BLUE = RGBColor(0x05, 0x63, 0xC1)

DOCUMENTS = [
    (
        BASE / "01_Manual_de_Usuario.md",
        BASE / "01_Manual_de_Usuario.docx",
        "Manual de Usuario",
        "Sistema de Inventario y Seguridad de Red",
    ),
    (
        BASE / "02_Manual_de_Instalacion_y_Despliegue.md",
        BASE / "02_Manual_de_Instalacion_y_Despliegue.docx",
        "Manual de Instalación y Despliegue",
        "Sistema de Inventario y Seguridad de Red",
    ),
]


def set_font(run, name=None, size=None, bold=None, italic=None, color=None, underline=None):
    if name:
        run.font.name = name
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    if underline is not None:
        run.underline = underline


def shade_run(run, fill):
    rpr = run._element.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    rpr.append(shd)


def shade_paragraph(paragraph, fill):
    ppr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.append(shd)


def set_paragraph_border(paragraph, color="1F3A5F", size="8", side="bottom", space="4"):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        ppr.append(pbdr)
    border = OxmlElement(f"w:{side}")
    border.set(qn("w:val"), "single")
    border.set(qn("w:sz"), size)
    border.set(qn("w:space"), space)
    border.set(qn("w:color"), color)
    pbdr.append(border)


def set_cell_shading(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def set_repeat_table_header(row):
    trpr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    trpr.append(tbl_header)


def prevent_row_split(row):
    trpr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    cant_split.set(qn("w:val"), "true")
    trpr.append(cant_split)


def add_field(paragraph, instruction, placeholder="", size=8.5):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)
    set_font(run, "Calibri", size, color=MUTED)


def add_toc(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "Actualice el índice con F9."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)
    set_font(run, "Calibri", 9.5, color=MUTED)


def ensure_style(document, name, base="Normal"):
    try:
        return document.styles[name]
    except KeyError:
        style = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = document.styles[base]
        return style


def configure_styles(document):
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.widow_control = True

    title = document.styles["Title"]
    title.font.name = "Calibri Light"
    title.font.size = Pt(27)
    title.font.bold = True
    title.font.color.rgb = PRIMARY
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(80)
    title.paragraph_format.space_after = Pt(12)

    cover_sub = ensure_style(document, "Cover Subtitle")
    cover_sub.font.name = "Calibri Light"
    cover_sub.font.size = Pt(17)
    cover_sub.font.color.rgb = ACCENT
    cover_sub.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cover_sub.paragraph_format.space_after = Pt(6)

    cover_sub2 = ensure_style(document, "Cover Subtitle 2")
    cover_sub2.font.name = "Calibri Light"
    cover_sub2.font.size = Pt(13)
    cover_sub2.font.color.rgb = MUTED
    cover_sub2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cover_sub2.paragraph_format.space_after = Pt(30)

    cover_meta = ensure_style(document, "Cover Metadata")
    cover_meta.font.name = "Calibri"
    cover_meta.font.size = Pt(9.5)
    cover_meta.font.color.rgb = MUTED
    cover_meta.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cover_meta.paragraph_format.space_after = Pt(0)
    cover_meta.paragraph_format.line_spacing = 1.25

    heading1 = document.styles["Heading 1"]
    heading1.font.name = "Calibri Light"
    heading1.font.size = Pt(18)
    heading1.font.bold = True
    heading1.font.color.rgb = PRIMARY
    heading1.paragraph_format.space_before = Pt(0)
    heading1.paragraph_format.space_after = Pt(10)
    heading1.paragraph_format.keep_with_next = True

    heading2 = document.styles["Heading 2"]
    heading2.font.name = "Calibri Light"
    heading2.font.size = Pt(13.5)
    heading2.font.bold = True
    heading2.font.color.rgb = ACCENT
    heading2.paragraph_format.space_before = Pt(12)
    heading2.paragraph_format.space_after = Pt(4)
    heading2.paragraph_format.keep_with_next = True

    heading3 = document.styles["Heading 3"]
    heading3.font.name = "Calibri"
    heading3.font.size = Pt(11.5)
    heading3.font.bold = True
    heading3.font.color.rgb = PRIMARY
    heading3.paragraph_format.space_before = Pt(9)
    heading3.paragraph_format.space_after = Pt(3)
    heading3.paragraph_format.keep_with_next = True

    caption = ensure_style(document, "Figure Caption")
    caption.font.name = "Calibri"
    caption.font.size = Pt(8.5)
    caption.font.italic = True
    caption.font.color.rgb = MUTED
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(7)
    caption.paragraph_format.keep_together = True

    code = ensure_style(document, "Code Block")
    code.font.name = "Consolas"
    code.font.size = Pt(8.5)
    code.font.color.rgb = RGBColor(0x1E, 0x1E, 0x1E)
    code.paragraph_format.left_indent = Cm(0.25)
    code.paragraph_format.right_indent = Cm(0.15)
    code.paragraph_format.space_before = Pt(4)
    code.paragraph_format.space_after = Pt(6)
    code.paragraph_format.line_spacing = 1.0

    note = ensure_style(document, "Note Box")
    note.font.name = "Calibri"
    note.font.size = Pt(9.5)
    note.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    note.paragraph_format.left_indent = Cm(0.35)
    note.paragraph_format.right_indent = Cm(0.2)
    note.paragraph_format.space_before = Pt(4)
    note.paragraph_format.space_after = Pt(7)


def configure_page(document, short_title, doc_title):
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(1.9)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(0.9)
    section.footer_distance = Cm(0.8)
    section.different_first_page_header_footer = True

    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.paragraph_format.tab_stops.add_tab_stop(Cm(16.6), WD_TAB_ALIGNMENT.RIGHT)
    hp.paragraph_format.space_after = Pt(0)
    run = hp.add_run(short_title)
    set_font(run, "Calibri", 8.5, color=MUTED)
    run = hp.add_run("\t" + doc_title)
    set_font(run, "Calibri", 8.5, color=MUTED)
    set_paragraph_border(hp, color="BFBFBF", size="4", side="bottom", space="4")

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_before = Pt(0)
    run = fp.add_run("Página ")
    set_font(run, "Calibri", 8.5, color=MUTED)
    add_field(fp, "PAGE", "1")
    run = fp.add_run(" de ")
    set_font(run, "Calibri", 8.5, color=MUTED)
    add_field(fp, "NUMPAGES", "1")

    first_header = section.first_page_header
    first_header.is_linked_to_previous = False
    first_header.paragraphs[0].text = ""
    first_footer = section.first_page_footer
    first_footer.is_linked_to_previous = False
    first_footer.paragraphs[0].text = ""

    settings = document.settings.element
    update_fields = OxmlElement("w:updateFields")
    update_fields.set(qn("w:val"), "true")
    settings.append(update_fields)


def add_inline(paragraph, node, bold=False, italic=False, code=False, link=False):
    if isinstance(node, NavigableString):
        text = str(node)
        if not text:
            return
        run = paragraph.add_run(text)
        set_font(run, "Consolas" if code else None, 8.5 if code else None)
        if bold:
            run.bold = True
        if italic:
            run.italic = True
        if code:
            run.font.color.rgb = CODE_RED
            shade_run(run, "F2F2F2")
        if link:
            run.underline = True
            run.font.color.rgb = LINK_BLUE
        return

    if not isinstance(node, Tag):
        return

    name = node.name
    if name == "br":
        paragraph.add_run().add_break(WD_BREAK.LINE)
        return
    if name in ("script", "style", "img"):
        return
    if name in ("strong", "b"):
        bold = True
    elif name in ("em", "i"):
        italic = True
    elif name == "code":
        code = True
    elif name == "a":
        link = True
    elif name == "del":
        for child in node.children:
            add_inline(paragraph, child, bold, italic, code, link)
        return

    for child in node.children:
        add_inline(paragraph, child, bold, italic, code, link)


def is_figure_caption(paragraph_tag):
    if paragraph_tag is None or paragraph_tag.name != "p":
        return False
    text = paragraph_tag.get_text(" ", strip=True)
    if not text.lower().startswith("figura"):
        return False
    em = paragraph_tag.find("em")
    return em is not None and em.get_text(" ", strip=True).startswith("Figura")


def add_image(document, image_tag, figure_number):
    src = image_tag.get("src", "")
    alt = image_tag.get("alt", "Evidencia")
    image_path = (BASE / src).resolve()
    if not image_path.exists():
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"[Imagen no encontrada: {src}]")
        set_font(run, "Calibri", 9, italic=True, color=RGBColor(0xC0, 0x00, 0x00))
        return False
    document.add_picture(str(image_path), width=Cm(16.0))
    p = document.paragraphs[-1]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(14)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.keep_together = True
    return True


def add_caption(document, text):
    p = document.add_paragraph(style="Figure Caption")
    add_inline(p, NavigableString(text))
    for run in p.runs:
        if run.font.name != "Consolas":
            run.italic = True
            run.font.color.rgb = MUTED


def add_code_block(document, code_tag):
    text = code_tag.get_text().rstrip("\n")
    if not text:
        return
    p = document.add_paragraph(style="Code Block")
    p.paragraph_format.keep_together = True
    lines = text.splitlines()
    for index, line in enumerate(lines):
        run = p.add_run(line)
        set_font(run, "Consolas", 8.5, color=RGBColor(0x1E, 0x1E, 0x1E))
        if index < len(lines) - 1:
            run.add_break(WD_BREAK.LINE)
    shade_paragraph(p, "F4F6F8")
    set_paragraph_border(p, color="D0D7DE", size="4", side="left", space="4")


def add_table(document, table_tag):
    rows = table_tag.find_all("tr")
    if not rows:
        return
    column_count = max(len(row.find_all(["th", "td"])) for row in rows)
    table = document.add_table(rows=0, cols=column_count)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for row_tag in rows:
        cells = row_tag.find_all(["th", "td"], recursive=False)
        row = table.add_row()
        prevent_row_split(row)
        if row_tag.find("th") is not None:
            set_repeat_table_header(row)
        for idx, cell_tag in enumerate(cells):
            if idx >= column_count:
                break
            cell = row.cells[idx]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(1)
            paragraph.paragraph_format.space_after = Pt(1)
            paragraph.paragraph_format.line_spacing = 1.0
            if cell_tag.name == "th":
                set_cell_shading(cell, "D9EAF7")
                for child in cell_tag.children:
                    add_inline(paragraph, child, bold=True)
                for run in paragraph.runs:
                    if not run.bold:
                        run.bold = True
                    if run.font.name != "Consolas":
                        run.font.size = Pt(8.5)
            else:
                for child in cell_tag.children:
                    add_inline(paragraph, child)
                for run in paragraph.runs:
                    if run.font.name != "Consolas":
                        run.font.size = Pt(8.5)
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
    spacer.paragraph_format.line_spacing = 0.6


def add_list(document, list_tag, level=0):
    ordered = list_tag.name == "ol"
    items = list_tag.find_all("li", recursive=False)
    start_number = int(list_tag.get("start", 1)) if ordered else 1
    for index, item in enumerate(items, start=start_number):
        p = document.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.55 + (0.55 * level))
        p.paragraph_format.first_line_indent = Cm(-0.45)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.08
        prefix = f"{index}. " if ordered else "• "
        run = p.add_run(prefix)
        set_font(run, "Calibri", 10.5)
        for child in item.children:
            if isinstance(child, Tag) and child.name in ("ul", "ol"):
                continue
            if isinstance(child, Tag) and child.name == "p":
                for sub in child.children:
                    add_inline(p, sub)
            else:
                add_inline(p, child)
        for child in item.children:
            if isinstance(child, Tag) and child.name in ("ul", "ol"):
                add_list(document, child, level + 1)


def add_heading(document, tag, cover_mode, chapter_break):
    text = tag.get_text(" ", strip=True)
    if tag.name == "h1":
        if cover_mode:
            p = document.add_paragraph(style="Title")
            add_inline(p, NavigableString(text))
        else:
            p = document.add_paragraph(text, style="Heading 1")
        return
    if tag.name == "h2":
        if cover_mode:
            p = document.add_paragraph(style="Cover Subtitle")
            add_inline(p, NavigableString(text))
        else:
            p = document.add_paragraph(text, style="Heading 1")
            if chapter_break:
                p.paragraph_format.page_break_before = True
        return
    if tag.name == "h3":
        if cover_mode:
            p = document.add_paragraph(style="Cover Subtitle 2")
            add_inline(p, NavigableString(text))
        else:
            p = document.add_paragraph(text, style="Heading 2")
        return
    if tag.name == "h4":
        document.add_paragraph(text, style="Heading 3")


def add_paragraph(document, tag, cover_mode, caption_mode=False):
    if tag.find("img") is not None and not tag.get_text(strip=True):
        return
    if caption_mode:
        p = document.add_paragraph(style="Figure Caption")
        for child in tag.children:
            add_inline(p, child)
        for run in p.runs:
            run.italic = True
            if run.font.name != "Consolas":
                run.font.color.rgb = MUTED
        return
    style = "Cover Metadata" if cover_mode else None
    p = document.add_paragraph(style=style) if style else document.add_paragraph()
    for child in tag.children:
        add_inline(p, child)
    if not cover_mode and len(p.text.strip()) <= 3:
        p.paragraph_format.space_after = Pt(0)


def add_blockquote(document, tag):
    for child in tag.children:
        if isinstance(child, Tag) and child.name == "p":
            p = document.add_paragraph(style="Note Box")
            for sub in child.children:
                add_inline(p, sub)
            shade_paragraph(p, "EAF1F8")
            set_paragraph_border(p, color="2E74B5", size="18", side="left", space="6")
        elif isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                p = document.add_paragraph(style="Note Box")
                add_inline(p, NavigableString(text))
                shade_paragraph(p, "EAF1F8")
                set_paragraph_border(p, color="2E74B5", size="18", side="left", space="6")


def build_document(source_path, output_path, doc_title, project_title):
    text = source_path.read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=["extra", "sane_lists"])
    html = md.convert(text)
    (BASE / "_fuentes" / (source_path.stem + ".html")).write_text(html, encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    root = soup.body or soup

    document = Document()
    configure_styles(document)
    configure_page(document, project_title, doc_title)

    document.core_properties.title = f"{doc_title} — {project_title}"
    document.core_properties.subject = "Computación en Red II — Municipalidad Distrital de Alto Selva Alegre"
    document.core_properties.author = "Equipo del proyecto"
    document.core_properties.keywords = "inventario, red, PostgreSQL, API REST, PowerShell, ACL"
    document.core_properties.comments = "Documento generado a partir de los archivos del proyecto."

    cover_mode = True
    in_index = False
    figure_number = 0

    for tag in root.children:
        if not isinstance(tag, Tag):
            continue
        if tag.name == "hr":
            if in_index:
                in_index = False
            if cover_mode:
                cover_mode = False
            continue
        if in_index:
            continue
        if tag.name in ("h1", "h2", "h3", "h4"):
            heading_text = tag.get_text(" ", strip=True)
            if tag.name == "h2" and heading_text.lower().startswith("índice"):
                add_heading(document, tag, cover_mode, True)
                toc_p = document.add_paragraph()
                add_toc(toc_p)
                in_index = True
                continue
            chapter = False
            if not cover_mode and tag.name == "h2":
                chapter = bool(re.match(r"^(\d+\.|ficha\b|índice\b)", heading_text.lower()))
            add_heading(document, tag, cover_mode, chapter)
            if not cover_mode and tag.name == "h2":
                for p in document.paragraphs[-1:]:
                    set_paragraph_border(p, color="2E74B5", size="8", side="bottom", space="4")
            continue
        if tag.name == "p":
            if tag.find("img") is not None and not tag.get_text(strip=True):
                figure_number += 1
                next_p = tag.find_next_sibling("p")
                add_image(document, tag.find("img"), figure_number)
                if not is_figure_caption(next_p):
                    alt = tag.find("img").get("alt", "Evidencia")
                    add_caption(document, f"Figura {figure_number}. {alt}.")
                continue
            add_paragraph(document, tag, cover_mode, is_figure_caption(tag))
            continue
        if tag.name == "pre":
            code_tag = tag.find("code") or tag
            add_code_block(document, code_tag)
            continue
        if tag.name == "table":
            add_table(document, tag)
            continue
        if tag.name in ("ul", "ol"):
            add_list(document, tag)
            continue
        if tag.name == "blockquote":
            add_blockquote(document, tag)
            continue
        if tag.name == "div" and tag.find("pre") is not None:
            add_code_block(document, tag.find("pre").find("code") or tag.find("pre"))
            continue

    document.save(str(output_path))
    return output_path


if __name__ == "__main__":
    for source, output, title, project in DOCUMENTS:
        result = build_document(source, output, title, project)
        print(f"DOCX generado: {result}")
