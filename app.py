from flask import Flask, render_template, request, jsonify, send_file
import jinja2
import subprocess
import os
import json
import re
import threading

app = Flask(__name__)
app.secret_key = 'mscs-curriculum-editor'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_TEX = os.path.join(BASE_DIR, 'curriculum_template.tex')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
DATA_FILE = os.path.join(BASE_DIR, 'form_data.json')

os.makedirs(OUTPUT_DIR, exist_ok=True)

compilation_status = {'status': 'idle', 'message': '', 'pdf_ready': False}
status_lock = threading.Lock()

latex_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(BASE_DIR),
    block_start_string=r'\BLOCK{',
    block_end_string=r'}',
    variable_start_string=r'\VAR{',
    variable_end_string=r'}',
    comment_start_string=r'\#{',
    comment_end_string=r'}',
    trim_blocks=False,
    autoescape=False,
)

DEFAULTS = {
    # Program Outcomes — columns of the curriculum map
    'outcomes': [
        {'code': 'PLO1', 'title': 'Analytical and Critical Thinking'},
        {'code': 'PLO2', 'title': 'Scholarship and Research'},
        {'code': 'PLO3', 'title': 'Collaboration and Communication'},
        {'code': 'PLO4', 'title': 'Professionalism and Ethics'},
    ],
    'program_full_name': 'Master of Science in Computer Science',
    'program_abbr': 'MSCS',
    'proposal_subtitle': 'Proposal for Curriculum Revision',
    'department': 'Department of Computer Science',
    'college': 'College of Computer Studies',
    'university': 'MSU - Iligan Institute of Technology',
    'proponent': 'MSU - IIT',
    'campus_offering': 'None',
    # Dept Committee
    'dept_member_1': 'ORVEN E. LLANTOS, PhD.',
    'dept_member_2': 'DANTE D. DINAWANAO',
    'dept_member_3': 'RENATO V. CRISOSTOMO',
    'dept_member_4': 'ALQUINE ROY F. TACULIN',
    'dept_member_5': 'HAROUN A. R. C. P. MACALISANG',
    'dept_member_6': 'JENNIFER JOYCE M. MONTEMAYOR',
    'dept_chair': 'MALIKEY M. MAULANA',
    # College Committee
    'college_dean': 'ATTY. EDDIE BOUY B. PALAD',
    'college_dean_role': 'Acting Dean, College of Computer Studies',
    'college_asst_dean': 'JERAME B. BELOY',
    'college_member_1': 'RABBY Q. LAVILLES',
    'college_member_2': 'CENIE V. MALABANAN, PhD.',
    'college_member_3': 'ANTONIO S. MARAJAS',
    'college_member_4': 'MICHAEL A. NABUA',
    'college_member_5': 'ERIK LOUWE R. SALA',
    'college_member_6': 'PAUL B. BOKINGKITO, JR.',
    'college_chair': 'RENATO V. CRISOSTOMO',
    # Campus Committee
    'campus_member_1': 'HILTON J. AGUJA',
    'campus_member_1_role': 'Member',
    'campus_member_2': 'SHIELA M. MENCHAVEZ',
    'campus_member_2_role': 'Member',
    'campus_member_3': 'ANGELINE L. TEATRO',
    'campus_member_3_role': 'Member',
    'campus_member_4': 'REYA T. SENO',
    'campus_member_4_role': 'Member',
    'campus_member_5': 'IRISH F. DALONA',
    'campus_member_5_role': 'Ex-Officio Member, CGEM',
    'campus_member_6': 'CECILIA B. TANGIAN',
    'campus_member_6_role': 'Ex-Officio Member, CAELL',
    'campus_chair': 'JOCELYN P. VILELA',
    'chancellor': 'PROF. ALIZEDNEY M. DITUCALAN, JD, LLM',
    # Approval Dates
    'date_apc': '',
    'date_campus_council': '',
    'date_university_council': '',
    'date_bor': '',
    'date_implementation': '',
    # Features of the Revision
    'features_intro': 'The revised program of Master of Science in Computer Science (MSCS) contains several features and characteristics relevant to the current trends and standards.',
    'feature_1': 'The revised program is an academic track and has a total of 34 units.',
    'feature_2': 'Revising the core courses into four (4) theory courses with a total of twelve (12) units, in compliance with CMO No. 7, series of 2010',
    'feature_3': 'Addition of new requirement for comprehensive examination required under CMO No. 15, series of 2019',
    'feature_4': 'Addition of new requirement for special common course for the mainstreaming of peace and development',
    'feature_5': 'Addition of new requirement for systematic literature review and seminar leading to research capability development',
    'feature_6': 'Addition of new and relevant specialization courses under theory and systems category',
    'feature_7': 'Compliance with the Outcomes-based QA in higher education as prescribed by Commission on Higher Education (CHED)',
    'feature_8': 'Use of the new prefix CSC in all of its courses',
    'feature_9': 'Compliance with the standard course coding of the Institute',
    # Rationale
    'rationale': (
        'The field of computing is dynamic and has developed into mature and independent discipline as Computer Science. '
        'The timely and rapid developments in computing technology such as artificial intelligence, data mining, data communications, '
        'and security anchored on the theories and principles of computing continue to enrich the discipline.\n\n'
        'The Department of Computer Science, in order to rectify perceived deficiencies in the old program and to maintain its '
        'relevance and currency, advance this revision. The impact of this rapidly evolving discipline where its technology '
        'contributions become part of everyday life of the people will require the new program to adjust its graduate curriculum '
        'for the new attributes and competencies required in this modern digital era.\n\n'
        'In view of the guidelines of the CHED prescribing the criteria and standards of MSCS program and the latest policies, '
        'standards and guidelines for graduate programs, the proposed revised program is an academic track with courses '
        'incorporating the latest trends in artificial intelligence and analytics. The revised program is deemed to provide '
        'the balance of theory and practice.\n\n'
        'The Computer Science graduate curriculum is based on local, national, and international criteria and standards. '
        'This means that the graduates of the program will be adequately prepared for advanced academic pursuits, and they '
        'will be equipped with the knowledge and skills required for the Industry 4.0 implementation. The outcomes-based '
        'quality assurance is expected to address these goals through the compliance of standards set by CHED Memo 46, series 2012.\n\n'
        'This curricular revision will mainstream the promotion of peace and development in Mindanao and beyond -- computing '
        'with its inevitable roles as a tool in shaping or aiding the socio-cultural, socio-political, and socio-economic '
        'aspects of society, its pervasiveness in government, business, industry, education, and all sectors of society in general. '
        'The ubiquity of the computing technology enabled people to communicate, collaborate, interact, and share ideas, thereby '
        'providing opportunities for unity and borderless communities and better understanding among people.'
    ),
    # Program Objectives
    'prog_obj_intro': (
        'The goal of the program administration of Computer Science is to provide excellence in Computer Science program '
        'through modern application of computing. The MSCS should always be responsive to the modern trends and aligned to '
        'the standards of the discipline and use the best recognized practices to produce reliable and successful professionals.'
    ),
    # Graduate Outcomes (MSCS)
    'plo1_title': 'Analytical and Critical Thinking',
    'plo1_desc': 'Ability to think critically, creatively and solve complex problems in the field of computing.',
    'plo2_title': 'Scholarship and Research',
    'plo2_desc': 'Ability to conduct original research, scholarship or creative endeavors using the advanced knowledge of the emerging computing technologies.',
    'plo3_title': 'Collaboration and Communication',
    'plo3_desc': 'Ability to effectively work with others and communicate in the field of computing, through scholarly writing and presentations to various audiences.',
    'plo4_title': 'Professionalism and Ethics',
    'plo4_desc': 'Ability to evaluate social and environmental issues in computing endeavors and make decisions in accordance to an ethical and responsible professional practices.',
    # Graduate Outcome Common
    'common_outcome_intro': 'The College of Computer Studies commits to the achievement of following common attribute for its graduate programs stated below:',
    'common_outcome_quote': 'Ability to use advanced knowledge and skills in ICT to promote peace and development.',
    # Program Educational Objectives
    'peo_intro': 'The program educational objectives (PEO) of the MSCS is to achieve the set of attributes for the alumni achievable after graduation are given below.',
    'peo_1': 'Engage in the productive practice as Computer Science professional to solve complex and significant problems across broad-range of application areas.',
    'peo_2': 'Adapt to technology advances and acquire new knowledge through continued professional growth and by embracing life-long learning.',
    'peo_3': 'Make well-rounded and fair decisions when faced with social, ethical, legal, and environmental issues inherent to computing practices.',
    'peo_4': 'Communicate effectively with their peers, clients, supervisors through both written and oral means.',
    # Eligibility
    'eligibility_text': 'The discipline of Computer Science was granted with Center of Development (COD) by the Commission on Higher Education (CHED) in the corresponding undergraduate program and still holding such status at present.',
    # Assessment & CQI
    'assessment_text': (
        'Assessment of the program is based on the evidences or outputs from the selected courses that supports for the '
        'achievement of its outcomes. The learning outcomes of each course are aligned constructively to support the '
        'achievement of the program learning outcomes (PLOs). The Curriculum Map provides the relationships of the courses and the Program Learning Outcomes.\n\n'
        'The details of program assessment and evaluation, and the continuous quality improvement are found in the Appendix.'
    ),
    'cqi_text': (
        'The assessment and evaluation results will help identify the areas that are considered best and should be maintained. '
        'More importantly, the results will also help identify the areas that need improvements.\n\n'
        'The details of program assessment and evaluation, and the continuous quality improvement are found in the Appendix.'
    ),
    # Course registry — single source of truth
    # knowledge_area groups courses in the curriculum map (matches ACM CS Curricula 2013 KAs)
    # plo_map values use I/P/D notation: I=Introduced, P=Practiced, D=Demonstrated, IP, IPD, etc.
    'courses': [
        {'code': 'CSC201', 'title': 'Advanced Data Structures and Algorithms', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Algorithms and Complexity (AL)',
         'desc': 'Introduction to problem solving methods and algorithm development; data abstraction for structures such as stacks, queues, linked lists, trees, and graphs; searching and sorting algorithms and their analysis.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'I', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC204', 'title': 'Automata and Computation Theory', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Algorithms and Complexity (AL)',
         'desc': 'Theoretical foundations of computer science. Formal languages and automata; regular expressions, context-free languages, parsing; Turing machines and complexity; partial recursive functions; undecidability; program correctness.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'I', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC202', 'title': 'Computer Architecture and Operating Systems', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Architecture and Organization (AR)',
         'desc': 'Fundamentals of operating system design and structure, resource management, and system support for multicore. Topics include scheduling, synchronization, system structure, virtual address spaces, memory management, I/O management.',
         'plo_map': {'PLO1': 'IP', 'PLO2': '', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC210', 'title': 'Computer Modeling and Simulation', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Computational Science (CN)',
         'desc': 'Computational methods for continuous and discrete system simulation; effects of computer software and hardware architectures on computational precision and accuracy requirements. Random-number generation and testing; calibration and scaling technique.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC291', 'title': 'Advanced Topics in Computational Science', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Computational Science (CN)',
         'desc': 'This course explores foundational and advanced methods in computational science, including numerical modeling, algorithmic simulation, and high-performance computing for solving real-world scientific problems. Emphasis is placed on understanding the computational representations of physical systems, validation of numerical methods, and interpretation of simulation results in various domains. Topics may include numerical linear algebra, finite difference methods, Monte Carlo methods, parallel computing, and data-driven modeling using machine learning.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': 'P', 'PLO4': 'P'}},
        {'code': 'CSC208', 'title': 'Cryptography', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Information Assurance and Security (IAS)',
         'desc': 'Review of mathematical theory for cryptography; classical ciphers; modern block and stream ciphers; symmetric and asymmetric systems; digital signatures; public key infrastructure; authentication.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'I', 'PLO3': '', 'PLO4': 'IP'}},
        {'code': 'CSC215', 'title': 'Computer Security', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Information Assurance and Security (IAS)',
         'desc': 'Functional description of cryptographic primitives; risk analysis; policy models; design principles; assurance; malicious logic.',
         'plo_map': {'PLO1': 'IP', 'PLO2': '', 'PLO3': '', 'PLO4': 'IP'}},
        {'code': 'CSC224', 'title': 'Data Analytics and Visualization', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Information Management (IM)',
         'desc': 'This course introduces students to the fundamental concepts and techniques in data analytics and visualization. It covers data wrangling, exploratory data analysis, statistical modeling, machine learning techniques, and effective visualization methods using contemporary tools. Emphasis is placed on data-driven decision-making, ethical considerations, and storytelling with data to support analytical thinking.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': 'P', 'PLO4': 'P'}},
        {'code': 'CSC290', 'title': 'Database Theory', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Information Management (IM)',
         'desc': 'Concepts in database systems. Relational database design. Editing, report generation, updating, schema refinement, tuning. Construction of database management systems. Conceptual and logical design of a database.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'P', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC211', 'title': 'Natural Language Studies', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Intelligent Systems (IS)',
         'desc': 'This course explores the structure, function, and cognitive dimensions of human language, focusing on phonetics, phonology, morphology, syntax, semantics, and pragmatics. It draws from linguistic theory to examine how natural language is acquired, used, and represented mentally. Applications in technology, society, and education are also discussed, preparing students for interdisciplinary research or application in computational linguistics, NLP, and cognitive science.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': 'IP', 'PLO4': 'IP'}},
        {'code': 'CSC217', 'title': 'Computer Vision', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Intelligent Systems (IS)',
         'desc': 'Image signal processing and filtering. Saliency, features and feature extraction, tracking, stereo disparity estimation, structure form motion, photogrammetry, optic flow, homography estimation and warping.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC218', 'title': 'Machine Learning', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Intelligent Systems (IS)',
         'desc': 'Machine learning algorithms: nearest-neighbor, regression, classification, perceptron, kernel methods, support vector machine (SVM), logistic regression, ensemble methods, boosting, graphical models, hidden Markov models (HMM), non-parametrics.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC220', 'title': 'Data Mining', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Intelligent Systems (IS)',
         'desc': 'Fundamental concepts of data mining. Algorithm techniques for data mining, including classification, clustering, association rules mining.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC227', 'title': 'Advanced Computer Networks', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Networking and Communications (NC)',
         'desc': 'Fundamental concepts in the design and implementation of computer communication networks; layered network architectures, applications, network programming interfaces, transport, routing, data link protocols, local area networks, network management, and network security.',
         'plo_map': {'PLO1': 'IP', 'PLO2': '', 'PLO3': '', 'PLO4': 'P'}},
        {'code': 'CSC228', 'title': 'Parallel and Distributed Systems', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Operating Systems (OS)',
         'desc': 'Algorithmic and implementation challenges in building large-scale distributed applications; distributed coordination, scheduling, consistency issues, and fault tolerance algorithms; fundamental distributed systems concepts applied to both high-performance computing and cloud computing environments.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CSC203', 'title': 'Programming Language Theory', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Programming Languages (PL)',
         'desc': 'Fundamental concepts underlying design of programming languages; detailed study of functional and object-oriented computational models; types, evaluation, abstraction, controlflow, modules, mutation, laziness, polymorphism, subtyping, inheritance.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'I', 'PLO3': '', 'PLO4': ''}},
        {'code': 'CCC296', 'title': 'ICT for Peace and Development', 'credits': '1', 'prereq': 'None',
         'knowledge_area': 'Social Issues and Professional Practice (SP)',
         'desc': 'Mainstreaming peace and development principles in computing; role of ICT in promoting social harmony, development, and conflict resolution.',
         'plo_map': {'PLO1': '', 'PLO2': '', 'PLO3': 'IP', 'PLO4': 'IP'}},
        {'code': 'CCC297', 'title': 'Systematic Review and Research Seminar in ICT', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Social Issues and Professional Practice (SP)',
         'desc': 'Systematic literature review methods; research proposal development; scholarly writing; presentation skills; research ethics and responsible conduct of research.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': 'IP', 'PLO4': 'P'}},
        {'code': 'CCC298', 'title': 'Methods of Research', 'credits': '3', 'prereq': 'None',
         'knowledge_area': 'Social Issues and Professional Practice (SP)',
         'desc': 'Research design and methodology; quantitative and qualitative approaches; data collection and analysis techniques; research writing and publication.',
         'plo_map': {'PLO1': 'IP', 'PLO2': 'IP', 'PLO3': 'IP', 'PLO4': 'P'}},
        {'code': 'CSC299', 'title': "Master's Thesis", 'credits': '6', 'prereq': 'CCC298',
         'knowledge_area': 'Social Issues and Professional Practice (SP)',
         'desc': 'Original research under the supervision of a faculty adviser; thesis writing and defense.',
         'plo_map': {'PLO1': 'D', 'PLO2': 'D', 'PLO3': 'IP', 'PLO4': 'IP'}},
    ],
}


