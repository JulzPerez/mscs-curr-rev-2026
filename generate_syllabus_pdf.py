#!/usr/bin/env python3
"""Generate a PDF syllabus using pdflatex, matching the MSU-IIT FM-MSUIIT-ACAD-016 format."""
import sys, json, os, subprocess, tempfile, shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(BASE_DIR, 'msuiit-logo.jpg')
COLLEGE = 'College of Computer Studies'
DEPARTMENT = 'Department of Computer Science'


def esc(s):
    """Escape LaTeX special characters."""
    if not isinstance(s, str):
        s = str(s) if s is not None else ''
    s = s.replace('\\', r'\textbackslash{}')
    s = s.replace('&',  r'\&')
    s = s.replace('%',  r'\%')
    s = s.replace('$',  r'\$')
    s = s.replace('#',  r'\#')
    s = s.replace('_',  r'\_')
    s = s.replace('{',  r'\{')
    s = s.replace('}',  r'\}')
    s = s.replace('~',  r'\textasciitilde{}')
    s = s.replace('^',  r'\textasciicircum{}')
    return s


def esc_nl(s):
    """Escape and convert newlines to LaTeX line breaks for table cells."""
    s = esc(s)
    s = s.replace('\n\n', r' \newline ')
    s = s.replace('\n',   r' \newline ')
    return s


