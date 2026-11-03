import sys, json, os
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ── XML helpers ──────────────────────────────────────────────────────────────

def _set_borders(table, color='000000', size='4'):
    """Add all-sides borders to every cell in a table."""
    for row in table.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
                border = OxmlElement(f'w:{side}')
                border.set(qn('w:val'), 'single')
                border.set(qn('w:sz'), size)
                border.set(qn('w:space'), '0')
                border.set(qn('w:color'), color)
                tcBorders.append(border)
            tcPr.append(tcBorders)


def _shd(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def _set_col_widths(table, widths_cm):
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            if i < len(widths_cm):
                cell.width = Cm(widths_cm[i])


def _cell(cell, text, bold=False, italic=False, size=10,
          align=WD_ALIGN_PARAGRAPH.LEFT, valign=WD_ALIGN_VERTICAL.CENTER,
          shade=None, color=None):
    if shade:
        _shd(cell, shade)
    cell.vertical_alignment = valign
    cell.text = ''
    p = cell.paragraphs[0]
    p.alignment = align
    run = p.add_run(str(text) if text else '')
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def _heading(doc, num, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(f'{num}.  {text}')
    run.bold = True
    run.font.size = Pt(10)


def _note(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(f'Note: {text}')
    run.font.size = Pt(9)
    run.italic = True


# ── Page header (letterhead) ─────────────────────────────────────────────────

def _add_page_header(doc, college, department):
    header = doc.sections[0].header
    header.is_linked_to_previous = False

    htbl = header.add_table(rows=4, cols=5, width=Cm(25.7))
    _set_borders(htbl)
    _set_col_widths(htbl, [2.0, 13.7, 3.0, 4.0, 3.0])

    # Row 0: logo | MSU+IIT name | Document Code No. (x3)
    htbl.rows[0].cells[0].text = ''
    _cell(htbl.rows[0].cells[1], 'Mindanao State University\nILIGAN INSTITUTE OF TECHNOLOGY',
          bold=False, size=9, valign=WD_ALIGN_VERTICAL.CENTER)
    for run in htbl.rows[0].cells[1].paragraphs[0].runs:
        run.bold = False
    for p in htbl.rows[0].cells[1].paragraphs:
        for run in p.runs:
            if 'ILIGAN' in run.text:
                run.bold = True
    for c in (2, 3, 4):
        _cell(htbl.rows[0].cells[c], 'Document Code No.',
              bold=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

    # Row 1: blank | College+Dept | FM code (x3)
    _cell(htbl.rows[1].cells[1], f'{college}\n{department}', size=9)
    for c in (2, 3, 4):
        _cell(htbl.rows[1].cells[c], 'FM – MSUIIT – ACAD – 016',
              bold=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

    # Row 2: sub-headers (red background)
    for c, txt in [(2, 'Revision No.'), (3, 'Effective Date'), (4, 'Page No.')]:
        _cell(htbl.rows[2].cells[c], txt, bold=True, size=9,
              align=WD_ALIGN_PARAGRAPH.CENTER, shade='FF0000')
        htbl.rows[2].cells[c].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Row 3: values
    _cell(htbl.rows[3].cells[2], '00', size=9, align=WD_ALIGN_PARAGRAPH.CENTER)
    _cell(htbl.rows[3].cells[3], '04.22.2024', size=9, align=WD_ALIGN_PARAGRAPH.CENTER)
    _cell(htbl.rows[3].cells[4], '', size=9, align=WD_ALIGN_PARAGRAPH.CENTER)


# ── Main generator ────────────────────────────────────────────────────────────

def generate(course, outcomes, output_path):
    doc = Document()

    # A4 Landscape
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width = Cm(29.7)
    sec.page_height = Cm(21)
    sec.top_margin = Cm(4.8)
    sec.bottom_margin = Cm(1.5)
    sec.left_margin = Cm(2.0)
    sec.right_margin = Cm(2.0)

    college = 'College of Computer Studies'
    department = 'Department of Computer Science'
    _add_page_header(doc, college, department)

    # ── SYLLABUS title ────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run('SYLLABUS')
    run.bold = True
    run.font.size = Pt(16)

    clos = course.get('clos', [])
    clo_plo = course.get('clo_plo_map', {})

    # ── 1. Course Information ─────────────────────────────────────────────────
    _heading(doc, 1, 'Course Information')
    tbl0 = doc.add_table(rows=8, cols=2)
    _set_col_widths(tbl0, [4.5, 21.2])
    _set_borders(tbl0)
    for i, (label, val) in enumerate([
        ('Course Code:',              course.get('code', '')),
        ('Course Title:',             course.get('title', '')),
        ('Description:',              course.get('desc', '')),
        ('Credits:',                  f"{course.get('credits', '')} units"),
        ('Modality:',                 course.get('modality', '')),
        ('Contact Hours:',            course.get('contact_hours', '')),
        ('Pre-requisite / Co-requisite:', course.get('prereq', 'None')),
        ('A.Y. and Semester:',        course.get('ay_semester', '')),
    ]):
        _cell(tbl0.rows[i].cells[0], label, size=10)
        _cell(tbl0.rows[i].cells[1], val,   size=10, bold=(i == 0))

    # ── 2. Course Outcomes ────────────────────────────────────────────────────
    _heading(doc, 2, 'Course Outcomes')
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run('At the end of the semester, the students should be able to:')
    run.font.size = Pt(10)

    for clo in clos:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r1 = p.add_run(f"{clo.get('code', '')}: ")
        r1.font.size = Pt(10)
        r2 = p.add_run(clo.get('description', ''))
        r2.font.size = Pt(10)

    # ── 3. Alignment of COs to POs ────────────────────────────────────────────
    _heading(doc, 3, 'Alignment of Course Outcomes (COs) to Program Outcomes (POs)')
    _note(doc, 'Put I (Introduced), P (Practiced), or D (Demonstrated) on the relevant and appropriate cells to indicate alignment.')

    if clos and outcomes:
        n_clo = len(clos)
        at = doc.add_table(rows=len(outcomes) + 1, cols=n_clo + 1)
        _set_borders(at)

        total_w = 25.7
        plo_w = 8.0
        clo_w = (total_w - plo_w) / n_clo
        _set_col_widths(at, [plo_w] + [clo_w] * n_clo)

        _cell(at.rows[0].cells[0], 'Program Learning Outcomes',
              bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        for j, clo in enumerate(clos):
            label = f"{clo.get('code', '')}: {clo.get('description', '')}"
            _cell(at.rows[0].cells[j + 1], label, bold=True, size=10)

        for i, o in enumerate(outcomes):
            row = at.rows[i + 1]
            plo_label = o.get('desc') or f"{o['code']} – {o.get('title', '')}"
            _cell(row.cells[0], plo_label, size=10)
            for j, clo in enumerate(clos):
                val = clo_plo.get(clo.get('code', ''), {}).get(o['code'], '')
                _cell(row.cells[j + 1], val, bold=bool(val), size=16 if val else 10,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
    else:
        doc.add_paragraph('No course outcomes or program outcomes defined.').runs[0].font.size = Pt(10)

    # ── 4. Assessment Blueprint ───────────────────────────────────────────────
    _heading(doc, 4, 'Assessment Blueprint')
    _note(doc, 'A CLO may be assessed by more than one major Assessment Task/Tool. The total weight of each CLO column must equal 100%.')

    ab = course.get('assessment_blueprint', [])
    abt = doc.add_table(rows=max(len(ab), 1) + 2, cols=7)
    _set_col_widths(abt, [1.6, 5.2, 3.0, 4.5, 3.8, 3.8, 3.8])
    _set_borders(abt)

    for j, h in enumerate(['CLO', 'Learning Outcome Description', 'Learning Taxonomy',
                            'Primary Assessment Tool/Task', 'Rubric/Evidence Reference',
                            'Weight', 'Weight']):
        _cell(abt.rows[0].cells[j], h, bold=True, size=10,
              align=WD_ALIGN_PARAGRAPH.CENTER)

    for j, h in enumerate(['CLO', 'Learning Outcome Description', 'Learning Taxonomy',
                            'Primary Assessment Tool/Task', 'Rubric/Evidence Reference',
                            'Assessment Task', 'CLO']):
        _cell(abt.rows[1].cells[j], h, bold=True, size=10,
              align=WD_ALIGN_PARAGRAPH.CENTER)

    if ab:
        for i, item in enumerate(ab):
            row = abt.rows[i + 2]
            for j, key in enumerate(['clo', 'description', 'taxonomy', 'tool', 'rubric', 'weight', 'weight_clo']):
                _cell(row.cells[j], item.get(key, ''), size=10,
                      align=WD_ALIGN_PARAGRAPH.CENTER if j in (0, 2, 5, 6) else WD_ALIGN_PARAGRAPH.LEFT)
    else:
        _cell(abt.rows[2].cells[0], '—', size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

    # ── 5. Learning Plan ──────────────────────────────────────────────────────
    _heading(doc, 5, 'Learning Plan')
    _note(doc, 'The Lesson Learning Outcomes (LLOs) shall be mapped to the Course Learning Outcomes (CLOs) it addresses by indicating a check mark (✓) in the appropriate column.')

    lp = course.get('learning_plan', [])
    n_co = len(clos)
    fixed_w = {'week': 1.0, 'topic': 2.8, 'llo': 3.8, 'methods': 3.5, 'resources': 4.5, 'assess': 3.2}
    co_w = max(0.9, (25.7 - sum(fixed_w.values())) / max(n_co, 1))
    col_widths = ([fixed_w['week'], fixed_w['topic'], fixed_w['llo']] +
                  [co_w] * n_co +
                  [fixed_w['methods'], fixed_w['resources'], fixed_w['assess']])

    lt = doc.add_table(rows=max(len(lp), 1) + 2, cols=3 + n_co + 3)
    _set_col_widths(lt, col_widths)
    _set_borders(lt)

    for j, h in enumerate(['Week', 'Topics', 'Lesson Learning Outcome (LLO)']):
        _cell(lt.rows[0].cells[j], h, bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
    if n_co:
        _cell(lt.rows[0].cells[3], 'Course Outcomes', bold=True, size=10,
              align=WD_ALIGN_PARAGRAPH.CENTER)
    for h, label in enumerate(['Teaching Learning Activities / Methodologies',
                                'Learning Resources', 'Assessment']):
        _cell(lt.rows[0].cells[3 + n_co + h], label, bold=True, size=10,
              align=WD_ALIGN_PARAGRAPH.CENTER)

    for j in range(3):
        _cell(lt.rows[1].cells[j], '', size=10)
    for j, clo in enumerate(clos):
        _cell(lt.rows[1].cells[3 + j], clo.get('code', f'CO{j+1}'),
              bold=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)
    for j in range(3):
        _cell(lt.rows[1].cells[3 + n_co + j], '', size=10)

    if lp:
        for i, row_data in enumerate(lp):
            row = lt.rows[i + 2]
            _cell(row.cells[0], row_data.get('week', ''), size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell(row.cells[1], row_data.get('topic', ''), size=10)
            _cell(row.cells[2], row_data.get('llo', ''), size=10)
            cos = row_data.get('cos', {})
            for j, clo in enumerate(clos):
                checked = cos.get(clo.get('code', ''), False)
                _cell(row.cells[3 + j], '✓' if checked else '', bold=checked, size=10,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
            _cell(row.cells[3 + n_co],     row_data.get('methods', ''),    size=10)
            _cell(row.cells[4 + n_co],     row_data.get('resources', ''),  size=10)
            _cell(row.cells[5 + n_co],     row_data.get('assessment', ''), size=10)
    else:
        _cell(lt.rows[2].cells[0], '—', size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

    # ── 6. Grading System ─────────────────────────────────────────────────────
    _heading(doc, 6, 'Grading System')
    gt = doc.add_table(rows=2, cols=4)
    _set_col_widths(gt, [6.425, 6.425, 6.425, 6.425])
    _set_borders(gt)
    for j in range(4):
        _cell(gt.rows[0].cells[j], 'Grade Equivalent', bold=True, size=10,
              align=WD_ALIGN_PARAGRAPH.CENTER)
    # Editable scale: fill the left column pair first, then the right.
    grading = [g for g in course.get('grading_system', [])
               if str(g.get('range', '')).strip() or str(g.get('grade', '')).strip()]
    half = (len(grading) + 1) // 2
    cols = [grading[:half], grading[half:]]
    for c, part in enumerate(cols):
        _cell(gt.rows[1].cells[c * 2], '\n'.join(str(g.get('range', '')) for g in part),
              size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
        _cell(gt.rows[1].cells[c * 2 + 1], '\n'.join(str(g.get('grade', '')) for g in part),
              size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

    # ── 7. References ─────────────────────────────────────────────────────────
    _heading(doc, 7, 'References')
    refs = course.get('references', {})
    for section_name, key in [('Textbooks', 'textbooks'), ('Journals', 'journals'),
                               ('Online Resources', 'online')]:
        items = [r for r in refs.get(key, []) if str(r).strip()]
        if items:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(section_name)
            r.bold = True
            r.font.size = Pt(10)
            for idx, ref in enumerate(items, 1):
                p2 = doc.add_paragraph()
                p2.paragraph_format.space_after = Pt(1)
                p2.paragraph_format.left_indent = Cm(0.5)
                p2.add_run(f'{idx}. {ref}').font.size = Pt(10)

    # ── 8. Classroom Policies ─────────────────────────────────────────────────
    _heading(doc, 8, 'Classroom Policies')
    for i, pol in enumerate([p for p in course.get('policies', []) if str(p).strip()], 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        p.add_run(f'{i}. {pol}').font.size = Pt(10)

    # ── 9. Approval ───────────────────────────────────────────────────────────
    _heading(doc, 9, 'Approval')
    appt = doc.add_table(rows=4, cols=4)
    _set_col_widths(appt, [6.425, 6.425, 6.425, 6.425])
    _set_borders(appt)
    for j, h in enumerate(['Prepared by:', 'Reviewed by:', 'Approved by:', 'Approved by:']):
        _cell(appt.rows[0].cells[j], h, bold=True, size=10)
    for j in range(4):
        _cell(appt.rows[2].cells[j], '_' * 28, bold=True, size=10,
              align=WD_ALIGN_PARAGRAPH.CENTER)
    for j, role in enumerate(['Faculty Member', 'Academic Program Coordinator',
                               'Academic Program Coordinator', 'Department Chairperson']):
        _cell(appt.rows[3].cells[j], role, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)


if __name__ == '__main__':
    data = json.loads(sys.stdin.read())
    course = data['course']
    outcomes = data['outcomes']
    out_dir = data.get('output_dir', '/tmp')
    out_path = os.path.join(out_dir, f"{course.get('code', 'syllabus')}_syllabus.docx")
    generate(course, outcomes, out_path)
    print(out_path)