def latex_escape(val):
    if isinstance(val, str):
        specials = {'&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
                    '_': r'\_', '{': r'\{', '}': r'\}',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
        return ''.join(specials.get(c, c) for c in val)
    if isinstance(val, list):
        return [latex_escape(item) for item in val]
    if isinstance(val, dict):
        return {k: latex_escape(v) for k, v in val.items()}
    return val


def load_data():
    data = DEFAULTS.copy()
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            data.update(json.load(f))
    return data


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def run_compilation(data):
    global compilation_status
    try:
        with status_lock:
            compilation_status = {'status': 'compiling', 'message': 'Rendering LaTeX template...', 'pdf_ready': False}

        escaped = {k: latex_escape(v) for k, v in data.items()}

        # Pre-compute curriculum map column spec from outcomes
        outcomes = data.get('outcomes', [])
        n = len(outcomes)
        escaped['outcome_col_spec'] = '|'.join(['C{.52in}'] * n) + '|'
        escaped['n_outcomes'] = n
        escaped['n_outcomes_plus_1'] = n + 1   # code col + N outcome cols

        template = latex_env.get_template('curriculum_template.tex')
        rendered = template.render(**escaped)

        tex_out = os.path.join(OUTPUT_DIR, 'curriculum.tex')
        with open(tex_out, 'w') as f:
            f.write(rendered)

        for pass_num in range(1, 3):
            with status_lock:
                compilation_status['message'] = f'Running pdflatex (pass {pass_num}/2)...'

            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-output-directory', OUTPUT_DIR, tex_out],
                capture_output=True, text=True, cwd=OUTPUT_DIR, timeout=120
            )

        pdf_path = os.path.join(OUTPUT_DIR, 'curriculum.pdf')
        if os.path.exists(pdf_path):
            with status_lock:
                compilation_status = {'status': 'done', 'message': 'PDF compiled successfully!', 'pdf_ready': True}
        else:
            log = (result.stdout + result.stderr)[-3000:]
            with status_lock:
                compilation_status = {'status': 'error', 'message': f'Compilation failed:\n{log}', 'pdf_ready': False}

    except Exception as e:
        with status_lock:
            compilation_status = {'status': 'error', 'message': str(e), 'pdf_ready': False}