def generate_tex(course, outcomes):
    code     = course.get('code', 'syllabus')
    clos     = course.get('clos', [])
    clo_plo  = course.get('clo_plo_map', {})
    ab       = course.get('assessment_blueprint', [])
    lp       = course.get('learning_plan', [])
    refs     = course.get('references', {})
    policies = [p for p in course.get('policies', []) if str(p).strip()]
    n_clo    = len(clos)
    logo     = LOGO.replace('\\', '/')

    # ── Header table column widths (total ≈ 25.7 cm usable on A4 landscape) ──
    # Logo | Institution | RevNo | EffDate | PageNo
    hdr_cols = r'|m{1.8cm}|p{13.6cm}|C{2.3cm}|C{3.6cm}|C{2.3cm}|'

    # ── Preamble ──────────────────────────────────────────────────────────────
    lines = [
        r'\documentclass[a4paper,10pt]{article}',
        # top = paper-edge → body-top distance (fancyhdr header sits inside this space).
        # headheight must equal actual header content height; any excess becomes blank gap.
        # Measured: table ≈ 2.1 cm + rule ≈ 0.05 cm → set headheight = 2.3 cm.
        # top = headheight + headsep + small top pad ≈ 2.3 + 0.5 + 0.2 = 3.0 cm.
        r'\usepackage[a4paper,landscape,top=3.2cm,bottom=1.5cm,left=2cm,right=2cm,headsep=0.5cm]{geometry}',
        r'\usepackage{graphicx}',
        r'\usepackage{array}',
        r'\usepackage{longtable}',
        r'\usepackage{multirow}',
        r'\usepackage{colortbl}',
        r'\usepackage{xcolor}',
        r'\usepackage{fancyhdr}',
        r'\usepackage{lastpage}',
        r'\usepackage[T1]{fontenc}',
        r'\usepackage[utf8]{inputenc}',
        r'\usepackage{helvet}',
        r'\usepackage{parskip}',
        r'\usepackage{amssymb}',
        r'\renewcommand{\familydefault}{\sfdefault}',
        r'\setlength{\parindent}{0pt}',
        r'\setlength{\parskip}{3pt}',
        r'\setlength{\tabcolsep}{3pt}',
        r'\setlength{\arrayrulewidth}{0.4pt}',
        r'\setlength{\LTpre}{2pt}',
        r'\setlength{\LTpost}{2pt}',
        r'\definecolor{headerred}{RGB}{192,0,0}',
        r'\definecolor{hdrfg}{RGB}{255,255,255}',
        r'\newcolumntype{C}[1]{>{\centering\arraybackslash}m{#1}}',
        r'\newcolumntype{L}[1]{>{\arraybackslash}p{#1}}',
        '',
        r'\pagestyle{fancy}',
        r'\fancyhf{}',
        r'\renewcommand{\headrulewidth}{0pt}',
        r'\setlength{\headheight}{2.4cm}',
        '',
        # Institution cell: multirow spanning all 4 rows so no internal lines cross it.
        # Only cols 3-5 (document code box) get \cline between rows.
        r'\fancyhead[C]{%',
        r'\makebox[\textwidth]{\normalsize',
        r'\begin{tabular}{' + hdr_cols + '}',
        r'\hline',
        r'\multirow{4}{*}{\includegraphics[width=1.7cm,keepaspectratio]{' + logo + '}} &'
            r' \multirow{4}{13.4cm}{\parbox{13.4cm}{\small Mindanao State University\newline'
            r'\textbf{ILIGAN INSTITUTE OF TECHNOLOGY}\\[6pt]'
            r'\small ' + esc(COLLEGE) + r'\newline\textbf{' + esc(DEPARTMENT) + r'}}} &'
            r' \multicolumn{3}{c|}{\small\textbf{Document Code No.}} \\',
        r'\cline{3-5}',
        r' & & \multicolumn{3}{c|}{\small\textbf{FM -- MSUIIT -- ACAD -- 016}} \\',
        r'\cline{3-5}',
        r' & & \cellcolor{headerred}\textcolor{hdrfg}{\small\textbf{Revision No.}}'
            r' & \cellcolor{headerred}\textcolor{hdrfg}{\small\textbf{Effective Date}}'
            r' & \cellcolor{headerred}\textcolor{hdrfg}{\small\textbf{Page No.}} \\',
        r'\cline{3-5}',
        r' & & {\small 02} & {\small 04.22.2024} & {\small\thepage/\pageref{LastPage}} \\',
        r'\hline',
        r'\end{tabular}%',
        r'}%',
        r'\vspace{0.1cm}%',
        r'\noindent\rule{\textwidth}{1.5pt}%',
        r'}',
        '',
        r'\begin{document}',
        '',
    ]

    # ── SYLLABUS title ────────────────────────────────────────────────────────
    lines += [
        r'\begin{center}',
        r'{\large\textbf{S{\small YLLABUS}}}',
        r'\end{center}',
        r'\vspace{2pt}',
        '',
    ]

    # Width helpers: tabcolsep=3pt=0.106cm per side; total overhead per col = 2×CS.
    # Available content width = TW − n_cols × 2 × CS (ignore hairline rule widths).
    TW = 25.3   # usable text width in cm (25.7 minus a small safety buffer)
    CS = 0.106  # tabcolsep in cm (3pt per side)

    def ca(n_cols):
        """Content width available across n_cols columns."""
        return round(TW - n_cols * 2 * CS, 3)

    def w(x):
        return f'{x:.3f}cm'

    def section(n, title):
        return [
            r'\vspace{6pt}',
            r'\noindent\textbf{' + str(n) + r'.\hspace{0.8cm}' + title + r'}',
            r'\vspace{4pt}',
            '',
        ]

    # ── 1. Course Information ─────────────────────────────────────────────────
    lines += section(1, 'Course Information')
    ci_avail  = ca(2)
    ci_label  = 4.2
    ci_val    = round(ci_avail - ci_label, 3)
    ci_rows = [
        ('Course Code:',                  course.get('code', '')),
        ('Course Title:',                 course.get('title', '')),
        ('Description:',                  course.get('desc', '')),
        ('Credits:',                      f"{course.get('credits', '')} units"),
        ('Modality:',                     course.get('modality', '')),
        ('Contact Hours:',                course.get('contact_hours', '')),
        ('Pre-requisite / Co-requisite:', course.get('prereq', 'None')),
        ('A.Y. and Semester:',            course.get('ay_semester', '')),
    ]
    lines.append(r'\noindent\begin{longtable}{|L{' + w(ci_label) + r'}|L{' + w(ci_val) + r'}|}')
    lines.append(r'\hline')
    lines.append(r'\endfirsthead')
    lines.append(r'\hline')
    lines.append(r'\endhead')
    for label, val in ci_rows:
        lines.append(esc(label) + ' & ' + esc_nl(val) + r' \\')
        lines.append(r'\hline')
    lines.append(r'\end{longtable}')
    lines.append('')

    # ── 2. Course Outcomes ────────────────────────────────────────────────────
    lines += section(2, 'Course Outcomes')
    lines.append(r'\noindent At the end of the semester, the students should be able to:')
    lines.append('')
    for clo in clos:
        c = esc(clo.get('code', ''))
        d = esc(clo.get('description', ''))
        lines.append(r'\noindent\textbf{' + c + r':} ' + d + r'\par')
    lines.append('')

    # ── 3. Alignment of COs to POs ────────────────────────────────────────────
    lines += section(3, 'Alignment of Course Outcomes (COs) to Program Outcomes (POs)')
    lines.append(r'\textit{\small Note: Put I (Introduced), P (Practiced), or D (Demonstrated) on the relevant cells to indicate alignment.}')
    lines.append('')

    if clos and outcomes:
        n_align  = 1 + n_clo
        al_avail = ca(n_align)
        plo_w    = min(8.0, round(al_avail * 0.40, 3))
        clo_w    = max(1.2, round((al_avail - plo_w) / n_clo, 3))
        col_spec = r'|L{' + w(plo_w) + r'}|' + ''.join([r'C{' + w(clo_w) + r'}|' for _ in clos])
        lines.append(r'\noindent\begin{longtable}{' + col_spec + '}')
        lines.append(r'\hline')
        hdr = [r'\textbf{Program Learning Outcomes}']
        for clo in clos:
            hdr.append(r'\textbf{' + esc(clo.get('code', '')) + r':} ' + esc(clo.get('description', '')))
        lines.append(' & '.join(hdr) + r' \\')
        lines.append(r'\hline')
        lines.append(r'\endfirsthead')
        lines.append(r'\hline')
        lines.append(' & '.join(hdr) + r' \\')
        lines.append(r'\hline')
        lines.append(r'\endhead')
        for o in outcomes:
            plo_text = esc(o.get('desc') or f"{o['code']} – {o.get('title', '')}")
            row = [plo_text]
            for clo in clos:
                val = clo_plo.get(clo.get('code', ''), {}).get(o['code'], '')
                row.append(esc(val) if val else '')
            lines.append(' & '.join(row) + r' \\')
            lines.append(r'\hline')
        lines.append(r'\end{longtable}')
    else:
        lines.append(r'\noindent\textit{No course outcomes or program outcomes defined.}')
    lines.append('')

    # ── 4. Assessment Blueprint ───────────────────────────────────────────────
    lines += section(4, 'Assessment Blueprint')
    lines.append(
        r'\textit{\small Note: A CLO may be assessed by more than one major Assessment Task/Tool. '
        r'Total weight of all CLOs and Assessment Tasks/Tools must be 100\%.}'
    )
    lines.append('')

    # 7 fixed columns; distribute remaining after fixed widths to desc and rubric
    ab_n   = 7
    ab_avl = ca(ab_n)
    ab_clo = 1.5; ab_tax = 2.8; ab_tool = 4.3; ab_wt1 = 2.6; ab_wt2 = 2.6
    ab_rem = round(ab_avl - ab_clo - ab_tax - ab_tool - ab_wt1 - ab_wt2, 3)
    ab_desc = round(ab_rem * 0.55, 3)
    ab_rub  = round(ab_rem - ab_desc, 3)
    ab_widths = [ab_clo, ab_desc, ab_tax, ab_tool, ab_rub, ab_wt1, ab_wt2]
    ab_types  = ['C',    'L',     'C',    'L',     'L',    'C',    'C']
    ab_spec   = '|' + '|'.join([t + '{' + w(ww) + '}' for t, ww in zip(ab_types, ab_widths)]) + '|'

    lines.append(r'\noindent\begin{longtable}{' + ab_spec + '}')
    lines.append(r'\hline')
    lines.append(
        r'\textbf{CLO} & \textbf{Learning Outcome Description} & \textbf{Learning Taxonomy} & '
        r'\textbf{Primary Assessment Tool/Task} & \textbf{Rubric/Evidence Reference} & '
        r'\multicolumn{2}{c|}{\textbf{Weight}} \\'
    )
    lines.append(r'\hline')
    lines.append(r' & & & & & \textbf{Assessment Task} & \textbf{CLO} \\')
    lines.append(r'\hline')
    lines.append(r'\endfirsthead')
    lines.append(r'\hline')
    lines.append(
        r'\textbf{CLO} & \textbf{Learning Outcome Description} & \textbf{Learning Taxonomy} & '
        r'\textbf{Primary Assessment Tool/Task} & \textbf{Rubric/Evidence Reference} & '
        r'\multicolumn{2}{c|}{\textbf{Weight}} \\'
    )
    lines.append(r'\hline')
    lines.append(r' & & & & & \textbf{Assessment Task} & \textbf{CLO} \\')
    lines.append(r'\hline')
    lines.append(r'\endhead')

    if ab:
        for item in ab:
            row = [
                esc(item.get('clo', '')),
                esc(item.get('description', '')),
                esc(item.get('taxonomy', '')),
                esc(item.get('tool', '')),
                esc(item.get('rubric', '')),
                esc(item.get('weight', '')),
                esc(item.get('weight_clo', '')),
            ]
            lines.append(' & '.join(row) + r' \\')
            lines.append(r'\hline')
    else:
        lines.append(r'-- & & & & & & \\')
        lines.append(r'\hline')
    lines.append(r'\end{longtable}')
    lines.append('')

    # ── 5. Learning Plan ──────────────────────────────────────────────────────
    lines += section(5, 'Learning Plan')
    lines.append(
        r'\textit{\small Note: The Lesson Learning Outcomes (LLOs) shall be mapped to the CLOs it '
        r'addresses by indicating a check mark ($\checkmark$) on the corresponding cell.}'
    )
    lines.append('')

    # Fixed column content widths (cm); CO columns share what remains
    lp_n     = 6 + n_clo
    lp_avail = ca(lp_n)
    lp_week  = 0.9
    lp_topic = 2.4
    lp_llo   = 3.3
    lp_meth  = 3.1
    lp_res   = 3.6
    lp_ass   = 2.6
    lp_fixed_sum = lp_week + lp_topic + lp_llo + lp_meth + lp_res + lp_ass
    co_w  = max(0.8, round((lp_avail - lp_fixed_sum) / max(n_clo, 1), 3))
    n_lp_cols = lp_n

    lp_spec = (
        r'|C{' + w(lp_week)  + r'}'
        r'|L{' + w(lp_topic) + r'}'
        r'|L{' + w(lp_llo)   + r'}' +
        ''.join([r'|C{' + w(co_w) + r'}' for _ in clos]) +
        r'|L{' + w(lp_meth) + r'}'
        r'|L{' + w(lp_res)  + r'}'
        r'|L{' + w(lp_ass)  + r'}|'
    )

    co_header_cell = (
        r'\multicolumn{' + str(n_clo) + r'}{c|}{\textbf{Course Outcomes}}'
        if n_clo else ''
    )
    co_codes_row = ' & '.join(
        [r'\textbf{' + esc(c.get('code', f'CO{i+1}')) + r'}' for i, c in enumerate(clos)]
    )

    def lp_header_row1():
        parts = [r'\textbf{Week}', r'\textbf{Topics}', r'\textbf{Lesson Learning Outcome (LLO)}']
        if n_clo:
            parts.append(co_header_cell)
        parts += [
            r'\textbf{Teaching Learning Activities / Methodologies}',
            r'\textbf{Learning Resources}',
            r'\textbf{Assessment}',
        ]
        return ' & '.join(parts) + r' \\'

    def lp_header_row2():
        parts = [' ', ' ', ' ']
        if n_clo:
            parts.append(co_codes_row)
        parts += [' ', ' ', ' ']
        return ' & '.join(parts) + r' \\'

    lines.append(r'\noindent\begin{longtable}{' + lp_spec + '}')
    lines.append(r'\hline')
    lines.append(lp_header_row1())
    lines.append(r'\hline')
    lines.append(lp_header_row2())
    lines.append(r'\hline')
    lines.append(r'\endfirsthead')
    lines.append(r'\hline')
    lines.append(lp_header_row1())
    lines.append(r'\hline')
    lines.append(lp_header_row2())
    lines.append(r'\hline')
    lines.append(r'\endhead')

    if lp:
        for row_data in lp:
            cos_map = row_data.get('cos', {})
            row = [
                esc(str(row_data.get('week', ''))),
                esc_nl(row_data.get('topic', '')),
                esc_nl(row_data.get('llo', '')),
            ]
            for clo in clos:
                checked = cos_map.get(clo.get('code', ''), False)
                row.append(r'$\checkmark$' if checked else '')
            row += [
                esc_nl(row_data.get('methods', '')),
                esc_nl(row_data.get('resources', '')),
                esc_nl(row_data.get('assessment', '')),
            ]
            lines.append(' & '.join(row) + r' \\')
            lines.append(r'\hline')
    else:
        blanks = [''] * (n_lp_cols - 1)
        lines.append('-- & ' + ' & '.join(blanks) + r' \\')
        lines.append(r'\hline')
    lines.append(r'\end{longtable}')
    lines.append('')

    # ── 6. Grading System ─────────────────────────────────────────────────────
    lines += section(6, 'Grading System')
    gw = round(ca(4) / 4, 3)
    lines.append(
        r'\noindent\begin{longtable}{|C{' + w(gw) + r'}|C{' + w(gw) + r'}|C{' + w(gw) + r'}|C{' + w(gw) + r'}|}'
    )
    lines.append(r'\hline')
    lines.append(r'\multicolumn{4}{|c|}{\textbf{Grade Equivalent}} \\')
    lines.append(r'\hline')
    lines.append(r'\endfirsthead')
    lines.append(r'\hline')
    lines.append(r'\multicolumn{4}{|c|}{\textbf{Grade Equivalent}} \\')
    lines.append(r'\hline')
    lines.append(r'\endhead')
    # Editable scale: fill the left column pair first, then the right.
    grading = [g for g in course.get('grading_system', [])
               if str(g.get('range', '')).strip() or str(g.get('grade', '')).strip()]
    half = (len(grading) + 1) // 2
    def gcell(g):
        rng = esc(g.get('range', '')).replace('–', '--').replace('—', '--')
        return [rng, esc(g.get('grade', ''))]
    for i in range(half):
        right = gcell(grading[half + i]) if half + i < len(grading) else ['', '']
        lines.append(' & '.join(gcell(grading[i]) + right) + r' \\')
    lines.append(r'\hline')
    lines.append(r'\end{longtable}')
    lines.append('')

    # ── 7. References ─────────────────────────────────────────────────────────
    lines += section(7, 'References')
    for section_name, key in [('Textbooks', 'textbooks'), ('Journals', 'journals'), ('Online Resources', 'online')]:
        items = [r for r in refs.get(key, []) if str(r).strip()]
        if items:
            lines.append(r'\noindent\textbf{' + section_name + r'}\\[2pt]')
            for i, ref in enumerate(items, 1):
                lines.append(r'\hspace{0.5cm}' + str(i) + '. ' + esc(ref) + r'\\[2pt]')
            lines.append('')

    # ── 8. Classroom Policies ─────────────────────────────────────────────────
    lines += section(8, 'Classroom Policies')
    for i, pol in enumerate(policies, 1):
        lines.append(r'\noindent ' + str(i) + '. ' + esc_nl(pol) + r'\par')
    lines.append('')

    # ── 9. Approval ───────────────────────────────────────────────────────────
    lines += section(9, 'Approval')
    aw = round(ca(3) / 3, 3)
    lines.append(
        r'\noindent\begin{longtable}{|C{' + w(aw) + r'}|C{' + w(aw) + r'}|C{' + w(aw) + r'}|}'
    )
    lines.append(r'\hline')
    lines.append(r'\textbf{Prepared by:} & \textbf{Reviewed by:} & \textbf{Approved by:} \\')
    lines.append(r'\hline')
    lines.append(r' & & \\[28pt]')
    lines.append(r'\hline')
    lines.append(r'\underline{\hspace{5.0cm}} & \underline{\hspace{5.0cm}} & \underline{\hspace{5.0cm}} \\[2pt]')
    lines.append(r'\hline')
    lines.append(r'Faculty Member & Academic Program Coordinator & Department Chairperson \\')
    lines.append(r'\hline')
    lines.append(r'\end{longtable}')
    lines.append('')

    lines.append(r'\end{document}')
    return '\n'.join(lines)


def generate(course, outcomes, out_path):
    tex = generate_tex(course, outcomes)
    tmp = tempfile.mkdtemp()
    tex_file = os.path.join(tmp, 'syllabus.tex')
    with open(tex_file, 'w', encoding='utf-8') as f:
        f.write(tex)

    for _ in range(2):
        result = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', '-output-directory', tmp, tex_file],
            capture_output=True, text=True, errors='replace', cwd=tmp, timeout=120,
        )

    pdf_tmp = os.path.join(tmp, 'syllabus.pdf')
    if not os.path.exists(pdf_tmp):
        log = (result.stdout + result.stderr)[-4000:]
        raise RuntimeError(f'pdflatex failed:\n{log}')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    shutil.copy2(pdf_tmp, out_path)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    data    = json.loads(sys.stdin.read())
    course  = data['course']
    outcomes = data['outcomes']
    out_dir  = data.get('output_dir', '/tmp')
    out_path = os.path.join(out_dir, f"{course.get('code', 'syllabus')}_syllabus.pdf")
    generate(course, outcomes, out_path)
    print(out_path)