@app.route('/')
def index():
    return render_template('index.html', data=load_data())


@app.route('/compile', methods=['POST'])
def compile_pdf():
    with status_lock:
        if compilation_status['status'] == 'compiling':
            return jsonify({'error': 'Already compiling'}), 409
    form_data = request.get_json() or {}
    data = DEFAULTS.copy()
    data.update(form_data)
    save_data(data)
    threading.Thread(target=run_compilation, args=(data,), daemon=True).start()
    return jsonify({'message': 'Compilation started'})


@app.route('/save', methods=['POST'])
def save():
    form_data = request.get_json() or {}
    data = DEFAULTS.copy()
    data.update(form_data)
    save_data(data)
    return jsonify({'message': 'Saved'})


@app.route('/status')
def get_status():
    with status_lock:
        return jsonify(compilation_status)


@app.route('/download')
def download_pdf():
    pdf_path = os.path.join(OUTPUT_DIR, 'curriculum.pdf')
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'No PDF yet'}), 404
    return send_file(pdf_path, as_attachment=True, download_name='MSCS-Curriculum.pdf')


# ── Syllabus editor ─────────────────────────────────────────────────────────

DEFAULT_POLICIES = [
    'Your instructor may or may not explicitly check attendance every day. However, if you are caught exceeding your allowable cuts for the semester, you may be given a grade of 5.00.',
    'In case you cut, it will be your responsibility to know the material covered for the day. The instructor reserves the right to give unannounced quizzes or graded lab exercises at any time.',
    'No makeup tests will be given unless you can present a medical certificate or an immediate member of your family died. Make up tests will solely be on the teacher\'s discretion.',
    'Playing games is strictly prohibited during class hours. Web browsing and doing email are also prohibited, unless done in connection with the current lecture or lab topic and allowed by the teacher.',
    'Use of communication devices is prohibited during class hours. Please turn them off during class.',
    'Class requirements are due during class hours, unless otherwise specified. Late submission will merit deductions as specified by the teacher.',
    'Cheating will not be tolerated. Cheating in any requirement will result in a minimum penalty of having a grade of 0 for that requirement. Duplicated projects/lab exercises will merit penalties for both the student who copied and the student from whom the work was copied.',
    'Additional policies, with due consultation with the students, may be implemented by the teacher to adapt to the class environment. Students are advised to be aware of such updates, and to ask their instructor if anything is unclear.',
]


# Standard MSU-IIT grade equivalents; seeds each course's editable grading system.
DEFAULT_GRADING_SYSTEM = [
    {'range': '97% – 100%', 'grade': '1.00'},
    {'range': '94% – 96%',  'grade': '1.25'},
    {'range': '91% – 93%',  'grade': '1.50'},
    {'range': '88% – 90%',  'grade': '1.75'},
    {'range': '85% – 87%',  'grade': '2.00'},
    {'range': '82% – 84%',  'grade': '2.25'},
    {'range': '79% – 81%',  'grade': '2.50'},
    {'range': '76% – 78%',  'grade': '2.75'},
    {'range': '75%',        'grade': '3.00'},
    {'range': 'Below 75%',  'grade': '5.00'},
]


# Semester each core course is fixed to in the curriculum ("Distribution of Courses by
# Semester"). Electives/specialization courses have no fixed term; the user picks one.
CURRICULUM_SEMESTERS = {
    'CSC201': ('1st Semester', 'First Year, First Semester'),
    'CSC202': ('1st Semester', 'First Year, First Semester'),
    'CSC203': ('2nd Semester', 'First Year, Second Semester'),
    'CSC204': ('2nd Semester', 'First Year, Second Semester'),
    'CCC298': ('2nd Semester', 'First Year, Second Semester'),
    'CCC296': ('1st Semester', 'Second Year, First Semester'),
    'CCC297': ('1st Semester', 'Second Year, First Semester'),
    'CSC299': ('2nd Semester', 'Second Year, Second Semester'),
}

_AY_YEAR_PREFIX_RE = re.compile(r'^\s*\d{4}\s*[-–]\s*\d{4}\s*,?\s*')


def ay_semester_complete(value):
    """True when a semester is set. The academic year is optional, so '1st Semester',
    'As offered' and '2026–2027, 1st Semester' all count; '2025–2026' alone does not."""
    return bool(_AY_YEAR_PREFIX_RE.sub('', value or '', count=1).strip())


def get_course_index(data, code):
    for i, c in enumerate(data.get('courses', [])):
        if c.get('code') == code:
            return i
    return -1


def ensure_syllabus_fields(course):
    course.setdefault('modality', 'Blended/Online')
    course.setdefault('contact_hours', '3 hours lecture')
    course.setdefault('ay_semester', '')
    course.setdefault('clos', [])
    course.setdefault('learning_plan', [])
    course.setdefault('assessment_blueprint', [])
    course.setdefault('references', {'textbooks': [''], 'journals': [''], 'online': ['']})
    course.setdefault('policies', list(DEFAULT_POLICIES))
    course.setdefault('grading_system', [dict(r) for r in DEFAULT_GRADING_SYSTEM])
    # Build clo_plo_map from existing plo_map when first opening syllabus editor
    if not course.get('clo_plo_map'):
        plo_map = course.get('plo_map', {})
        clo_plo = {}
        for clo in course.get('clos', []):
            clo_code = clo.get('code', '')
            clo_plo[clo_code] = {so: bool(val) for so, val in plo_map.items()}
        course['clo_plo_map'] = clo_plo
    return course


@app.route('/syllabus/<code>')
def syllabus_editor(code):
    data = load_data()
    idx = get_course_index(data, code)
    if idx < 0:
        return f'Course {code} not found', 404
    course = dict(data['courses'][idx])
    ensure_syllabus_fields(course)
    outcomes = data.get('outcomes', DEFAULTS['outcomes'])
    sem = CURRICULUM_SEMESTERS.get(code)
    return render_template('syllabus.html', course=course, outcomes=outcomes,
                           default_grading=DEFAULT_GRADING_SYSTEM,
                           curriculum_semester=sem[0] if sem else '',
                           curriculum_term=sem[1] if sem else '')


@app.route('/syllabus/<code>/save', methods=['POST'])
def save_syllabus(code):
    payload = request.get_json() or {}
    data = load_data()
    idx = get_course_index(data, code)
    if idx < 0:
        return jsonify({'error': f'Course {code} not found'}), 404

    for field in ['title', 'desc', 'credits', 'prereq', 'modality', 'contact_hours', 'ay_semester',
                  'clos', 'clo_plo_map', 'learning_plan', 'assessment_blueprint', 'references', 'policies',
                  'grading_system']:
        if field in payload:
            data['courses'][idx][field] = payload[field]

    # Sync plo_map by aggregating I/P/D values across all CLOs for each PLO
    clo_plo = data['courses'][idx].get('clo_plo_map', {})
    outcomes = data.get('outcomes', DEFAULTS['outcomes'])
    new_plo = {}
    for o in outcomes:
        oc = o['code']
        letters = set()
        for clo_vals in clo_plo.values():
            for letter in (clo_vals.get(oc) or ''):
                if letter in ('I', 'P', 'D'):
                    letters.add(letter)
        new_plo[oc] = ''.join(l for l in ['I', 'P', 'D'] if l in letters)
    data['courses'][idx]['plo_map'] = new_plo

    save_data(data)
    return jsonify({'message': 'Saved', 'plo_map': new_plo})


@app.route('/syllabus/<code>/pdf')
def download_syllabus_pdf(code):
    data = load_data()
    idx = get_course_index(data, code)
    if idx < 0:
        return jsonify({'error': f'Course {code} not found'}), 404
    course = dict(data['courses'][idx])
    ensure_syllabus_fields(course)
    if not ay_semester_complete(course.get('ay_semester')):
        return ('Semester is required. Set it in Course Info before downloading the syllabus.', 400)
    outcomes_raw = data.get('outcomes', DEFAULTS['outcomes'])
    outcomes = []
    for o in outcomes_raw:
        i = o['code'].replace('PLO', '')
        enriched = dict(o)
        enriched['desc'] = data.get(f'plo{i}_desc', o.get('title', ''))
        outcomes.append(enriched)

    script = os.path.join(BASE_DIR, 'generate_syllabus_pdf.py')
    payload = json.dumps({'course': course, 'outcomes': outcomes, 'output_dir': OUTPUT_DIR})
    venv_python = os.path.join(BASE_DIR, 'venv', 'bin', 'python3')
    python = venv_python if os.path.exists(venv_python) else 'python3'

    try:
        result = subprocess.run([python, script], input=payload,
                                capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return jsonify({'error': result.stderr[-2000:]}), 500
        out_path = os.path.join(OUTPUT_DIR, f'{code}_syllabus.pdf')
        return send_file(out_path, as_attachment=True, download_name=f'{code}_syllabus.pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/syllabus/<code>/docx')
def download_syllabus_docx(code):
    data = load_data()
    idx = get_course_index(data, code)
    if idx < 0:
        return jsonify({'error': f'Course {code} not found'}), 404
    course = dict(data['courses'][idx])
    ensure_syllabus_fields(course)
    if not ay_semester_complete(course.get('ay_semester')):
        return ('Semester is required. Set it in Course Info before downloading the syllabus.', 400)
    outcomes_raw = data.get('outcomes', DEFAULTS['outcomes'])
    # Enrich outcomes with full PLO descriptions for the alignment table
    outcomes = []
    for o in outcomes_raw:
        idx = o['code'].replace('PLO', '')
        enriched = dict(o)
        enriched['desc'] = data.get(f'plo{idx}_desc', o.get('title', ''))
        outcomes.append(enriched)

    script = os.path.join(BASE_DIR, 'generate_syllabus_docx.py')
    payload = json.dumps({'course': course, 'outcomes': outcomes, 'output_dir': OUTPUT_DIR})
    venv_python = os.path.join(BASE_DIR, 'venv', 'bin', 'python3')
    python = venv_python if os.path.exists(venv_python) else '/tmp/docx-venv/bin/python3'

    try:
        result = subprocess.run([python, script], input=payload,
                                capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return jsonify({'error': result.stderr[-1000:]}), 500
        out_path = os.path.join(OUTPUT_DIR, f'{code}_syllabus.docx')
        return send_file(out_path, as_attachment=True, download_name=f'{code}_syllabus.docx')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/courses')
def api_courses():
    data = load_data()
    return jsonify({'courses': data.get('courses', []), 'outcomes': data.get('outcomes', [])})


@app.route('/tracker')
def get_tracker():
    data = load_data()
    return jsonify({'tracker': data.get('syllabus_tracker', {})})


@app.route('/tracker/save', methods=['POST'])
def save_tracker():
    payload = request.get_json() or {}
    data = load_data()
    data['syllabus_tracker'] = payload.get('tracker', {})
    save_data(data)
    return jsonify({'message': 'Saved'})


if __name__ == '__main__':
    print('Starting MSCS Curriculum Editor at http://127.0.0.1:8080')
    app.run(debug=True, port=8080)
