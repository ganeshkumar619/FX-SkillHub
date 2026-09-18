import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from catalogue.models import (
    Department,
    SkillCategory,
    SkillDomain,
    Skill,
    Course,
    Module,
    Lesson,
    LearningResource,
    VideoResource,
    StudyMaterial,
    PracticeTask
)
from assessments.models import (
    Assessment,
    Question,
    QuestionOption
)

User = get_user_model()


def generate_pdf_handbook(filepath, title, subtitle, sections):
    """Generates a real PDF study material using ReportLab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        doc = SimpleDocTemplate(str(filepath), pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#475569'),
            spaceAfter=18
        )
        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1e3a8a'),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            spaceAfter=8
        )

        elements = [
            Paragraph(title, title_style),
            Paragraph(f"Francis Xavier Engineering College (Autonomous) • {subtitle}", subtitle_style),
            Spacer(1, 10),
        ]

        for sec_title, sec_body in sections:
            elements.append(Paragraph(sec_title, heading_style))
            elements.append(Paragraph(sec_body, body_style))
            elements.append(Spacer(1, 6))

        doc.build(elements)
        return True
    except Exception as e:
        print(f"Warning: Could not generate PDF: {e}")
        return False


class Command(BaseCommand):
    help = "Populates comprehensive learning materials, lessons, videos, and assessment questions for all courses."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write(self.style.WARNING("POPULATING MATERIALS & ASSESSMENTS FOR ALL COURSES"))
        self.stdout.write(self.style.WARNING("=" * 70))

        with transaction.atomic():
            admin_user = User.objects.filter(role='ADMIN').first()
            faculty_user = User.objects.filter(role='MENTOR').first() or admin_user

            media_dir = Path(settings.MEDIA_ROOT)
            materials_dir = media_dir / 'materials'
            materials_dir.mkdir(parents=True, exist_ok=True)

            # 1. Generate PDF Handbooks for all courses
            self.stdout.write("Generating institutional PDF study handbooks...")
            handbooks = {
                'python_data_analysis_handbook.pdf': (
                    "Python for Data Analysis Official Handbook",
                    "Department of AI & Data Science",
                    [
                        ("1. NumPy Vectorized Computation", "NumPy provides high-performance multidimensional array objects (ndarray) and mathematical operations executed in optimized C. Broadcasting allows arithmetic operations across arrays with differing compatible shapes."),
                        ("2. Pandas DataFrames & Series", "Pandas structures data into 1D Series and 2D tabular DataFrames with aligned row/column indices. Common operations include filtering, missing value imputation, group aggregation, and merges."),
                        ("3. Data Cleaning & Transformation", "Real data contains missing values (NaN), duplicates, and incorrect types. Methods like dropna(), fillna(), drop_duplicates(), and astype() ensure data integrity."),
                        ("4. Exploratory Statistical Analysis", "EDA combines numerical summarization (describe, corr) with visualization (Matplotlib, Seaborn) to uncover patterns, anomalies, and hypotheses before predictive modeling.")
                    ]
                ),
                'java_fundamentals_handbook.pdf': (
                    "Java Fundamentals Official Handbook",
                    "Department of Information Technology",
                    [
                        ("1. Java Virtual Machine Architecture", "Java source code compiles into platform-independent bytecode (.class files) executed by the JVM using the ClassLoader, Bytecode Verifier, and Just-In-Time (JIT) compiler."),
                        ("2. Object-Oriented Principles", "Java strictly enforces object-oriented programming: Encapsulation via private members and accessors, Inheritance via extends, Polymorphism via overriding/overloading, and Abstraction via interfaces and abstract classes."),
                        ("3. Exception Handling Architecture", "Throwable branches into Error (serious system failures) and Exception. Exceptions divide into checked exceptions (must be caught or declared) and unchecked RuntimeExceptions."),
                        ("4. Java Collections Framework", "The framework provides unified interfaces (List, Set, Queue, Map) and performant concrete implementations such as ArrayList, LinkedList, HashSet, TreeSet, and HashMap.")
                    ]
                ),
                'advanced_java_enterprise_handbook.pdf': (
                    "Advanced Java Enterprise & Spring Boot Handbook",
                    "Department of Computer Science & Engineering",
                    [
                        ("1. Spring Boot & Dependency Injection", "The Spring IoC container manages bean lifecycles. Dependency Injection (DI) through constructor injection decouples components for modularity and testability."),
                        ("2. RESTful Web Services with Spring MVC", "Spring MVC routes HTTP requests to controller methods via @RestController, @GetMapping, @PostMapping, and handles serialization using Jackson."),
                        ("3. Spring Data JPA & Hibernate ORM", "Spring Data JPA reduces boilerplate data access logic via CrudRepository and JpaRepository, automatically generating SQL queries from method naming conventions."),
                        ("4. Stateless JWT Security & Microservices", "Spring Security 6 enforces stateless authentication using JSON Web Tokens (JWT) verified in custom security filters before endpoint execution.")
                    ]
                ),
                'fullstack_react_node_handbook.pdf': (
                    "Enterprise Full Stack (React & Node.js) Handbook",
                    "Department of Computer Science & Centre for Training",
                    [
                        ("1. Declarative UI with React & TypeScript", "React utilizes a virtual DOM and unidirectional data flow. Functional components leverage hooks (useState, useEffect, useMemo) for responsive component state."),
                        ("2. Node.js & Express REST APIs", "Node.js provides a single-threaded, non-blocking asynchronous event loop. Express organizes modular routing and request-response middleware pipelines."),
                        ("3. Relational Persistence & Transactions", "Full stack architectures require ACID transactional guarantees, indexed relations, foreign key constraints, and parameterized SQL queries to prevent injection."),
                        ("4. JWT Authentication & Production Hardening", "Stateless authentication uses signed JWTs stored securely. Production pipelines include CORS restrictions, helmet HTTP headers, rate limiting, and automated CI/CD builds.")
                    ]
                )
            }

            for filename, (title, subtitle, secs) in handbooks.items():
                pdf_path = materials_dir / filename
                if not pdf_path.exists():
                    generate_pdf_handbook(pdf_path, title, subtitle, secs)
                    self.stdout.write(f"  + Generated {filename}")

            # =========================================================================
            # HELPER FUNCTION TO SEED OR UPDATE A COMPLETE MODULE
            # =========================================================================
            def seed_module_content(course, order, title, topic_tag, desc, duration,
                                    video_title, video_url,
                                    structured_notes, pdf_rel_path,
                                    practice_title, practice_mcqs):
                module, _ = Module.objects.update_or_create(
                    course=course,
                    order=order,
                    defaults={
                        'title': title,
                        'topic_tag': topic_tag,
                        'description': desc,
                        'duration_minutes': duration,
                        'estimated_minutes': duration,
                        'is_required': True,
                        'status': 'PUBLISHED',
                        'source_type': 'FXEC_OFFICIAL',
                        'source_title': 'FXEC Autonomous Curriculum 2026',
                        'source_url': 'https://www.francisxavier.ac.in/',
                        'created_by': faculty_user
                    }
                )

                lesson, _ = Lesson.objects.update_or_create(
                    module=module,
                    order=1,
                    defaults={
                        'title': f"{title} - Core Concepts & Lab Guide",
                        'description': desc,
                        'content_type': 'TEXT',
                        'text_content': structured_notes.get('concept_explanation', desc),
                        'concept_explanation': structured_notes.get('concept_explanation', ''),
                        'summary': structured_notes.get('introduction', ''),
                        'duration_minutes': duration,
                        'estimated_minutes': duration,
                        'is_required': True,
                        'status': 'PUBLISHED',
                        'source_type': 'FXEC_OFFICIAL',
                        'created_by': faculty_user
                    }
                )

                VideoResource.objects.update_or_create(
                    module=module,
                    order=1,
                    defaults={
                        'lesson': lesson,
                        'title': video_title,
                        'description': desc,
                        'video_type': 'EXTERNAL_VIDEO',
                        'external_url': video_url,
                        'duration_seconds': 300,
                        'completion_threshold_percent': 80.0,
                        'is_required': True,
                        'status': 'PUBLISHED',
                        'source_type': 'FXEC_OFFICIAL',
                        'created_by': faculty_user
                    }
                )

                StudyMaterial.objects.update_or_create(
                    module=module,
                    order=1,
                    defaults={
                        'lesson': lesson,
                        'title': f"{title} - AI Study Guide & Reference Notes",
                        'description': desc,
                        'resource_type': 'AI_STUDY_NOTES',
                        'file': pdf_rel_path,
                        'structured_content': structured_notes,
                        'text_content': f"# {title}\n\n{structured_notes.get('introduction', '')}\n\n## Core Concepts\n{structured_notes.get('concept_explanation', '')}\n\n## Syntax\n```\n{structured_notes.get('syntax', '')}\n```",
                        'completion_method': 'MANUAL_COMPLETE',
                        'version': 1,
                        'is_required': True,
                        'status': 'PUBLISHED',
                        'explanation_level': 'BEGINNER',
                        'model_provider': 'FXEC AI Engine (Gemini 2.5)',
                        'review_status': 'APPROVED',
                        'source_type': 'FXEC_OFFICIAL',
                        'source_title': 'FXEC Curriculum Reference',
                        'source_url': 'https://www.francisxavier.ac.in/',
                        'uploaded_by': faculty_user,
                        'reviewed_by': faculty_user,
                        'reviewed_at': timezone.now()
                    }
                )

                PracticeTask.objects.update_or_create(
                    module=module,
                    order=1,
                    defaults={
                        'lesson': lesson,
                        'title': practice_title,
                        'description': f"Practice quiz and concept check for {title}.",
                        'task_type': 'MCQ_PRACTICE',
                        'difficulty': 'MEDIUM',
                        'content': {'questions': practice_mcqs},
                        'explanation': f"Review all fundamental principles of {title} to achieve 100% mastery.",
                        'pass_score': 70.0,
                        'is_required': True,
                        'status': 'PUBLISHED',
                        'source_type': 'FXEC_OFFICIAL',
                        'created_by': faculty_user
                    }
                )
                return module

            # =========================================================================
            # HELPER FUNCTION TO SEED ASSESSMENTS & QUESTIONS
            # =========================================================================
            def seed_assessment_with_questions(course, assessment_type, title, duration, pass_pct, questions_data):
                assess, _ = Assessment.objects.update_or_create(
                    course=course,
                    assessment_type=assessment_type,
                    defaults={
                        'title': title,
                        'version': 1,
                        'duration_minutes': duration,
                        'pass_percentage': pass_pct,
                        'max_attempts': 5 if assessment_type == 'PRE_ASSESSMENT' else 3,
                        'randomize_questions': True,
                        'randomize_options': True,
                        'is_published': True,
                        'camera_required': (assessment_type == 'FINAL_ASSESSMENT'),
                        'screen_share_required': (assessment_type == 'FINAL_ASSESSMENT'),
                        'fullscreen_required': (assessment_type == 'FINAL_ASSESSMENT'),
                        'face_detection_enabled': (assessment_type == 'FINAL_ASSESSMENT'),
                        'created_by': faculty_user
                    }
                )

                # Clear previous questions for this assessment to re-seed cleanly
                assess.questions.all().delete()

                for idx, q_info in enumerate(questions_data, start=1):
                    q = Question.objects.create(
                        assessment=assess,
                        course=course,
                        text=q_info['text'],
                        topic_tag=q_info['topic_tag'],
                        question_type='MCQ_SINGLE',
                        difficulty=q_info.get('difficulty', 'EASY'),
                        marks=1,
                        explanation=q_info['explanation'],
                        order=idx,
                        is_bank_question=True
                    )
                    for opt_idx, (opt_text, is_correct) in enumerate(q_info['options'], start=1):
                        QuestionOption.objects.create(
                            question=q,
                            text=opt_text,
                            is_correct=is_correct,
                            order=opt_idx
                        )
                return assess

            # =========================================================================
            # 1. COURSE: PYTHON FUNDAMENTALS (ID 6)
            # Add Pre-Assessment diagnostic questions
            # =========================================================================
            course_py_fund = Course.objects.filter(slug='python-fundamentals').first()
            if course_py_fund:
                self.stdout.write(f"Seeding Pre-Assessment for: {course_py_fund.title}")
                py_pre_questions = [
                    {
                        "text": "Which of the following creates a single-line comment in Python?",
                        "topic_tag": "python-intro",
                        "difficulty": "EASY",
                        "explanation": "In Python, the hash symbol (#) initiates a single-line comment.",
                        "options": [("# This is a comment", True), ("// This is a comment", False), ("/* Comment */", False), ("-- Comment", False)]
                    },
                    {
                        "text": "What is the primary role of the Python Virtual Machine (PVM)?",
                        "topic_tag": "python-intro",
                        "difficulty": "MEDIUM",
                        "explanation": "The PVM is the runtime engine of Python that executes compiled bytecode instructions.",
                        "options": [("Executes compiled Python bytecode (.pyc)", True), ("Transpiles Python code to C++", False), ("Performs static type checks at compile time", False), ("Acts as an operating system kernel", False)]
                    },
                    {
                        "text": "What is the return type of expression `type(5 / 2)` in Python 3?",
                        "topic_tag": "variables-datatypes",
                        "difficulty": "EASY",
                        "explanation": "In Python 3, true division (/) always returns a float.",
                        "options": [("<class 'float'>", True), ("<class 'int'>", False), ("<class 'double'>", False), ("<class 'number'>", False)]
                    },
                    {
                        "text": "Which built-in Python collection is ordered, mutable, and allows duplicate elements?",
                        "topic_tag": "variables-datatypes",
                        "difficulty": "EASY",
                        "explanation": "A list is an ordered, mutable sequence of elements in Python.",
                        "options": [("list", True), ("tuple", False), ("set", False), ("dict keys", False)]
                    },
                    {
                        "text": "What does the expression `10 // 3` evaluate to in Python?",
                        "topic_tag": "operators-conditions",
                        "difficulty": "EASY",
                        "explanation": "The double slash (//) is the floor division operator, returning 3 for 10 // 3.",
                        "options": [("3", True), ("3.333", False), ("3.0", False), ("1", False)]
                    },
                    {
                        "text": "How do you check if a key exists in a dictionary `d` in Python?",
                        "topic_tag": "operators-conditions",
                        "difficulty": "MEDIUM",
                        "explanation": "The `in` operator tests membership in sequences and dictionary keys.",
                        "options": [("key in d", True), ("d.has_key(key)", False), ("d.contains(key)", False), ("key.exists(d)", False)]
                    },
                    {
                        "text": "Which statement immediately aborts the current loop iteration and moves to the next one?",
                        "topic_tag": "loops-iterations",
                        "difficulty": "EASY",
                        "explanation": "`continue` skips the rest of the current loop body and proceeds to the next iteration.",
                        "options": [("continue", True), ("break", False), ("pass", False), ("skip", False)]
                    },
                    {
                        "text": "In a Python function definition, which syntax collects arbitrary keyword arguments into a dictionary?",
                        "topic_tag": "functions-scope",
                        "difficulty": "MEDIUM",
                        "explanation": "`**kwargs` gathers any unmatched keyword arguments into a standard Python dictionary.",
                        "options": [("**kwargs", True), ("*args", False), ("&kwargs", False), ("...kwargs", False)]
                    },
                    {
                        "text": "In Python object-oriented programming, what is the purpose of the `self` parameter in instance methods?",
                        "topic_tag": "oop-concepts",
                        "difficulty": "MEDIUM",
                        "explanation": "`self` represents the instance of the class through which attributes and methods are accessed.",
                        "options": [("Refers to the specific instance calling the method", True), ("Declares a static class variable", False), ("Imports the parent module", False), ("Allocates memory on the heap", False)]
                    },
                    {
                        "text": "Which block in a Python try-except construct executes regardless of whether an exception occurred or not?",
                        "topic_tag": "exceptions-file-io",
                        "difficulty": "EASY",
                        "explanation": "The `finally` block always executes, ensuring proper cleanup and resource closure.",
                        "options": [("finally", True), ("else", False), ("except", False), ("catch", False)]
                    }
                ]
                seed_assessment_with_questions(
                    course=course_py_fund,
                    assessment_type='PRE_ASSESSMENT',
                    title="Python Fundamentals Diagnostic Pre-Assessment",
                    duration=20,
                    pass_pct=70.0,
                    questions_data=py_pre_questions
                )

            # =========================================================================
            # 2. COURSE: PYTHON FOR DATA ANALYSIS (ID 7)
            # =========================================================================
            course_py_data = Course.objects.filter(slug='python-data-analysis').first()
            if course_py_data:
                self.stdout.write(f"Seeding Modules, Materials & Assessments for: {course_py_data.title}")
                py_data_modules = [
                    (
                        1,
                        "NumPy Fundamentals & Array Operations",
                        "numpy-fundamentals",
                        "Multi-dimensional ndarrays, vectorized arithmetic, broadcasting rules, and mathematical functions.",
                        35,
                        "NumPy Arrays & Vectorized Math Guide",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                        {
                            "topic": "NumPy Arrays & Vectorization",
                            "introduction": "NumPy (Numerical Python) is the foundational library for scientific and data analytics computing in Python. It provides fast C-implemented contiguous memory arrays.",
                            "concept_explanation": "A NumPy ndarray is a homogeneous, multidimensional container. Unlike Python lists, ndarrays support element-wise operations without explicit loops, leveraging SIMD CPU vectorization.",
                            "key_points": [
                                "Homogeneous memory: all elements in an ndarray have identical data types.",
                                "Vectorization replaces slow Python for-loops with fast C-level loops.",
                                "Broadcasting describes how NumPy treats arrays with different shapes during arithmetic operations.",
                                "Slicing an ndarray creates a view, not a copy; modifications alter the original array."
                            ],
                            "syntax": "import numpy as np\narr = np.array([1, 2, 3, 4], dtype=np.float64)\nprint(arr * 2)  # [2. 4. 6. 8.]\nprint(arr.mean(), arr.shape)",
                            "examples": [
                                {
                                    "title": "Creating 2D Array and Matrix Multiplication",
                                    "code": "import numpy as np\nA = np.array([[1, 2], [3, 4]])\nB = np.array([[5, 6], [7, 8]])\nproduct = np.dot(A, B)\nprint('Matrix Product:\\n', product)",
                                    "output": "Matrix Product:\n [[19 22]\n [43 50]]",
                                    "explanation": "np.dot or the @ operator performs linear algebra matrix multiplication."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "arr_copy = arr[:2] alters original array when modified",
                                    "correct": "arr_copy = arr[:2].copy()",
                                    "reason": "Standard NumPy slicing returns a view of the original memory buffer."
                                }
                            ],
                            "important_terms": [
                                {"term": "ndarray", "definition": "N-dimensional homogeneous array class in NumPy."},
                                {"term": "Broadcasting", "definition": "Mechanism allowing NumPy to work with arrays of different shapes for arithmetic operations."}
                            ],
                            "quick_revision": ["Use np.zeros(), np.ones(), np.arange(), np.linspace() for array creation.", "Use arr.shape, arr.ndim, arr.dtype to inspect dimensionality."],
                            "practice_questions": [
                                {"question": "What is the result of np.array([1, 2, 3]) + 5?", "answer": "array([6, 7, 8])", "explanation": "The scalar 5 is broadcast across all array elements."}
                            ]
                        },
                        "materials/python_data_analysis_handbook.pdf",
                        "NumPy Array Operations Concept Check",
                        [
                            {"id": 1, "question": "What happens when you slice a NumPy array (e.g., sub = arr[1:3]) and modify sub[0]?", "options": ["The original array is also modified (view semantics)", "Only the slice is modified (copy semantics)", "Raises a ReadOnlyError", "Creates a new tuple"], "correct_option": "The original array is also modified (view semantics)"},
                            {"id": 2, "question": "Which NumPy method reshapes an array of 12 elements into 3 rows and 4 columns?", "options": ["arr.reshape(3, 4)", "arr.resize_view(3, 4)", "arr.shape = (4, 3)", "np.transpose(arr, 3, 4)"], "correct_option": "arr.reshape(3, 4)"}
                        ]
                    ),
                    (
                        2,
                        "Pandas Series & DataFrames Processing",
                        "pandas-processing",
                        "Tabular data structures, label-based indexing (.loc/.iloc), column manipulations, and reading external CSV files.",
                        40,
                        "Pandas DataFrames & Series Deep Dive",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                        {
                            "topic": "Pandas Data Structures",
                            "introduction": "Pandas is the premier open-source data manipulation library providing labelled DataFrame and Series structures built on top of NumPy.",
                            "concept_explanation": "A Series is a one-dimensional labeled array. A DataFrame is a two-dimensional tabular data structure consisting of aligned rows and columns. Indexing with .loc uses labels, while .iloc uses integer positions.",
                            "key_points": [
                                "DataFrame columns are individual Series objects.",
                                ".loc[row_label, col_label] enables explicit label-based indexing.",
                                ".iloc[row_idx, col_idx] enables integer offset indexing.",
                                "read_csv() and to_csv() provide fast I/O for structured flat files."
                            ],
                            "syntax": "import pandas as pd\ndf = pd.DataFrame({'name': ['Alice', 'Bob'], 'score': [92, 85]})\nprint(df.loc[0, 'name'])  # Alice\nprint(df['score'].mean()) # 88.5",
                            "examples": [
                                {
                                    "title": "Filtering Data with Boolean Indexing",
                                    "code": "import pandas as pd\ndf = pd.DataFrame({'dept': ['CSE', 'IT', 'CSE'], 'gpa': [8.5, 7.9, 9.1]})\ntop_cse = df[(df['dept'] == 'CSE') & (df['gpa'] > 8.0)]\nprint(top_cse)",
                                    "output": "  dept  gpa\n0  CSE  8.5\n2  CSE  9.1",
                                    "explanation": "Bitwise & operator filters rows where both conditions are True."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Using `and` instead of `&` for boolean Series filtering",
                                    "correct": "df[(df['age'] > 18) & (df['score'] >= 50)]",
                                    "reason": "Python's `and` evaluates truthiness of the entire object; `&` performs element-wise logical AND."
                                }
                            ],
                            "important_terms": [
                                {"term": "Series", "definition": "1D labeled homogeneous array in Pandas."},
                                {"term": "DataFrame", "definition": "2D tabular mutable dataset with labelled axes."}
                            ],
                            "quick_revision": ["df.head(n) views first n rows.", "df.info() summarizes types and non-null counts."],
                            "practice_questions": [
                                {"question": "What is the difference between df.loc[0] and df.iloc[0]?", "answer": ".loc searches for index label 0; .iloc retrieves the very first row position.", "explanation": ".loc is label-based, .iloc is integer position-based."}
                            ]
                        },
                        "materials/python_data_analysis_handbook.pdf",
                        "Pandas Indexing & Filtering Practice",
                        [
                            {"id": 1, "question": "Which indexing accessor in Pandas is strictly based on integer zero-indexed positions?", "options": [".iloc", ".loc", ".ix", ".at_label"], "correct_option": ".iloc"},
                            {"id": 2, "question": "How do you add a new column 'status' with default value 'ACTIVE' to a DataFrame df?", "options": ["df['status'] = 'ACTIVE'", "df.add_col('status', 'ACTIVE')", "df.insert_column('status', 'ACTIVE')", "df.columns.append('status')"], "correct_option": "df['status'] = 'ACTIVE'"}
                        ]
                    ),
                    (
                        3,
                        "Data Cleaning, Missing Values & Filtering",
                        "data-cleaning",
                        "Detecting NaN values, imputation strategies (mean, median, mode), deduplication, and type casting.",
                        35,
                        "Real-world Data Cleaning Strategies",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
                        {
                            "topic": "Data Cleaning & Preprocessing",
                            "introduction": "Garbage in, garbage out. High-quality data cleaning transforms raw, corrupted, or incomplete observations into validated inputs ready for analysis.",
                            "concept_explanation": "Pandas marks missing data as np.nan or pd.NA. Functions like isna(), dropna(), and fillna() detect, remove, or impute missing entries respectively.",
                            "key_points": [
                                "df.isna().sum() reveals count of missing values per column.",
                                "dropna(axis=0) drops rows; dropna(axis=1) drops columns.",
                                "fillna(df['col'].median()) is preferred over mean for skewed distributions.",
                                "drop_duplicates(subset=['id']) eliminates redundant records."
                            ],
                            "syntax": "df.isna().sum()\ndf['age'] = df['age'].fillna(df['age'].median())\ndf = df.drop_duplicates()\ndf['date'] = pd.to_datetime(df['date'])",
                            "examples": [
                                {
                                    "title": "Imputing Missing Numeric Values with Column Mean",
                                    "code": "import pandas as pd, numpy as np\ndf = pd.DataFrame({'val': [10, np.nan, 30]})\ndf['val'] = df['val'].fillna(df['val'].mean())\nprint(df['val'].tolist())",
                                    "output": "[10.0, 20.0, 30.0]",
                                    "explanation": "np.nan was replaced by (10 + 30) / 2 = 20.0."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "df.dropna() without reassignment or inplace=True leaves df unchanged",
                                    "correct": "df = df.dropna()",
                                    "reason": "Most Pandas transformations return new DataFrames rather than mutating in place."
                                }
                            ],
                            "important_terms": [
                                {"term": "Imputation", "definition": "The process of replacing missing data with substituted statistical estimates."},
                                {"term": "NaN", "definition": "Not a Number; IEEE 754 floating point representation of missing values."}
                            ],
                            "quick_revision": ["Use df.dropna(thresh=k) to keep rows with at least k non-null values.", "Use .astype() to cast columns to integers or categories."],
                            "practice_questions": [
                                {"question": "What is the return type of df.isna()?", "answer": "A DataFrame of boolean values (True where missing).", "explanation": "Each cell is tested for nullity."}
                            ]
                        },
                        "materials/python_data_analysis_handbook.pdf",
                        "Data Cleaning & Imputation Practice",
                        [
                            {"id": 1, "question": "Which method removes duplicate rows based only on the 'student_id' column?", "options": ["df.drop_duplicates(subset=['student_id'])", "df.deduplicate('student_id')", "df.unique('student_id')", "df.drop_repeats(by='student_id')"], "correct_option": "df.drop_duplicates(subset=['student_id'])"},
                            {"id": 2, "question": "Which imputation strategy is most resistant to extreme statistical outliers?", "options": ["Median imputation", "Mean imputation", "Maximum value fill", "Zero fill"], "correct_option": "Median imputation"}
                        ]
                    ),
                    (
                        4,
                        "Data Visualization with Matplotlib & Seaborn",
                        "data-visualization",
                        "Line charts, scatter plots, histograms, heatmaps, aesthetic customization, and figure exports.",
                        35,
                        "Statistical Visualization with Matplotlib and Seaborn",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
                        {
                            "topic": "Data Visualization",
                            "introduction": "Visualization transforms abstract tabular data into intuitive graphical stories. Matplotlib provides foundational low-level plotting while Seaborn offers high-level statistical themes.",
                            "concept_explanation": "Matplotlib uses an object-oriented Figure and Axes hierarchy. Seaborn automatically computes statistics, error intervals, and aesthetic color palettes for relational and categorical data.",
                            "key_points": [
                                "plt.subplots() creates a Figure container and one or more Axes objects.",
                                "Histograms display frequency distribution of continuous features.",
                                "Scatter plots highlight correlation and cluster patterns between two continuous variables.",
                                "Heatmaps (sns.heatmap) visualize 2D correlation matrices."
                            ],
                            "syntax": "import matplotlib.pyplot as plt\nimport seaborn as sns\nfig, ax = plt.subplots(figsize=(8, 5))\nsns.histplot(df['score'], kde=True, ax=ax)\nax.set_title('Score Distribution')\nplt.tight_layout()",
                            "examples": [
                                {
                                    "title": "Plotting Correlation Heatmap",
                                    "code": "import seaborn as sns, matplotlib.pyplot as plt\ncorr = df.corr(numeric_only=True)\nsns.heatmap(corr, annot=True, cmap='coolwarm')\nplt.title('Feature Correlation Matrix')",
                                    "output": "Displays annotated color-coded grid of Pearson correlation coefficients.",
                                    "explanation": "annot=True prints values inside each grid tile."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Calling plt.plot() without plt.show() or saving the figure",
                                    "correct": "plt.savefig('chart.png') or plt.show()",
                                    "reason": "Plot commands populate the buffer; display or save commands are required to render."
                                }
                            ],
                            "important_terms": [
                                {"term": "Figure", "definition": "Top-level container holding all plot elements and subplots."},
                                {"term": "Axes", "definition": "The coordinate plane containing data points, axes lines, and labels."}
                            ],
                            "quick_revision": ["sns.boxplot() reveals median and outlier quartiles.", "plt.tight_layout() prevents overlapping axis labels."],
                            "practice_questions": [
                                {"question": "Which plot is ideal to compare the distributions of several categories?", "answer": "Box plot or violin plot.", "explanation": "Shows median, interquartile range, and outliers across groups."}
                            ]
                        },
                        "materials/python_data_analysis_handbook.pdf",
                        "Visualization Techniques Practice",
                        [
                            {"id": 1, "question": "Which Seaborn function displays a correlation matrix as an annotated color grid?", "options": ["sns.heatmap()", "sns.matrixplot()", "sns.gridplot()", "sns.corrplot()"], "correct_option": "sns.heatmap()"},
                            {"id": 2, "question": "What is the primary role of a box plot (sns.boxplot)?", "options": ["Visualizing quartiles, median, and identifying outliers", "Plotting 3D surface trajectories", "Generating pie chart slices", "Plotting linear regression residuals only"], "correct_option": "Visualizing quartiles, median, and identifying outliers"}
                        ]
                    ),
                    (
                        5,
                        "Exploratory Data Analysis & GroupBy Aggregations",
                        "eda-aggregation",
                        "Split-apply-combine paradigm with groupby, pivot tables, cross-tabulations, and correlation analysis.",
                        40,
                        "Exploratory Data Analysis & Statistical Aggregation",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4",
                        {
                            "topic": "EDA & Aggregation Strategies",
                            "introduction": "Exploratory Data Analysis (EDA) leverages split-apply-combine aggregations to discover patterns, compute group summaries, and validate assumptions.",
                            "concept_explanation": "df.groupby('category') splits the dataset by category, applies an aggregation function (mean, sum, count), and combines results into a concise summary.",
                            "key_points": [
                                "df.groupby('dept')['salary'].agg(['mean', 'median', 'std']) executes multiple aggregates.",
                                "pivot_table() reshapes data with index rows and column dimensions.",
                                "df.describe() computes count, mean, standard deviation, and percentiles.",
                                "Correlation matrices quantify linear relationships between numerical columns."
                            ],
                            "syntax": "df.groupby('dept')['salary'].mean()\ndf.pivot_table(values='sales', index='region', columns='year', aggfunc='sum')",
                            "examples": [
                                {
                                    "title": "Computing Multi-Metric Departmental Summary",
                                    "code": "summary = df.groupby('department').agg({'gpa': 'mean', 'attendance': 'median'})\nprint(summary)",
                                    "output": "            gpa  attendance\ndepartment                  \nAIDS        8.8        94.0\nCSE         8.4        91.5\nIT          8.1        90.0",
                                    "explanation": "Calculates mean GPA and median attendance per academic department."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Forgetting reset_index() after groupby when needing standard DataFrame columns",
                                    "correct": "df.groupby('dept')['salary'].mean().reset_index()",
                                    "reason": "Grouped operations place grouping keys into the DataFrame Index."
                                }
                            ],
                            "important_terms": [
                                {"term": "Split-Apply-Combine", "definition": "Data analysis pattern of breaking data into subsets, executing operations, and assembling results."},
                                {"term": "Pivot Table", "definition": "Multi-dimensional summary table aggregating values across intersecting dimensions."}
                            ],
                            "quick_revision": ["Use .value_counts() for categorical distributions.", "Use .corr() for Pearson correlation coefficients."],
                            "practice_questions": [
                                {"question": "What does df.groupby('type').size() return?", "answer": "The count of rows in each group.", "explanation": ".size() counts all rows including NaNs, while .count() excludes NaNs."}
                            ]
                        },
                        "materials/python_data_analysis_handbook.pdf",
                        "GroupBy & Aggregation Mastery Check",
                        [
                            {"id": 1, "question": "What design pattern does df.groupby() implement?", "options": ["Split-Apply-Combine", "Model-View-Controller", "Singleton Factory", "Observer-Subscriber"], "correct_option": "Split-Apply-Combine"},
                            {"id": 2, "question": "How do you calculate both mean and standard deviation of 'sales' grouped by 'region'?", "options": ["df.groupby('region')['sales'].agg(['mean', 'std'])", "df.groupby('region')['sales'].mean_and_std()", "df.aggregate('region', sales=['mean', 'std'])", "df.calc_metrics('region', 'sales')"], "correct_option": "df.groupby('region')['sales'].agg(['mean', 'std'])"}
                        ]
                    )
                ]

                for mod_spec in py_data_modules:
                    seed_module_content(course_py_data, *mod_spec)

                # Seed Pre-Assessment & Final Assessment
                py_data_pre_q = [
                    {"text": "Which NumPy attribute reveals the tuple of array dimensions?", "topic_tag": "numpy-fundamentals", "difficulty": "EASY", "explanation": "The .shape attribute returns a tuple of integers representing dimensions.", "options": [("arr.shape", True), ("arr.size", False), ("arr.ndim", False), ("arr.dimension", False)]},
                    {"text": "What is broadcasting in NumPy?", "topic_tag": "numpy-fundamentals", "difficulty": "MEDIUM", "explanation": "Broadcasting describes how NumPy treats arrays of different shapes during arithmetic operations.", "options": [("Rules for arithmetic operations between different array shapes", True), ("Sending arrays over network sockets", False), ("Exporting arrays to binary storage", False), ("Converting floating point arrays to complex numbers", False)]},
                    {"text": "Which Pandas data structure represents a one-dimensional labeled array?", "topic_tag": "pandas-processing", "difficulty": "EASY", "explanation": "A Series is a one-dimensional labeled array capable of holding any data type.", "options": [("Series", True), ("DataFrame", False), ("Panel", False), ("Index", False)]},
                    {"text": "How do you select rows in DataFrame `df` where column 'age' is greater than 25?", "topic_tag": "pandas-processing", "difficulty": "EASY", "explanation": "Boolean indexing syntax df[df['age'] > 25] filters matching records.", "options": [("df[df['age'] > 25]", True), ("df.filter('age > 25')", False), ("df.where(age > 25)", False), ("df.select('age' > 25)", False)]},
                    {"text": "What does `df.isna().sum()` calculate in Pandas?", "topic_tag": "data-cleaning", "difficulty": "EASY", "explanation": "It sums boolean missing indicators to give the count of null values per column.", "options": [("The total number of missing values per column", True), ("The sum of all non-null numbers in the dataset", False), ("The total count of zero values in the dataset", False), ("The count of duplicated records", False)]},
                    {"text": "Which Pandas method removes rows containing any null values from a DataFrame?", "topic_tag": "data-cleaning", "difficulty": "EASY", "explanation": "df.dropna() drops all rows with at least one missing value by default.", "options": [("df.dropna()", True), ("df.remove_nulls()", False), ("df.clean_na()", False), ("df.filter_na()", False)]},
                    {"text": "Which Matplotlib function creates a figure and a set of subplots?", "topic_tag": "data-visualization", "difficulty": "EASY", "explanation": "plt.subplots() conveniently initializes both Figure and Axes objects.", "options": [("plt.subplots()", True), ("plt.make_plot()", False), ("plt.figure_set()", False), ("plt.axes_grid()", False)]},
                    {"text": "Which chart type is best suited to display the distribution of a single numerical variable?", "topic_tag": "data-visualization", "difficulty": "EASY", "explanation": "Histograms show the frequency distribution of a continuous variable.", "options": [("Histogram", True), ("Scatter plot", False), ("Pie chart", False), ("Line chart", False)]},
                    {"text": "In Pandas groupby, what is the default behavior regarding missing (NaN) group keys?", "topic_tag": "eda-aggregation", "difficulty": "MEDIUM", "explanation": "Pandas groupby historically excludes NaN keys unless dropna=False is specified.", "options": [("They are excluded from groups by default", True), ("They are converted to string 'NaN'", False), ("They raise a GroupByError", False), ("They are imputed with the mean", False)]},
                    {"text": "Which method generates descriptive statistics including mean, std, and quartiles for numeric columns?", "topic_tag": "eda-aggregation", "difficulty": "EASY", "explanation": "df.describe() summarizes the central tendency, dispersion and shape of a dataset.", "options": [("df.describe()", True), ("df.summary()", False), ("df.stats()", False), ("df.info()", False)]}
                ]
                seed_assessment_with_questions(
                    course=course_py_data,
                    assessment_type='PRE_ASSESSMENT',
                    title="Python Data Analysis Diagnostic Pre-Assessment",
                    duration=20,
                    pass_pct=70.0,
                    questions_data=py_data_pre_q
                )

                py_data_final_q = [
                    {"text": "If array A has shape (3, 1) and array B has shape (1, 4), what is the shape of (A + B)?", "topic_tag": "numpy-fundamentals", "difficulty": "HARD", "explanation": "According to broadcasting rules, dimensions of size 1 stretch to match the other array, resulting in shape (3, 4).", "options": [("(3, 4)", True), ("(3, 1)", False), ("(1, 4)", False), ("Raises ValueError", False)]},
                    {"text": "How do you calculate the dot product of two 2D NumPy matrices X and Y?", "topic_tag": "numpy-fundamentals", "difficulty": "MEDIUM", "explanation": "np.dot(X, Y) or X @ Y computes matrix multiplication.", "options": [("X @ Y or np.dot(X, Y)", True), ("X * Y", False), ("np.multiply(X, Y)", False), ("X.cross(Y)", False)]},
                    {"text": "What does df.iloc[0:2, 1:3] return in Pandas?", "topic_tag": "pandas-processing", "difficulty": "MEDIUM", "explanation": "It retrieves rows at index 0 and 1, and columns at index 1 and 2 by integer location.", "options": [("Rows 0 and 1, columns at integer positions 1 and 2", True), ("Rows 0 through 2, columns 1 through 3 including labels", False), ("All rows matching index label '0:2'", False), ("A single scalar value", False)]},
                    {"text": "How do you convert a string date column 'created_at' into datetime objects in Pandas?", "topic_tag": "pandas-processing", "difficulty": "EASY", "explanation": "pd.to_datetime() parses string timestamps into Pandas Timestamp objects.", "options": [("pd.to_datetime(df['created_at'])", True), ("df['created_at'].astype('datetime')", False), ("df['created_at'].parse_date()", False), ("pd.format_date(df['created_at'])", False)]},
                    {"text": "When imputing missing values in a heavily right-skewed salary column, which metric minimizes distortion?", "topic_tag": "data-cleaning", "difficulty": "MEDIUM", "explanation": "Median is robust to outliers, making it optimal for skewed data distributions.", "options": [("Median", True), ("Mean", False), ("Mode", False), ("Standard deviation", False)]},
                    {"text": "What is the purpose of `df.drop_duplicates(subset=['email'], keep='last')`?", "topic_tag": "data-cleaning", "difficulty": "MEDIUM", "explanation": "It removes earlier duplicate rows sharing the same 'email', retaining only the final occurrence.", "options": [("Retains only the last duplicate entry and removes prior occurrences", True), ("Deletes all duplicate rows including the last", False), ("Sorts emails in descending order", False), ("Removes null email entries", False)]},
                    {"text": "Which Seaborn visualization displays a five-number summary (minimum, Q1, median, Q3, maximum)?", "topic_tag": "data-visualization", "difficulty": "EASY", "explanation": "A box plot (sns.boxplot) visualizes quartiles and highlights outliers.", "options": [("sns.boxplot()", True), ("sns.barplot()", False), ("sns.kdeplot()", False), ("sns.lineplot()", False)]},
                    {"text": "How do you annotate correlation numbers inside the tiles of a Seaborn heatmap?", "topic_tag": "data-visualization", "difficulty": "MEDIUM", "explanation": "Passing annot=True displays the numeric values inside each heatmap cell.", "options": [("sns.heatmap(data, annot=True)", True), ("sns.heatmap(data, show_text=True)", False), ("sns.heatmap(data, labels=True)", False), ("sns.heatmap(data, with_numbers=True)", False)]},
                    {"text": "What is the result of `df.groupby('dept')['rating'].agg(['mean', 'max'])`?", "topic_tag": "eda-aggregation", "difficulty": "MEDIUM", "explanation": "It computes both the mean and maximum rating grouped by each department.", "options": [("A DataFrame with columns 'mean' and 'max' indexed by department", True), ("A single number representing the overall maximum", False), ("A 1D Series containing both values joined by comma", False), ("An error because multiple aggregates require separate calls", False)]},
                    {"text": "Which Pandas function reshapes data like an Excel pivot table, computing aggregations across two dimensions?", "topic_tag": "eda-aggregation", "difficulty": "MEDIUM", "explanation": "df.pivot_table() computes multi-dimensional aggregations over specified rows and columns.", "options": [("df.pivot_table()", True), ("df.unstack_all()", False), ("df.transpose_grid()", False), ("df.crosstab_calc()", False)]}
                ]
                seed_assessment_with_questions(
                    course=course_py_data,
                    assessment_type='FINAL_ASSESSMENT',
                    title="Python for Data Analysis Certification Exam",
                    duration=30,
                    pass_pct=70.0,
                    questions_data=py_data_final_q
                )

            # =========================================================================
            # 3. COURSE: JAVA FUNDAMENTALS (ID 8)
            # =========================================================================
            course_java_fund = Course.objects.filter(slug='java-fundamentals').first()
            if course_java_fund:
                self.stdout.write(f"Seeding Modules, Materials & Assessments for: {course_java_fund.title}")
                java_fund_modules = [
                    (
                        1,
                        "Java Architecture & Environment Setup",
                        "java-intro",
                        "JDK, JRE, JVM internals, bytecode verification, JIT compilation, and executing your first class.",
                        35,
                        "Java Virtual Machine Architecture Explained",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4",
                        {
                            "topic": "JVM Architecture & Environment",
                            "introduction": "Java is a class-based, object-oriented programming language designed for portability ('Write Once, Run Anywhere').",
                            "concept_explanation": "Java source (.java) is compiled by javac into platform-neutral bytecode (.class). The JVM loads, verifies, and executes bytecode using interpreter and JIT compilation to native machine instructions.",
                            "key_points": [
                                "JDK includes tools to compile and run; JRE contains the runtime environment; JVM executes bytecode.",
                                "Garbage collection automatically reclaims unreferenced heap memory.",
                                "public static void main(String[] args) is the required entry point for Java applications.",
                                "Bytecode verification protects system memory from illegal pointers and stack overflows."
                            ],
                            "syntax": "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, FXEC SkillHub!\");\n    }\n}",
                            "examples": [
                                {
                                    "title": "Basic Class Definition and Execution",
                                    "code": "public class Welcome {\n    public static void main(String[] args) {\n        String institution = \"FXEC\";\n        System.out.println(\"Welcome to \" + institution);\n    }\n}",
                                    "output": "Welcome to FXEC",
                                    "explanation": "Standard console output using System.out.println."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Mismatched file name and public class name",
                                    "correct": "File Welcome.java must contain public class Welcome",
                                    "reason": "Java enforces identical naming between public classes and their source files."
                                }
                            ],
                            "important_terms": [
                                {"term": "JVM", "definition": "Java Virtual Machine that executes compiled bytecode."},
                                {"term": "JIT", "definition": "Just-In-Time compiler translating frequently executed bytecode to native machine code."}
                            ],
                            "quick_revision": ["Primitive types: byte, short, int, long, float, double, char, boolean.", "Garbage collection operates in generational heap segments (Young, Old)."],
                            "practice_questions": [
                                {"question": "What is the file extension of compiled Java code?", "answer": ".class", "explanation": "javac compiles .java source files into .class bytecode files."}
                            ]
                        },
                        "materials/java_fundamentals_handbook.pdf",
                        "Java Environment & Architecture Check",
                        [
                            {"id": 1, "question": "What does javac produce when it compiles a Java source file?", "options": [".class bytecode file", ".exe native executable", ".obj assembly file", ".jar compressed archive directly"], "correct_option": ".class bytecode file"},
                            {"id": 2, "question": "Which memory segment does the Java Garbage Collector manage?", "options": ["Heap memory", "Stack memory", "Program Counter register", "Native method stack"], "correct_option": "Heap memory"}
                        ]
                    ),
                    (
                        2,
                        "Data Types, Operators & Control Flow",
                        "java-control-flow",
                        "Primitive vs reference types, type casting, arithmetic/relational operators, if-else, switch, and loops.",
                        35,
                        "Java Types, Operators and Control Structures",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4",
                        {
                            "topic": "Java Control Flow & Data Types",
                            "introduction": "Java is statically typed. Every variable must have an explicitly declared type, checked at compile time.",
                            "concept_explanation": "Primitives store values directly in stack frames; Reference types store memory addresses pointing to objects on the heap. Control flow constructs (if, switch, for, while) direct program execution paths.",
                            "key_points": [
                                "Java has 8 primitive types: boolean, byte, char, short, int, long, float, double.",
                                "Widening casting (int to double) is automatic; narrowing casting requires explicit cast (int) 9.99.",
                                "Switch expressions support modern pattern matching and arrow syntax in modern Java.",
                                "Enhanced for-loop (for-each) iterates smoothly over arrays and Iterables."
                            ],
                            "syntax": "int score = 85;\nif (score >= 90) {\n    System.out.println(\"Grade A\");\n} else {\n    System.out.println(\"Passed\");\n}",
                            "examples": [
                                {
                                    "title": "Enhanced For-Loop over an Array",
                                    "code": "int[] numbers = {10, 20, 30};\nfor (int n : numbers) {\n    System.out.print(n + \" \");\n}",
                                    "output": "10 20 30 ",
                                    "explanation": "Iterates sequentially through all elements without maintaining an index."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Comparing Strings with `==` instead of `.equals()`",
                                    "correct": "str1.equals(str2)",
                                    "reason": "`==` checks reference identity (memory address); `.equals()` checks character content."
                                }
                            ],
                            "important_terms": [
                                {"term": "Primitive Type", "definition": "Basic data type storing raw values directly in memory."},
                                {"term": "Type Casting", "definition": "Converting a value from one data type to another."}
                            ],
                            "quick_revision": ["switch statements require break or arrow syntax to prevent fall-through.", "Array length is an immutable property: arr.length."],
                            "practice_questions": [
                                {"question": "What is the result of 5 / 2 in Java?", "answer": "2 (integer division truncates decimal part)", "explanation": "Both operands are integers, yielding integer quotient 2."}
                            ]
                        },
                        "materials/java_fundamentals_handbook.pdf",
                        "Control Flow & Type Conversion Check",
                        [
                            {"id": 1, "question": "What is the correct way to test if two String objects contain identical text in Java?", "options": ["s1.equals(s2)", "s1 == s2", "s1 === s2", "s1.compareTo(s2) == -1"], "correct_option": "s1.equals(s2)"},
                            {"id": 2, "question": "What is the output of `(int) 7.89` in Java?", "options": ["7", "8", "7.89", "Compilation error"], "correct_option": "7"}
                        ]
                    ),
                    (
                        3,
                        "Object-Oriented Programming: Classes & Objects",
                        "java-oop-classes",
                        "Encapsulation, constructors, 'this' keyword, access modifiers (private, protected, public), and method overloading.",
                        40,
                        "Mastering Classes and Encapsulation in Java",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                        {
                            "topic": "Java Classes & Encapsulation",
                            "introduction": "Encapsulation bundles data (fields) and methods operating on that data within a single class unit, preventing unauthorized external interference.",
                            "concept_explanation": "Classes declare member variables and methods. The `new` keyword instantiates objects on the heap and invokes constructors. Access modifiers enforce data hiding.",
                            "key_points": [
                                "Access modifiers: private (class only), default (package-private), protected (package + subclasses), public (everywhere).",
                                "Constructors initialize instance state and do not specify a return type.",
                                "The `this` keyword resolves naming ambiguities between parameters and instance variables.",
                                "Method overloading defines multiple methods with identical names but differing parameter signatures."
                            ],
                            "syntax": "public class Student {\n    private String name;\n    public Student(String name) { this.name = name; }\n    public String getName() { return this.name; }\n}",
                            "examples": [
                                {
                                    "title": "Encapsulated BankAccount Class",
                                    "code": "public class Account {\n    private double balance;\n    public void deposit(double amt) {\n        if (amt > 0) balance += amt;\n    }\n    public double getBalance() { return balance; }\n}",
                                    "output": "Guarantees balance cannot be set to arbitrary negative values externally.",
                                    "explanation": "Validation logic inside setter/deposit method enforces domain rules."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Adding a void return type to a constructor: public void Student()",
                                    "correct": "public Student()",
                                    "reason": "Adding a return type turns the constructor into a regular instance method."
                                }
                            ],
                            "important_terms": [
                                {"term": "Encapsulation", "definition": "Hiding internal object representation and requiring all interaction through methods."},
                                {"term": "Constructor", "definition": "Special method invoked when an object is instantiated."}
                            ],
                            "quick_revision": ["If no constructor is defined, Java provides a default no-argument constructor.", "Static members belong to the class rather than instances."],
                            "practice_questions": [
                                {"question": "Can a constructor be declared private?", "answer": "Yes (commonly used in Singleton pattern or utility classes).", "explanation": "Prevents instantiation from outside the class."}
                            ]
                        },
                        "materials/java_fundamentals_handbook.pdf",
                        "OOP Classes & Encapsulation Practice",
                        [
                            {"id": 1, "question": "Which access modifier restricts access strictly to within the same class?", "options": ["private", "protected", "default (package-private)", "public"], "correct_option": "private"},
                            {"id": 2, "question": "What defines method overloading in Java?", "options": ["Same method name with different parameter types or count", "Same method name and parameters in subclass", "Changing only the return type of a method", "Adding static keyword to an existing method"], "correct_option": "Same method name with different parameter types or count"}
                        ]
                    ),
                    (
                        4,
                        "Inheritance, Polymorphism & Interfaces",
                        "java-inheritance-interfaces",
                        "Class extension ('extends'), method overriding ('@Override'), 'super' keyword, abstract classes, and interface contracts.",
                        40,
                        "Inheritance, Polymorphism and Interfaces in Java",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                        {
                            "topic": "Polymorphism & Interface Contracts",
                            "introduction": "Inheritance promotes code reuse across hierarchical abstractions. Polymorphism allows subclasses to define customized behavior while sharing a common interface.",
                            "concept_explanation": "Java supports single class inheritance with `extends` and multiple interface inheritance with `implements`. Subclasses override methods using @Override. Polymorphism executes the concrete runtime method via dynamic dispatch.",
                            "key_points": [
                                "Java does not support multiple class inheritance to prevent the Diamond Problem.",
                                "Interfaces define contracts that implementing classes must fulfill.",
                                "The `super` keyword invokes superclass constructors and overridden methods.",
                                "An abstract class cannot be instantiated and may contain abstract and concrete methods."
                            ],
                            "syntax": "public interface Playable {\n    void play();\n}\npublic class Video implements Playable {\n    @Override\n    public void play() { System.out.println(\"Playing video...\"); }\n}",
                            "examples": [
                                {
                                    "title": "Polymorphic Method Execution",
                                    "code": "abstract class Animal { abstract void speak(); }\nclass Dog extends Animal { void speak() { System.out.println(\"Woof\"); } }\nAnimal a = new Dog();\na.speak();",
                                    "output": "Woof",
                                    "explanation": "Dynamic method dispatch invokes Dog's speak method at runtime."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Trying to instantiate an abstract class or interface: new Animal()",
                                    "correct": "Instantiate a concrete subclass: new Dog()",
                                    "reason": "Abstract classes and interfaces are incomplete blueprints."
                                }
                            ],
                            "important_terms": [
                                {"term": "Dynamic Dispatch", "definition": "The mechanism by which a call to an overridden method is resolved at runtime."},
                                {"term": "Interface", "definition": "Abstract reference type in Java that specifies method signatures implementing classes must define."}
                            ],
                            "quick_revision": ["Use final on a class to prevent inheritance.", "Use final on a method to prevent overriding."],
                            "practice_questions": [
                                {"question": "Can a Java class implement multiple interfaces?", "answer": "Yes, classes can implement as many interfaces as required.", "explanation": "Java allows multiple interface implementation: class C implements A, B."}
                            ]
                        },
                        "materials/java_fundamentals_handbook.pdf",
                        "Polymorphism & Interface Practice",
                        [
                            {"id": 1, "question": "Which keyword prevents a Java class from being extended by any subclass?", "options": ["final", "static", "abstract", "const"], "correct_option": "final"},
                            {"id": 2, "question": "Can a single Java class implement multiple interfaces?", "options": ["Yes, using comma separation after implements", "No, Java permits only single interface implementation", "Only if all interfaces are marked abstract", "Only in Java 8 and below"], "correct_option": "Yes, using comma separation after implements"}
                        ]
                    ),
                    (
                        5,
                        "Exception Handling & Java Collections Framework",
                        "java-exceptions-collections",
                        "Try-catch-finally, checked vs unchecked exceptions, custom exceptions, ArrayList, HashMap, HashSet, and Iterators.",
                        45,
                        "Exception Safety & Java Collections Framework",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WhatCarCanYouGetForAGrand.mp4",
                        {
                            "topic": "Exception Handling & Collections",
                            "introduction": "Enterprise software must gracefully handle runtime anomalies and organize dynamic data collections in memory.",
                            "concept_explanation": "Exceptions separate error-handling code from normal logic. Checked exceptions (IOException, SQLException) are verified at compile time. The Collections Framework (List, Set, Map) provides pre-built, optimized data structures.",
                            "key_points": [
                                "try-catch-finally catches exceptions and guarantees cleanup execution.",
                                "try-with-resources automatically closes AutoCloseable streams and connections.",
                                "ArrayList provides fast index-based access (O(1)); LinkedList optimizes insertions.",
                                "HashMap stores key-value pairs using hash tables for O(1) average retrieval."
                            ],
                            "syntax": "List<String> names = new ArrayList<>();\nnames.add(\"Priya\");\nMap<String, Integer> map = new HashMap<>();\nmap.put(\"CSE\", 120);\nSystem.out.println(map.get(\"CSE\"));",
                            "examples": [
                                {
                                    "title": "Exception Handling with Try-With-Resources",
                                    "code": "try (BufferedReader br = new BufferedReader(new FileReader(\"data.txt\"))) {\n    System.out.println(br.readLine());\n} catch (IOException e) {\n    System.err.println(\"Failed to read file: \" + e.getMessage());\n}",
                                    "output": "Safely reads file or reports exception without manual br.close() in finally.",
                                    "explanation": "AutoCloseable resources are guaranteed to close upon try block exit."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Using a raw collection without generics: List list = new ArrayList()",
                                    "correct": "List<String> list = new ArrayList<>()",
                                    "reason": "Generics provide compile-time type safety and eliminate runtime ClassCastException."
                                }
                            ],
                            "important_terms": [
                                {"term": "Checked Exception", "definition": "Exception checked at compile-time that must be caught or declared in throws clause."},
                                {"term": "HashMap", "definition": "Hash table based implementation of the Map interface."}
                            ],
                            "quick_revision": ["Set does not allow duplicate elements.", "Comparable and Comparator interfaces define sorting orders."],
                            "practice_questions": [
                                {"question": "What is the average time complexity of HashMap.get(key)?", "answer": "O(1) constant time.", "explanation": "Calculates bucket index from key.hashCode()."}
                            ]
                        },
                        "materials/java_fundamentals_handbook.pdf",
                        "Collections & Exceptions Practice",
                        [
                            {"id": 1, "question": "Which of the following is an unchecked (Runtime) exception in Java?", "options": ["NullPointerException", "IOException", "SQLException", "ClassNotFoundException"], "correct_option": "NullPointerException"},
                            {"id": 2, "question": "Which Collection implementation prevents duplicate elements and does not guarantee insertion order?", "options": ["HashSet", "ArrayList", "LinkedList", "Vector"], "correct_option": "HashSet"}
                        ]
                    )
                ]

                for mod_spec in java_fund_modules:
                    seed_module_content(course_java_fund, *mod_spec)

                # Pre-Assessment & Final Assessment
                java_fund_pre_q = [
                    {"text": "What is the primary role of the Java Virtual Machine (JVM)?", "topic_tag": "java-intro", "difficulty": "EASY", "explanation": "The JVM executes compiled Java bytecode on the host operating system.", "options": [("Executes compiled bytecode (.class files)", True), ("Translates Java source directly to assembly", False), ("Acts as an IDE compiler plugin", False), ("Provides network routing protocols", False)]},
                    {"text": "Which command compiles a Java source file `App.java` from the command line?", "topic_tag": "java-intro", "difficulty": "EASY", "explanation": "javac is the official Java compiler command.", "options": [("javac App.java", True), ("java App.java", False), ("jvm compile App.java", False), ("run App.java", False)]},
                    {"text": "Which of the following is NOT a primitive data type in Java?", "topic_tag": "java-control-flow", "difficulty": "EASY", "explanation": "String is a class and reference type, whereas int, float, and boolean are primitives.", "options": [("String", True), ("int", False), ("boolean", False), ("double", False)]},
                    {"text": "What is the result of expression `15 % 4` in Java?", "topic_tag": "java-control-flow", "difficulty": "EASY", "explanation": "% is the modulo operator; 15 divided by 4 leaves remainder 3.", "options": [("3", True), ("3.75", False), ("3.0", False), ("0", False)]},
                    {"text": "Which access modifier gives a class member visibility only inside its own class?", "topic_tag": "java-oop-classes", "difficulty": "EASY", "explanation": "private members cannot be accessed outside the enclosing class.", "options": [("private", True), ("protected", False), ("public", False), ("package", False)]},
                    {"text": "What is the purpose of the `this` keyword in Java?", "topic_tag": "java-oop-classes", "difficulty": "MEDIUM", "explanation": "`this` refers to the current invoking instance of the class.", "options": [("Refers to the current class instance", True), ("Instantiates a new subclass", False), ("Imports static packages", False), ("Destroys an object from memory", False)]},
                    {"text": "Which keyword is used by a class to inherit from a superclass in Java?", "topic_tag": "java-inheritance-interfaces", "difficulty": "EASY", "explanation": "The `extends` keyword establishes class inheritance.", "options": [("extends", True), ("implements", False), ("inherits", False), ("derives", False)]},
                    {"text": "Can an abstract class in Java have concrete methods with bodies?", "topic_tag": "java-inheritance-interfaces", "difficulty": "MEDIUM", "explanation": "Yes, abstract classes can mix abstract and concrete methods.", "options": [("Yes, abstract classes can have both concrete and abstract methods", True), ("No, all methods in an abstract class must be abstract", False), ("Only if marked static", False), ("Only in private scope", False)]},
                    {"text": "Which Java keyword is used to explicitly throw an exception object?", "topic_tag": "java-exceptions-collections", "difficulty": "EASY", "explanation": "The `throw` keyword throws an exception instance (e.g. throw new IllegalArgumentException()).", "options": [("throw", True), ("throws", False), ("catch", False), ("raise", False)]},
                    {"text": "Which Collection interface allows ordered elements with duplicates and fast index retrieval?", "topic_tag": "java-exceptions-collections", "difficulty": "EASY", "explanation": "List implementations (such as ArrayList) allow duplicates and index-based access.", "options": [("List", True), ("Set", False), ("Map", False), ("Queue", False)]}
                ]
                seed_assessment_with_questions(
                    course=course_java_fund,
                    assessment_type='PRE_ASSESSMENT',
                    title="Java Fundamentals Diagnostic Pre-Assessment",
                    duration=20,
                    pass_pct=70.0,
                    questions_data=java_fund_pre_q
                )

                java_fund_final_q = [
                    {"text": "In the JVM, where are local variables allocated during method execution?", "topic_tag": "java-intro", "difficulty": "MEDIUM", "explanation": "Local variables and call frames reside on the thread Stack; objects reside on the Heap.", "options": [("Stack memory", True), ("Heap memory", False), ("Method Area", False), ("Garbage Collector space", False)]},
                    {"text": "What happens if a Java program exhausts all heap memory allocating objects?", "topic_tag": "java-intro", "difficulty": "MEDIUM", "explanation": "JVM throws OutOfMemoryError when heap space cannot satisfy object allocation.", "options": [("java.lang.OutOfMemoryError is thrown", True), ("StackOverflowError is thrown", False), ("The OS restarts the computer", False), ("Variables become null automatically", False)]},
                    {"text": "What is the output of `System.out.println(10 + 20 + \"Hello\");`?", "topic_tag": "java-control-flow", "difficulty": "HARD", "explanation": "Evaluation proceeds left to right: 10 + 20 yields 30, then 30 + 'Hello' yields string '30Hello'.", "options": [("30Hello", True), ("1020Hello", False), ("Hello30", False), ("Compilation error", False)]},
                    {"text": "How do you terminate the outer loop from inside a nested loop in Java?", "topic_tag": "java-control-flow", "difficulty": "MEDIUM", "explanation": "Labeled break statements (e.g. break outerLoop;) break out of designated enclosing loops.", "options": [("Using a labeled break statement", True), ("break 2;", False), ("exit(0);", False), ("return break;", False)]},
                    {"text": "Can constructor overloading exist within the same Java class?", "topic_tag": "java-oop-classes", "difficulty": "EASY", "explanation": "Yes, classes can provide multiple constructors differing in parameter count or types.", "options": [("Yes, by providing differing parameter signatures", True), ("No, Java permits exactly one constructor per class", False), ("Only if marked static", False), ("Only if marked with @Override", False)]},
                    {"text": "What is the effect of declaring a class variable `static` in Java?", "topic_tag": "java-oop-classes", "difficulty": "MEDIUM", "explanation": "A static variable is shared across all instances of the class rather than per object.", "options": [("A single copy is shared across all instances of the class", True), ("The variable becomes immutable and cannot be changed", False), ("The variable is stored on the stack", False), ("The variable cannot be accessed by static methods", False)]},
                    {"text": "Which Java keyword is used to access overridden methods or constructors of the parent class?", "topic_tag": "java-inheritance-interfaces", "difficulty": "EASY", "explanation": "`super` references the immediate superclass members and constructors.", "options": [("super", True), ("parent", False), ("base", False), ("this.parent", False)]},
                    {"text": "Can an interface in Java declare private helper methods?", "topic_tag": "java-inheritance-interfaces", "difficulty": "HARD", "explanation": "Starting in Java 9, interfaces can declare private helper methods for internal default method code reuse.", "options": [("Yes, starting in Java 9", True), ("No, interface methods must always be public", False), ("Only if marked abstract", False), ("Only in Java 7", False)]},
                    {"text": "What is the primary advantage of the try-with-resources statement in Java 7+?", "topic_tag": "java-exceptions-collections", "difficulty": "MEDIUM", "explanation": "It guarantees that all declared AutoCloseable resources are closed automatically when execution completes.", "options": [("Automatically closes AutoCloseable resources avoiding memory/handle leaks", True), ("Prevents all RuntimeExceptions from being thrown", False), ("Speeds up CPU execution by 50%", False), ("Permits catching multiple errors without catch blocks", False)]},
                    {"text": "Why is HashMap faster than TreeMap for general key-value retrieval?", "topic_tag": "java-exceptions-collections", "difficulty": "HARD", "explanation": "HashMap provides O(1) average lookup using hash buckets, while TreeMap provides O(log N) lookup using a Red-Black Tree.", "options": [("HashMap offers O(1) average complexity vs TreeMap O(log N)", True), ("HashMap is stored on the CPU registers", False), ("TreeMap does not support String keys", False), ("HashMap compresses memory by 80%", False)]}
                ]
                seed_assessment_with_questions(
                    course=course_java_fund,
                    assessment_type='FINAL_ASSESSMENT',
                    title="Java Fundamentals Certification Exam",
                    duration=30,
                    pass_pct=70.0,
                    questions_data=java_fund_final_q
                )

            # =========================================================================
            # 4. COURSE: ADVANCED JAVA ENTERPRISE (ID 9)
            # =========================================================================
            course_java_adv = Course.objects.filter(slug='advanced-java-enterprise').first()
            if course_java_adv:
                self.stdout.write(f"Seeding Modules, Materials & Assessments for: {course_java_adv.title}")
                java_adv_modules = [
                    (
                        1,
                        "Spring Boot Architecture & Dependency Injection",
                        "spring-core-di",
                        "Spring IoC Container, ApplicationContext, @Component, @Autowired, @Bean, and auto-configuration.",
                        40,
                        "Spring Boot Architecture and Inversion of Control",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4",
                        {
                            "topic": "Spring Boot & Inversion of Control",
                            "introduction": "Spring Boot simplifies Java enterprise application development with opinionated auto-configuration, embedded servers, and dependency injection.",
                            "concept_explanation": "Inversion of Control (IoC) delegates object creation and lifecycle management to the Spring container. Constructor injection provides immutable, easily unit-testable components.",
                            "key_points": [
                                "@SpringBootApplication enables component scanning, auto-configuration, and property configuration.",
                                "Spring Beans are singleton by default in the ApplicationContext.",
                                "Constructor injection is preferred over field injection for testability.",
                                "@Value and @ConfigurationProperties inject environment configurations."
                            ],
                            "syntax": "@Service\npublic class StudentService {\n    private final StudentRepository repo;\n    public StudentService(StudentRepository repo) {\n        this.repo = repo;\n    }\n}",
                            "examples": [
                                {
                                    "title": "Configuring a Custom Bean with @Configuration and @Bean",
                                    "code": "@Configuration\npublic class AppConfig {\n    @Bean\n    public RestTemplate restTemplate() {\n        return new RestTemplate();\n    }\n}",
                                    "output": "Registers RestTemplate singleton in the Spring container.",
                                    "explanation": "@Bean methods return objects managed by the ApplicationContext."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Placing @SpringBootApplication outside the root package of custom components",
                                    "correct": "Place the main application class in the root parent package",
                                    "reason": "Component scanning recursively scans child packages from the main class location."
                                }
                            ],
                            "important_terms": [
                                {"term": "IoC", "definition": "Inversion of Control; architectural pattern delegating object assembly to a container."},
                                {"term": "Spring Bean", "definition": "An object instantiated, assembled, and managed by the Spring IoC container."}
                            ],
                            "quick_revision": ["Use @Component, @Service, @Repository, @Controller for stereotype annotations.", "Profiles (dev, prod) customize bean creation per environment."],
                            "practice_questions": [
                                {"question": "What is the default scope of a Spring Bean?", "answer": "Singleton", "explanation": "A single shared instance is maintained per Spring IoC container."}
                            ]
                        },
                        "materials/advanced_java_enterprise_handbook.pdf",
                        "Spring Boot DI & Architecture Check",
                        [
                            {"id": 1, "question": "What is the default scope of a Spring Bean in the ApplicationContext?", "options": ["Singleton", "Prototype", "Request", "Session"], "correct_option": "Singleton"},
                            {"id": 2, "question": "Why is constructor-based dependency injection preferred over @Autowired field injection?", "options": ["Facilitates immutability and simplifies unit testing with mocks", "It runs 10x faster at runtime", "Field injection is deprecated in Java 17", "Constructor injection bypasses the Spring container"], "correct_option": "Facilitates immutability and simplifies unit testing with mocks"}
                        ]
                    ),
                    (
                        2,
                        "RESTful Web Services with Spring MVC",
                        "spring-rest-apis",
                        "@RestController, @GetMapping, @PostMapping, RequestBody, ResponseEntity, and global exception handling.",
                        40,
                        "Building Production REST APIs with Spring MVC",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                        {
                            "topic": "Spring REST APIs & Controller Design",
                            "introduction": "Spring MVC provides robust routing, parameter binding, and serialization to develop RESTful microservice contracts.",
                            "concept_explanation": "@RestController combines @Controller and @ResponseBody, automatically serializing Java POJOs into JSON. @ControllerAdvice intercepts exceptions globally across all controllers.",
                            "key_points": [
                                "HTTP methods map directly to actions: GET (read), POST (create), PUT (update), DELETE (remove).",
                                "ResponseEntity<T> customizes HTTP status codes and headers.",
                                "@Valid triggers Bean Validation constraints (@NotNull, @Size).",
                                "@ExceptionHandler methods in @RestControllerAdvice format standardized error responses."
                            ],
                            "syntax": "@RestController\n@RequestMapping(\"/api/courses\")\npublic class CourseController {\n    @GetMapping(\"/{id}\")\n    public ResponseEntity<Course> getCourse(@PathVariable Long id) {\n        return ResponseEntity.ok(service.findById(id));\n    }\n}",
                            "examples": [
                                {
                                    "title": "Global Exception Handling Controller",
                                    "code": "@RestControllerAdvice\npublic class GlobalErrorHandler {\n    @ExceptionHandler(ResourceNotFoundException.class)\n    public ResponseEntity<ApiError> handleNotFound(ResourceNotFoundException ex) {\n        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new ApiError(ex.getMessage()));\n    }\n}",
                                    "output": "Returns structured JSON error with HTTP 404.",
                                    "explanation": "Decouples error response formatting from individual controller methods."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Returning raw domain entities directly from endpoints without DTOs",
                                    "correct": "Map domain models to Data Transfer Objects (DTOs)",
                                    "reason": "DTOs prevent accidental exposure of internal fields (passwords, salts) and circular JSON references."
                                }
                            ],
                            "important_terms": [
                                {"term": "@RestController", "definition": "Convenience annotation combining @Controller and @ResponseBody."},
                                {"term": "DTO", "definition": "Data Transfer Object; object carrying data between processes without domain behavior."}
                            ],
                            "quick_revision": ["Use @PathVariable for URI parameters and @RequestParam for query string parameters.", "HTTP 201 Created should be returned for successful POST operations."],
                            "practice_questions": [
                                {"question": "Which HTTP status code signifies a validation failure in user input?", "answer": "HTTP 400 Bad Request or HTTP 422 Unprocessable Entity.", "explanation": "Indicates client-side request syntax or constraint violations."}
                            ]
                        },
                        "materials/advanced_java_enterprise_handbook.pdf",
                        "Spring REST Controller Practice",
                        [
                            {"id": 1, "question": "What is the difference between @Controller and @RestController in Spring?", "options": ["@RestController includes @ResponseBody on every method automatically", "@Controller only works with XML", "@RestController cannot handle GET requests", "@Controller is for WebSockets only"], "correct_option": "@RestController includes @ResponseBody on every method automatically"},
                            {"id": 2, "question": "Which annotation handles exceptions across all controllers globally in Spring MVC?", "options": ["@ControllerAdvice / @RestControllerAdvice", "@GlobalCatch", "@ApplicationErrorHandler", "@InterceptorError"], "correct_option": "@ControllerAdvice / @RestControllerAdvice"}
                        ]
                    ),
                    (
                        3,
                        "Data Persistence with Spring Data JPA & Hibernate",
                        "spring-data-jpa",
                        "Entities, relationships (@OneToMany, @ManyToOne), JpaRepository, custom JPQL queries, and transaction management.",
                        45,
                        "Enterprise Persistence with Spring Data JPA & Hibernate",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                        {
                            "topic": "Spring Data JPA & Hibernate",
                            "introduction": "Spring Data JPA provides high-productivity data persistence by generating implementation code from repository interface definitions.",
                            "concept_explanation": "Hibernate is the Object-Relational Mapping (ORM) provider implementing the JPA specification. Entities map to tables; Spring repositories provide built-in CRUD, pagination, and derived query methods.",
                            "key_points": [
                                "@Entity marks classes for ORM mapping; @Id specifies primary keys.",
                                "Spring Data generates queries automatically from method names (e.g. findByEmail).",
                                "@Transactional guarantees atomicity, rolling back on unhandled runtime exceptions.",
                                "Lazy loading (@ManyToOne(fetch = FetchType.LAZY)) prevents N+1 query overhead."
                            ],
                            "syntax": "public interface UserRepository extends JpaRepository<User, Long> {\n    Optional<User> findByEmail(String email);\n    @Query(\"SELECT u FROM User u WHERE u.active = true\")\n    List<User> findAllActive();\n}",
                            "examples": [
                                {
                                    "title": "Declaring an Entity with Relationships",
                                    "code": "@Entity\n@Table(name = \"departments\")\npublic class Department {\n    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)\n    private Long id;\n    private String code;\n    @OneToMany(mappedBy = \"department\", fetch = FetchType.LAZY)\n    private List<Student> students = new ArrayList<>();\n}",
                                    "output": "Maps Department class to departments table with 1-to-many relationship.",
                                    "explanation": "mappedBy points to the owning field in the child entity."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Leaving relationships as FetchType.EAGER causing the N+1 query problem",
                                    "correct": "Use FetchType.LAZY and fetch joins (@EntityGraph or JOIN FETCH)",
                                    "reason": "Eager fetching loads all related entities in separate queries, degrading database performance."
                                }
                            ],
                            "important_terms": [
                                {"term": "ORM", "definition": "Object-Relational Mapping; technique converting data between incompatible type systems."},
                                {"term": "JPQL", "definition": "Java Persistence Query Language; queries entities rather than database tables."}
                            ],
                            "quick_revision": ["CascadeType.ALL propagates persist, merge, and remove operations.", "Use @Modifying for UPDATE and DELETE JPQL queries."],
                            "practice_questions": [
                                {"question": "What is the purpose of @Transactional?", "answer": "Enforces atomic database transaction boundary with automatic rollback on error.", "explanation": "Ensures ACID properties for database mutations."}
                            ]
                        },
                        "materials/advanced_java_enterprise_handbook.pdf",
                        "Spring Data JPA & ORM Check",
                        [
                            {"id": 1, "question": "What is the N+1 query problem in ORM systems?", "options": ["Executing 1 query for parents, then N additional queries for related children", "Exceeding database connection pool limits", "Querying a table with N+1 columns simultaneously", "Inserting N+1 rows in a single batch"], "correct_option": "Executing 1 query for parents, then N additional queries for related children"},
                            {"id": 2, "question": "How does Spring Data JPA automatically generate queries like `findByEmail(String email)`?", "options": ["By parsing method names into database queries via reflection at startup", "By sending raw method bytecode to the SQL engine", "By executing an external Python script", "By requiring stored procedures on the DB server"], "correct_option": "By parsing method names into database queries via reflection at startup"}
                        ]
                    ),
                    (
                        4,
                        "Spring Security 6 & Stateless JWT Authentication",
                        "spring-security-jwt",
                        "SecurityFilterChain, BCryptPasswordEncoder, JWT generation/validation filter, and role-based access control.",
                        45,
                        "Securing Microservices with Spring Security and JWT",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
                        {
                            "topic": "Stateless JWT Security Architecture",
                            "introduction": "Modern enterprise applications operate statelessly across distributed cloud microservices using cryptographically signed JSON Web Tokens (JWT).",
                            "concept_explanation": "Spring Security filters incoming HTTP requests through a chain of security interceptors. A custom OncePerRequestFilter validates the Authorization: Bearer <token> header and populates the SecurityContextHolder.",
                            "key_points": [
                                "SecurityFilterChain bean configures endpoint authorization rules and disables session state.",
                                "BCryptPasswordEncoder hashes passwords with a secure, adaptive salting algorithm.",
                                "JWT comprises Header (algorithm), Payload (claims, expiry), and Signature.",
                                "@PreAuthorize(\"hasRole('ADMIN')\") secures individual methods based on authenticated roles."
                            ],
                            "syntax": "@Bean\npublic SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {\n    return http\n        .csrf(csrf -> csrf.disable())\n        .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))\n        .authorizeHttpRequests(auth -> auth.requestMatchers(\"/api/auth/**\").permitAll().anyRequest().authenticated())\n        .build();\n}",
                            "examples": [
                                {
                                    "title": "Verifying JWT Claims in Filter",
                                    "code": "String header = request.getHeader(\"Authorization\");\nif (header != null && header.startsWith(\"Bearer \")) {\n    String token = header.substring(7);\n    String username = jwtService.extractUsername(token);\n    // populate SecurityContextHolder\n}",
                                    "output": "Extracts identity and establishes authenticated principal for current request.",
                                    "explanation": "Operates without requiring server-side session state storage."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Storing sensitive information (plain passwords, secrets) in JWT payload",
                                    "correct": "Store only non-sensitive identifiers and claims (user_id, roles)",
                                    "reason": "JWT payloads are merely base64 encoded and can be decoded by any client."
                                }
                            ],
                            "important_terms": [
                                {"term": "JWT", "definition": "JSON Web Token; compact URL-safe means of representing claims between two parties."},
                                {"term": "SecurityContextHolder", "definition": "Thread-local store holding details of the current security context."}
                            ],
                            "quick_revision": ["Always verify token expiration (exp claim).", "CSRF can be safely disabled for stateless token-authenticated APIs."],
                            "practice_questions": [
                                {"question": "Why is BCrypt considered safe for password hashing?", "answer": "It includes a salt to protect against rainbow tables and has a configurable work factor.", "explanation": "Slow hash algorithm resistant to brute-force GPU attacks."}
                            ]
                        },
                        "materials/advanced_java_enterprise_handbook.pdf",
                        "Spring Security & JWT Check",
                        [
                            {"id": 1, "question": "Why can CSRF protection be safely disabled for REST APIs using stateless JWT authentication?", "options": ["Because browsers do not automatically attach bearer tokens to cross-origin requests", "Because JWT encrypts all HTTP traffic automatically", "Because Spring Security 6 removes CSRF support", "Because CSRF attacks only occur on Windows servers"], "correct_option": "Because browsers do not automatically attach bearer tokens to cross-origin requests"},
                            {"id": 2, "question": "Where does Spring Security store authentication details for the current request thread?", "options": ["SecurityContextHolder", "HttpSessionCookie", "GlobalApplicationState", "DatabaseUserTable"], "correct_option": "SecurityContextHolder"}
                        ]
                    ),
                    (
                        5,
                        "Enterprise Microservices & Cloud Native Deployment",
                        "spring-microservices",
                        "Service decomposition, Spring Cloud Gateway, Docker containerization, Spring Boot Actuator, and health monitoring.",
                        40,
                        "Enterprise Microservices Architecture & Containerization",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
                        {
                            "topic": "Microservices & Cloud Deployment",
                            "introduction": "Enterprise applications decompose monolithic codebases into autonomous, independently deployable microservices orchestrated in containers.",
                            "concept_explanation": "Microservices communicate asynchronously or via lightweight REST/gRPC. An API Gateway routes traffic, enforces rate limiting, and centralizes authentication. Spring Boot Actuator exposes health metrics.",
                            "key_points": [
                                "Microservices adhere to the Single Responsibility Principle with independent databases.",
                                "Spring Boot Actuator provides /actuator/health and /actuator/metrics endpoints.",
                                "Multi-stage Dockerfiles create minimal, secure production container images.",
                                "Resilience patterns (Circuit Breaker, Retry) protect against cascading distributed failures."
                            ],
                            "syntax": "# Multi-stage Dockerfile\nFROM eclipse-temurin:17-jdk-alpine AS build\nWORKDIR /app\nCOPY . .\nRUN ./gradlew bootJar\nFROM eclipse-temurin:17-jre-alpine\nCOPY --from=build /app/build/libs/*.jar app.jar\nENTRYPOINT [\"java\", \"-jar\", \"/app.jar\"]",
                            "examples": [
                                {
                                    "title": "Actuator Health Check Response",
                                    "code": "GET /actuator/health\nHTTP/1.1 200 OK\n{\n  \"status\": \"UP\",\n  \"components\": {\n    \"db\": { \"status\": \"UP\" },\n    \"diskSpace\": { \"status\": \"UP\" }\n  }\n}",
                                    "output": "Enables Kubernetes liveness and readiness probes.",
                                    "explanation": "Reports overall application subsystem health."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Sharing a single relational database directly among multiple microservices",
                                    "correct": "Each microservice must own its private datastore (Database-per-service pattern)",
                                    "reason": "Shared databases create tight schema coupling and prevent independent deployments."
                                }
                            ],
                            "important_terms": [
                                {"term": "API Gateway", "definition": "Single entry point for client requests routing to internal microservices."},
                                {"term": "Actuator", "definition": "Spring Boot module exposing production-ready monitoring and management endpoints."}
                            ],
                            "quick_revision": ["Use Circuit Breakers (Resilience4j) to prevent cascading failures.", "Containerize using lightweight JRE runtime base images."],
                            "practice_questions": [
                                {"question": "What is the purpose of a Kubernetes readiness probe with Spring Actuator?", "answer": "Verifies whether the container is ready to accept incoming user traffic.", "explanation": "Prevents routing traffic to initializing or overloaded pods."}
                            ]
                        },
                        "materials/advanced_java_enterprise_handbook.pdf",
                        "Microservices & Cloud Deployment Practice",
                        [
                            {"id": 1, "question": "What is the primary objective of the Database-per-Service pattern in microservices?", "options": ["Ensure loose coupling so services can evolve and deploy their schemas independently", "Reduce total cloud database hosting costs to zero", "Eliminate all SQL queries in favor of flat text files", "Enforce identical table names across all systems"], "correct_option": "Ensure loose coupling so services can evolve and deploy their schemas independently"},
                            {"id": 2, "question": "Which Spring Boot dependency provides built-in /health and /metrics production monitoring endpoints?", "options": ["spring-boot-starter-actuator", "spring-boot-starter-monitor", "spring-cloud-healthcheck", "spring-boot-diagnostic-tools"], "correct_option": "spring-boot-starter-actuator"}
                        ]
                    )
                ]

                for mod_spec in java_adv_modules:
                    seed_module_content(course_java_adv, *mod_spec)

                # Pre-Assessment & Final Assessment
                java_adv_pre_q = [
                    {"text": "What is Inversion of Control (IoC) in Spring Boot?", "topic_tag": "spring-core-di", "difficulty": "EASY", "explanation": "IoC delegates object creation and dependency wiring to the Spring framework container.", "options": [("Framework controls object creation and lifecycle rather than custom code", True), ("Controlling CPU threads directly with C libraries", False), ("Reversing the order of array iteration", False), ("Inverting database table columns", False)]},
                    {"text": "Which annotation marks a Spring configuration class that declares @Bean methods?", "topic_tag": "spring-core-di", "difficulty": "EASY", "explanation": "@Configuration indicates that a class declares one or more @Bean methods.", "options": [("@Configuration", True), ("@Service", False), ("@Entity", False), ("@ComponentFactory", False)]},
                    {"text": "Which Spring annotation maps HTTP GET requests to specific controller handler methods?", "topic_tag": "spring-rest-apis", "difficulty": "EASY", "explanation": "@GetMapping is a composed annotation acting as a shortcut for @RequestMapping(method = RequestMethod.GET).", "options": [("@GetMapping", True), ("@PostMapping", False), ("@FetchMapping", False), ("@ActionMapping", False)]},
                    {"text": "How do you extract a URI path parameter `/api/students/{id}` in a Spring controller?", "topic_tag": "spring-rest-apis", "difficulty": "EASY", "explanation": "@PathVariable binds a URI template variable into a method parameter.", "options": [("@PathVariable Long id", True), ("@RequestParam Long id", False), ("@RequestBody Long id", False), ("@Header Long id", False)]},
                    {"text": "Which interface in Spring Data JPA provides built-in CRUD and pagination operations?", "topic_tag": "spring-data-jpa", "difficulty": "EASY", "explanation": "JpaRepository extends PagingAndSortingRepository and CrudRepository.", "options": [("JpaRepository", True), ("SqlRepository", False), ("HibernateManager", False), ("DataEntityManager", False)]},
                    {"text": "What does the `@Transactional` annotation guarantee on a service method?", "topic_tag": "spring-data-jpa", "difficulty": "MEDIUM", "explanation": "It ensures the method executes inside a database transaction with automatic commit/rollback.", "options": [("Atomic database execution with rollback on unhandled runtime exceptions", True), ("Asynchronous execution on a secondary thread pool", False), ("Automatic JSON serialization of return values", False), ("Caching of method return values indefinitely", False)]},
                    {"text": "What are the three parts of a standard JSON Web Token (JWT)?", "topic_tag": "spring-security-jwt", "difficulty": "EASY", "explanation": "A JWT consists of Header, Payload, and Signature separated by dots.", "options": [("Header, Payload, and Signature", True), ("Username, Password, and Salt", False), ("Host, Port, and Protocol", False), ("Client, Server, and SessionID", False)]},
                    {"text": "Which password hashing encoder is standard and recommended in Spring Security 6?", "topic_tag": "spring-security-jwt", "difficulty": "EASY", "explanation": "BCryptPasswordEncoder is the standard salt-based key derivation password encoder.", "options": [("BCryptPasswordEncoder", True), ("MD5PasswordEncoder", False), ("PlainTextPasswordEncoder", False), ("SHA1PasswordEncoder", False)]},
                    {"text": "What endpoint does Spring Boot Actuator provide to verify application operational status?", "topic_tag": "spring-microservices", "difficulty": "EASY", "explanation": "/actuator/health returns application and subsystem health indicators.", "options": [("/actuator/health", True), ("/api/status", False), ("/monitor/live", False), ("/sys/check", False)]},
                    {"text": "In a microservices architecture, what is the role of an API Gateway?", "topic_tag": "spring-microservices", "difficulty": "MEDIUM", "explanation": "An API Gateway acts as a single reverse proxy entry point routing client requests to backend services.", "options": [("Centralized entry point routing and securing client requests to microservices", True), ("A physical hardware router inside the server rack", False), ("A database engine replicating SQL queries", False), ("A compiler that compiles Java into JavaScript", False)]}
                ]
                seed_assessment_with_questions(
                    course=course_java_adv,
                    assessment_type='PRE_ASSESSMENT',
                    title="Advanced Java Enterprise Diagnostic Pre-Assessment",
                    duration=20,
                    pass_pct=70.0,
                    questions_data=java_adv_pre_q
                )

                java_adv_final_q = [
                    {"text": "What is the key advantage of constructor injection over field injection (@Autowired) in Spring?", "topic_tag": "spring-core-di", "difficulty": "MEDIUM", "explanation": "Constructor injection enables immutable fields (final) and allows POJO instantiation in unit tests without a Spring context.", "options": [("Enables immutable dependencies (final) and pure POJO unit testing", True), ("Bypasses Java reflection overhead entirely", False), ("Allows circular dependencies to resolve silently", False), ("Automatically creates database tables", False)]},
                    {"text": "How does Spring Boot resolve conflicting beans when multiple candidates match an injection target?", "topic_tag": "spring-core-di", "difficulty": "HARD", "explanation": "@Primary marks a default bean; @Qualifier specifies the exact bean name at the injection site.", "options": [("Using @Primary or @Qualifier(\"beanName\")", True), ("By picking the smallest bean in memory", False), ("By throwing an unresolvable Error at runtime", False), ("By combining both beans into a proxy", False)]},
                    {"text": "Which HTTP status code should a RESTful API return when a POST request successfully creates a new resource?", "topic_tag": "spring-rest-apis", "difficulty": "EASY", "explanation": "HTTP 201 Created indicates successful resource creation, ideally accompanied by a Location header.", "options": [("201 Created", True), ("200 OK", False), ("204 No Content", False), ("301 Moved Permanently", False)]},
                    {"text": "How do you trigger automatic input validation on a `@RequestBody` DTO parameter in Spring MVC?", "topic_tag": "spring-rest-apis", "difficulty": "MEDIUM", "explanation": "Annotating the parameter with `@Valid` or `@Validated` triggers Jakarta Bean Validation.", "options": [("@Valid @RequestBody UserDTO dto", True), ("@CheckInput @RequestBody UserDTO dto", False), ("@Verify @RequestBody UserDTO dto", False), ("@Sanitize @RequestBody UserDTO dto", False)]},
                    {"text": "What is the root cause of the N+1 query problem when querying JPA entities?", "topic_tag": "spring-data-jpa", "difficulty": "HARD", "explanation": "Loading a parent list in 1 query, then triggering N subsequent queries for each parent's lazily/eagerly fetched relationship.", "options": [("1 initial query for parents followed by N individual queries for child associations", True), ("A syntax error in SQL indexing", False), ("Running an uncommitted transaction across N threads", False), ("Creating N+1 tables for an inheritance hierarchy", False)]},
                    {"text": "How can you resolve the N+1 query issue in a Spring Data JPA repository query?", "topic_tag": "spring-data-jpa", "difficulty": "HARD", "explanation": "Using JOIN FETCH in JPQL or @EntityGraph instructs Hibernate to load associations in a single SQL JOIN.", "options": [("Using JOIN FETCH in JPQL or applying @EntityGraph", True), ("Switching to NoSQL database storage", False), ("Increasing database connection pool size", False), ("Setting FetchType.EAGER on all relations", False)]},
                    {"text": "Where should a JWT token typically be sent in an authenticated HTTP request?", "topic_tag": "spring-security-jwt", "difficulty": "EASY", "explanation": "In the Authorization header with the Bearer scheme (Authorization: Bearer <token>).", "options": [("Authorization header as 'Bearer <token>'", True), ("URL query parameter as '?jwt=<token>'", False), ("Cookie named 'session_token' only", False), ("HTTP User-Agent header", False)]},
                    {"text": "What does a signature in a JWT prove?", "topic_tag": "spring-security-jwt", "difficulty": "MEDIUM", "explanation": "The signature verifies that the sender is who it says it is and ensures the message was not altered in transit.", "options": [("The token was issued by a trusted party and has not been tampered with", True), ("The token payload is encrypted and unreadable to clients", False), ("The client's IP address has not changed", False), ("The database password was verified on the client", False)]},
                    {"text": "In a distributed microservices system, what is the role of the Circuit Breaker pattern (e.g. Resilience4j)?", "topic_tag": "spring-microservices", "difficulty": "HARD", "explanation": "Prevents cascading failures by halting calls to a failing remote dependency and returning a fallback response.", "options": [("Halts calls to a failing downstream service to prevent cascading system collapse", True), ("Encrypts TCP socket streams using SSL", False), ("Automatically scales Kubernetes nodes", False), ("Breaks infinite loops in recursive algorithms", False)]},
                    {"text": "Why do production Docker container images for Spring Boot use multi-stage builds?", "topic_tag": "spring-microservices", "difficulty": "MEDIUM", "explanation": "Multi-stage builds compile with a full JDK in stage 1, then copy only the jar into a slim JRE runtime in stage 2.", "options": [("Produces small, secure images containing only the JRE runtime without compiler tools", True), ("Runs the application twice as fast", False), ("Eliminates the need for a database", False), ("Enables Windows containers to run on Linux natively", False)]}
                ]
                seed_assessment_with_questions(
                    course=course_java_adv,
                    assessment_type='FINAL_ASSESSMENT',
                    title="Advanced Java Enterprise Certification Exam",
                    duration=30,
                    pass_pct=70.0,
                    questions_data=java_adv_final_q
                )

            # =========================================================================
            # 5. COURSE: ENTERPRISE FULL STACK (REACT & NODE.JS) (ID 10)
            # =========================================================================
            course_fullstack = Course.objects.filter(slug='enterprise-fullstack-react-node').first()
            if course_fullstack:
                self.stdout.write(f"Seeding Modules, Materials & Assessments for: {course_fullstack.title}")
                fullstack_modules = [
                    (
                        1,
                        "Modern React Architecture & Component State",
                        "react-architecture",
                        "JSX compilation, declarative rendering, useState, useEffect, virtual DOM reconciliation, and unidirectional data flow.",
                        45,
                        "Modern React Architecture & Component State",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WhatCarCanYouGetForAGrand.mp4",
                        {
                            "topic": "React Architecture & State",
                            "introduction": "React is a component-driven declarative UI library based on reactive state and virtual DOM diffing.",
                            "concept_explanation": "React components describe UI as a function of state. When state changes via setter functions, React re-executes the component and reconciles the virtual DOM with minimal real DOM mutations.",
                            "key_points": [
                                "JSX compiles to React.createElement calls via Babel/Vite.",
                                "useState holds local reactive component state across re-renders.",
                                "useEffect executes side-effects (data fetching, subscriptions) after DOM painting.",
                                "Data flows unidirectionally from parent to child via props."
                            ],
                            "syntax": "import { useState, useEffect } from 'react';\nfunction Counter() {\n    const [count, setCount] = useState(0);\n    return <button onClick={() => setCount(count + 1)}>Count: {count}</button>;\n}",
                            "examples": [
                                {
                                    "title": "Data Fetching with useEffect Hook",
                                    "code": "useEffect(() => {\n    let isMounted = true;\n    fetch('/api/skills')\n        .then(res => res.json())\n        .then(data => { if (isMounted) setSkills(data); });\n    return () => { isMounted = false; };\n}, []);",
                                    "output": "Fetches data on component mount and cleans up if unmounted before response.",
                                    "explanation": "Empty dependency array [] ensures execution only once on initial mount."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Mutating state directly: state.count = 5",
                                    "correct": "setCount(5) or setCount(prev => prev + 1)",
                                    "reason": "Direct mutation does not trigger React's reconciliation and re-render cycle."
                                }
                            ],
                            "important_terms": [
                                {"term": "Virtual DOM", "definition": "In-memory tree representation of real DOM elements used for fast reconciliation."},
                                {"term": "Reconciliation", "definition": "The algorithm React uses to diff one tree with another to determine parts which need update."}
                            ],
                            "quick_revision": ["State updates may be asynchronous and batched.", "Use key prop on mapped list items to preserve component identity."],
                            "practice_questions": [
                                {"question": "What is the purpose of the dependency array in useEffect?", "answer": "Controls when the effect re-runs (only when dependencies change).", "explanation": "Omitting it runs on every render; [] runs only on mount."}
                            ]
                        },
                        "materials/fullstack_react_node_handbook.pdf",
                        "React Architecture & State Practice",
                        [
                            {"id": 1, "question": "Why must you never mutate React state directly (e.g. state.val = 1)?", "options": ["Direct mutation does not trigger the reconciliation and re-render cycle", "It throws a fatal SyntaxError in modern browsers", "It deletes the virtual DOM tree", "It disables TypeScript compilation"], "correct_option": "Direct mutation does not trigger the reconciliation and re-render cycle"},
                            {"id": 2, "question": "When does a useEffect hook with an empty dependency array `[]` execute?", "options": ["Once after the initial component mount", "On every single component re-render", "Only right before the component unmounts", "Before the initial DOM rendering"], "correct_option": "Once after the initial component mount"}
                        ]
                    ),
                    (
                        2,
                        "React Router, Forms & Global State Management",
                        "react-routing-state",
                        "Client-side routing with React Router, form validation, custom hooks, and global state via Context API.",
                        40,
                        "Routing, Forms & State Management in React",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                        {
                            "topic": "React Router & Global Context",
                            "introduction": "Single Page Applications (SPAs) navigate dynamically without full browser page reloads using client-side routing and centralized global state.",
                            "concept_explanation": "React Router coordinates URLs with component trees. Controlled form components bind input values to reactive state. Context API provides shared state across deep component trees without prop drilling.",
                            "key_points": [
                                "BrowserRouter, Routes, and Route map paths to components.",
                                "useNavigate hook triggers programmatic navigation.",
                                "useContext and createContext distribute global authentication/theme states.",
                                "Custom hooks encapsulate reusable stateful business logic."
                            ],
                            "syntax": "const AuthContext = createContext(null);\nexport const useAuth = () => useContext(AuthContext);\n// In component:\nconst { user, login } = useAuth();",
                            "examples": [
                                {
                                    "title": "Controlled Input Form Component",
                                    "code": "const [email, setEmail] = useState('');\n<input type='email' value={email} onChange={e => setEmail(e.target.value)} />",
                                    "output": "React state serves as the single source of truth for the input's current value.",
                                    "explanation": "Every keystroke updates state, triggering controlled re-rendering."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Prop drilling: passing props through 5 layers of intermediate components",
                                    "correct": "Use React Context API or a state management store for global dependencies",
                                    "reason": "Avoids boilerplate and tight coupling in intermediary presentation components."
                                }
                            ],
                            "important_terms": [
                                {"term": "Prop Drilling", "definition": "Passing data from a parent to a deeply nested child through irrelevant intermediaries."},
                                {"term": "SPA", "definition": "Single Page Application; updates page contents dynamically without full page reloads."}
                            ],
                            "quick_revision": ["e.preventDefault() prevents standard browser form reload on submit.", "Custom hook names must always begin with 'use'."],
                            "practice_questions": [
                                {"question": "What is the return value of the useNavigate hook in React Router?", "answer": "A function to navigate programmatically between routes.", "explanation": "e.g. const navigate = useNavigate(); navigate('/dashboard');"}
                            ]
                        },
                        "materials/fullstack_react_node_handbook.pdf",
                        "Routing & Context State Check",
                        [
                            {"id": 1, "question": "What is the primary benefit of using React Context API in an enterprise application?", "options": ["Prevents prop drilling by providing data globally across the component tree", "Accelerates database SQL execution speed", "Compiles React components into native iOS binaries", "Renders HTML entirely on the server without client JS"], "correct_option": "Prevents prop drilling by providing data globally across the component tree"},
                            {"id": 2, "question": "What does `e.preventDefault()` do inside a form onSubmit handler?", "options": ["Prevents the default browser behavior of reloading the page upon submission", "Cancels all active HTTP network requests", "Resets all form input values to blank", "Validates password complexity"], "correct_option": "Prevents the default browser behavior of reloading the page upon submission"}
                        ]
                    ),
                    (
                        3,
                        "Node.js, Express & RESTful API Engineering",
                        "nodejs-express-api",
                        "V8 engine, non-blocking asynchronous event loop, Express middleware pipeline, routing, and error handling.",
                        45,
                        "Building High-Scale Backend APIs with Node.js and Express",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4",
                        {
                            "topic": "Node.js Architecture & Express APIs",
                            "introduction": "Node.js runs Google Chrome's V8 JavaScript engine outside the browser, executing non-blocking I/O operations through an event loop.",
                            "concept_explanation": "Express is a minimalist web framework for Node.js organized around middleware functions that process requests in sequence before sending a response.",
                            "key_points": [
                                "Single-threaded event loop delegates I/O (files, network, DB) to libuv worker threads.",
                                "Middleware functions take (req, res, next) and can transform requests or terminate them.",
                                "Express.json() parses incoming JSON bodies.",
                                "Error-handling middleware takes 4 arguments: (err, req, res, next)."
                            ],
                            "syntax": "const express = require('express');\nconst app = express();\napp.use(express.json());\napp.get('/api/health', (req, res) => res.json({ status: 'UP' }));\napp.listen(5000);",
                            "examples": [
                                {
                                    "title": "Custom Authentication Middleware",
                                    "code": "const authMiddleware = (req, res, next) => {\n    const token = req.headers.authorization;\n    if (!token) return res.status(401).json({ error: 'Unauthorized' });\n    req.user = verifyToken(token);\n    next();\n};",
                                    "output": "Guards downstream routes, returning HTTP 401 if missing token.",
                                    "explanation": "Calling next() forwards execution to the next handler in the pipeline."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Blocking the event loop with synchronous CPU-intensive tasks: fs.readFileSync()",
                                    "correct": "Use asynchronous non-blocking methods: fs.promises.readFile()",
                                    "reason": "Blocking operations freeze the single thread, preventing all concurrent users from receiving responses."
                                }
                            ],
                            "important_terms": [
                                {"term": "Event Loop", "definition": "Mechanism that allows Node.js to perform non-blocking I/O operations by offloading tasks."},
                                {"term": "Middleware", "definition": "Functions that have access to the request, response, and the next middleware function."}
                            ],
                            "quick_revision": ["Always call next(err) to pass errors to centralized error middleware.", "Use async/await with try-catch blocks for asynchronous handlers."],
                            "practice_questions": [
                                {"question": "How many parameters must an Express error-handling middleware function have?", "answer": "Exactly 4 parameters: (err, req, res, next).", "explanation": "Express identifies error-handling middleware by function arity (4 arguments)."}
                            ]
                        },
                        "materials/fullstack_react_node_handbook.pdf",
                        "Node.js & Express Middleware Practice",
                        [
                            {"id": 1, "question": "Why is synchronous file I/O (like fs.readFileSync) discouraged in production Node.js servers?", "options": ["It blocks the single-threaded event loop, halting all concurrent requests", "It consumes 100% of GPU memory", "Node.js does not support synchronous functions", "It automatically terminates the OS kernel"], "correct_option": "It blocks the single-threaded event loop, halting all concurrent requests"},
                            {"id": 2, "question": "What is the purpose of the `next()` function in an Express middleware?", "options": ["Passes control to the next middleware or route handler in the pipeline", "Restarts the Node.js server process", "Sends the final HTTP response to the client", "Rolls back active database transactions"], "correct_option": "Passes control to the next middleware or route handler in the pipeline"}
                        ]
                    ),
                    (
                        4,
                        "Relational Database Persistence & ORM Modeling",
                        "database-orm-modeling",
                        "Relational schema design, normalization, foreign keys, migrations, ORM querying, and SQL injection defense.",
                        45,
                        "Relational Database Design, Indexing and ORM Modeling",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                        {
                            "topic": "Relational Data Modeling & Security",
                            "introduction": "Enterprise full stack platforms rely on relational databases (PostgreSQL, MySQL, SQLite) to provide ACID transactional integrity and relational normalization.",
                            "concept_explanation": "Relational modeling separates data into normalized entities connected by Foreign Key constraints. ORM libraries generate parameterized SQL queries, protecting against SQL injection attacks.",
                            "key_points": [
                                "Primary keys guarantee row uniqueness; Foreign keys enforce referential integrity.",
                                "Database indexes (B-Tree) accelerate search lookups at the expense of write overhead.",
                                "ACID guarantees: Atomicity, Consistency, Isolation, Durability.",
                                "Parameterized queries treat inputs as data literals rather than executable SQL code."
                            ],
                            "syntax": "SELECT u.id, u.username, COUNT(e.id) AS enrollments\nFROM users u\nLEFT JOIN enrollments e ON u.id = e.student_id\nGROUP BY u.id, u.username;",
                            "examples": [
                                {
                                    "title": "Preventing SQL Injection with Parameterized Queries",
                                    "code": "// VULNERABLE:\nconst sql = \"SELECT * FROM users WHERE email = '\" + input + \"'\";\n// SECURE (Parameterized):\nconst sql = \"SELECT * FROM users WHERE email = $1\";\nawait pool.query(sql, [input]);",
                                    "output": "Input is treated strictly as a string literal, thwarting injection exploits.",
                                    "explanation": "The database driver escapes and handles parameters securely."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Concatenating un-sanitized user input strings directly into SQL statements",
                                    "correct": "Always use parameterized queries or ORM query builders",
                                    "reason": "String concatenation leaves the application vulnerable to catastrophic SQL injection."
                                }
                            ],
                            "important_terms": [
                                {"term": "Referential Integrity", "definition": "Property ensuring relationships between tables remain consistent and valid."},
                                {"term": "SQL Injection", "definition": "Security vulnerability allowing attackers to interfere with queries made to database."}
                            ],
                            "quick_revision": ["Migrations version-control database schema transformations.", "Use transactions when mutating multiple related tables."],
                            "practice_questions": [
                                {"question": "What does the 'I' in ACID stand for?", "answer": "Isolation", "explanation": "Ensures concurrent transactions execute without interfering with one another."}
                            ]
                        },
                        "materials/fullstack_react_node_handbook.pdf",
                        "Database Modeling & Security Check",
                        [
                            {"id": 1, "question": "What is the primary technical defense against SQL injection vulnerabilities?", "options": ["Parameterized queries / prepared statements", "Encoding all text in Base64", "Storing passwords in plain text", "Disabling database indexes"], "correct_option": "Parameterized queries / prepared statements"},
                            {"id": 2, "question": "What does a Foreign Key constraint enforce in a relational database?", "options": ["Referential integrity between parent and child tables", "Encryption of data on disk", "Automatic creation of backup snapshots", "Hardware RAID failover"], "correct_option": "Referential integrity between parent and child tables"}
                        ]
                    ),
                    (
                        5,
                        "Full Stack JWT Authentication, Security & CI/CD",
                        "fullstack-security-deployment",
                        "Stateless authentication flow, bcrypt hashing, CORS protection, helmet HTTP headers, and production deployment pipelines.",
                        45,
                        "Full Stack Security, Hardening and Production Deployment",
                        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                        {
                            "topic": "Full Stack Security & Deployment",
                            "introduction": "Deploying full stack software requires defense-in-depth security: secure cookie/token storage, CORS policies, secure password hashing, and continuous integration.",
                            "concept_explanation": "Clients authenticate via credentials, receive a cryptographically signed JWT, and attach it to subsequent requests. Production servers implement CORS, rate-limiting, and automated deployment pipelines.",
                            "key_points": [
                                "Passwords must be hashed with bcrypt or Argon2 with unique salts.",
                                "CORS (Cross-Origin Resource Sharing) headers restrict which origins can access backend APIs.",
                                "Helmet middleware sets defensive HTTP headers (CSP, X-Frame-Options).",
                                "Continuous Integration (CI) executes linting, type checks, and automated unit tests."
                            ],
                            "syntax": "const cors = require('cors');\napp.use(cors({\n    origin: ['http://localhost:5173', 'https://skills.francisxavier.ac.in'],\n    credentials: true\n}));",
                            "examples": [
                                {
                                    "title": "Bcrypt Password Hashing Workflow",
                                    "code": "const bcrypt = require('bcrypt');\nconst saltRounds = 12;\nconst hash = await bcrypt.hash(rawPassword, saltRounds);\n// Verification:\nconst isValid = await bcrypt.compare(candidatePassword, hash);",
                                    "output": "Produces irreversible, salted password digest.",
                                    "explanation": "Salt prevents rainbow table attacks; work factor slows brute force."
                                }
                            ],
                            "common_mistakes": [
                                {
                                    "mistake": "Setting CORS to origin: '*' on authenticated API routes with credentials",
                                    "correct": "Explicitly whitelist authorized frontend origins",
                                    "reason": "Browsers reject wildcard origins when credentials (cookies, auth headers) are included."
                                }
                            ],
                            "important_terms": [
                                {"term": "CORS", "definition": "Security mechanism allowing restricted resources to be requested from another domain."},
                                {"term": "Salting", "definition": "Adding random unique characters to passwords prior to hashing to foil rainbow tables."}
                            ],
                            "quick_revision": ["Never commit secrets or .env files to Git repositories.", "Use HTTPS in production to encrypt tokens in transit."],
                            "practice_questions": [
                                {"question": "What is the purpose of the HTTP header X-Frame-Options: DENY?", "answer": "Prevents clickjacking attacks by forbidding the page from being embedded in an iframe.", "explanation": "Protects users from invisible overlay clicks."}
                            ]
                        },
                        "materials/fullstack_react_node_handbook.pdf",
                        "Security & Deployment Verification Check",
                        [
                            {"id": 1, "question": "Why is salt added to passwords before hashing with algorithms like bcrypt?", "options": ["To ensure identical passwords generate distinct hashes, defeating precomputed rainbow tables", "To make password strings shorter in memory", "To allow passwords to be decrypted by admins", "To enable faster database queries"], "correct_option": "To ensure identical passwords generate distinct hashes, defeating precomputed rainbow tables"},
                            {"id": 2, "question": "What attack does the HTTP response header `X-Frame-Options: DENY` prevent?", "options": ["Clickjacking attacks via invisible iframes", "SQL injection attacks", "Buffer overflow exploits", "Distributed Denial of Service (DDoS)"], "correct_option": "Clickjacking attacks via invisible iframes"}
                        ]
                    )
                ]

                for mod_spec in fullstack_modules:
                    seed_module_content(course_fullstack, *mod_spec)

                # Pre-Assessment & Final Assessment
                fs_pre_q = [
                    {"text": "What is JSX in React development?", "topic_tag": "react-architecture", "difficulty": "EASY", "explanation": "JSX is a syntax extension for JavaScript that compiles into React.createElement calls.", "options": [("A syntax extension allowing HTML-like tags inside JavaScript code", True), ("A separate programming language replacing JavaScript", False), ("A CSS preprocessor similar to Sass", False), ("A database query language for MongoDB", False)]},
                    {"text": "Which React hook is used to manage local component state?", "topic_tag": "react-architecture", "difficulty": "EASY", "explanation": "useState initializes and returns a state value along with an update function.", "options": [("useState", True), ("useEffect", False), ("useContext", False), ("useReducerOnly", False)]},
                    {"text": "What is the purpose of React Router in a web application?", "topic_tag": "react-routing-state", "difficulty": "EASY", "explanation": "React Router coordinates client-side routing without reloading the browser page.", "options": [("Enables client-side routing and page transitions without page reloads", True), ("Renders 3D graphics on HTML5 Canvas", False), ("Manages SQL database connections", False), ("Transpiles TypeScript into JavaScript", False)]},
                    {"text": "What is the primary problem solved by React's Context API?", "topic_tag": "react-routing-state", "difficulty": "MEDIUM", "explanation": "Context API shares state across component hierarchies without manual prop drilling.", "options": [("Eliminates prop drilling through intermediate components", True), ("Encrypts network packets over HTTPS", False), ("Replaces the Node.js event loop", False), ("Optimizes CSS selector performance", False)]},
                    {"text": "What is the execution model of the core Node.js runtime?", "topic_tag": "nodejs-express-api", "difficulty": "EASY", "explanation": "Node.js uses a single-threaded non-blocking asynchronous event loop architecture.", "options": [("Single-threaded event loop with non-blocking I/O", True), ("Multi-threaded synchronous process per user", False), ("Purely compiled machine binary without an event loop", False), ("Multi-process memory shared kernel", False)]},
                    {"text": "Which Express middleware parses incoming requests with JSON payloads?", "topic_tag": "nodejs-express-api", "difficulty": "EASY", "explanation": "express.json() parses incoming request bodies formatted as JSON.", "options": [("express.json()", True), ("express.urlencoded()", False), ("express.static()", False), ("express.parse()", False)]},
                    {"text": "What guarantees the ACID properties in relational database systems?", "topic_tag": "database-orm-modeling", "difficulty": "MEDIUM", "explanation": "ACID guarantees that database transactions are processed reliably.", "options": [("Atomicity, Consistency, Isolation, and Durability", True), ("Asynchronous, Concurrent, Indexed, and Distributed", False), ("Array, Collection, Interface, and Data", False), ("Authentication, Cryptography, Identity, and Defense", False)]},
                    {"text": "How do parameterized queries prevent SQL injection?", "topic_tag": "database-orm-modeling", "difficulty": "MEDIUM", "explanation": "Parameters are treated strictly as data values, preventing them from altering the query structure.", "options": [("Input is treated strictly as data literals, never executable SQL commands", True), ("They compile all database tables into C++", False), ("They encrypt the database password with MD5", False), ("They require admin biometric verification", False)]},
                    {"text": "What algorithm is recommended for irreversible, salted password storage?", "topic_tag": "fullstack-security-deployment", "difficulty": "EASY", "explanation": "bcrypt incorporates a salt and adaptive work factor designed for password hashing.", "options": [("bcrypt / Argon2", True), ("MD5", False), ("Base64", False), ("SHA-1", False)]},
                    {"text": "What does CORS stand for in web security?", "topic_tag": "fullstack-security-deployment", "difficulty": "EASY", "explanation": "Cross-Origin Resource Sharing manages HTTP access across differing origins.", "options": [("Cross-Origin Resource Sharing", True), ("Centralized Object Routing Standard", False), ("Client-Oriented Response Service", False), ("Cryptographic Origin Recovery System", False)]}
                ]
                seed_assessment_with_questions(
                    course=course_fullstack,
                    assessment_type='PRE_ASSESSMENT',
                    title="Full Stack Web Engineering Diagnostic Pre-Assessment",
                    duration=20,
                    pass_pct=70.0,
                    questions_data=fs_pre_q
                )

                fs_final_q = [
                    {"text": "What is the reconciliation algorithm in React?", "topic_tag": "react-architecture", "difficulty": "HARD", "explanation": "Reconciliation compares the virtual DOM trees (diffing) to determine the minimal set of changes to apply to the actual DOM.", "options": [("The diffing algorithm comparing virtual DOM trees to apply minimal actual DOM updates", True), ("The build process that bundles JavaScript with Vite", False), ("The database migration script that synchronizes schemas", False), ("The method that decrypts HTTPS payloads in the browser", False)]},
                    {"text": "Why does React require a unique `key` prop when rendering dynamic arrays of elements?", "topic_tag": "react-architecture", "difficulty": "MEDIUM", "explanation": "Keys help React identify which items have changed, been added, or been removed between renders.", "options": [("Identifies elements across renders to maintain component state and avoid re-mounting", True), ("Sets the HTML id attribute in the browser DOM", False), ("Encrypts the rendered component with a cryptographic key", False), ("Sorts elements alphabetically automatically", False)]},
                    {"text": "What is the return signature of the custom hook pattern in React?", "topic_tag": "react-routing-state", "difficulty": "MEDIUM", "explanation": "A custom hook is a JavaScript function whose name starts with 'use' and that may call other hooks, returning data/functions.", "options": [("Can return any data structure (arrays, objects, primitives) needed by consumers", True), ("Must always return exactly JSX elements", False), ("Must return an Express middleware function", False), ("Must return a Promise resolving to void", False)]},
                    {"text": "In React Router v6+, how do you protect a route so that unauthenticated users are redirected to `/login`?", "topic_tag": "react-routing-state", "difficulty": "MEDIUM", "explanation": "An AuthGuard or ProtectedRoute wrapper checks user status and returns `<Navigate to='/login' replace />` if unauthenticated.", "options": [("Render a ProtectedRoute wrapper returning <Navigate to='/login' /> when unauthenticated", True), ("Set status='401' on the Route component", False), ("Throw an error inside the BrowserRouter", False), ("Configure the Nginx server to reject the route", False)]},
                    {"text": "What handles background asynchronous I/O operations (file system, DNS, crypto) in Node.js?", "topic_tag": "nodejs-express-api", "difficulty": "HARD", "explanation": "The C-based libuv thread pool handles blocking operations asynchronously on behalf of the single V8 event loop thread.", "options": [("The libuv thread pool", True), ("The browser rendering engine", False), ("The HTML5 Web Worker thread", False), ("The Apache HTTP server", False)]},
                    {"text": "What happens if an error is thrown inside an asynchronous Express route handler without try-catch or next(err)?", "topic_tag": "nodejs-express-api", "difficulty": "MEDIUM", "explanation": "In Node.js, an unhandled promise rejection occurs, which may crash the process or leave the client request hanging indefinitely.", "options": [("Unhandled promise rejection occurs and the client request may hang until timeout", True), ("Express automatically restarts the operating system", False), ("The error is printed to the client browser console automatically", False), ("The database rollback is triggered automatically", False)]},
                    {"text": "What is the purpose of database normalization (up to 3rd Normal Form)?", "topic_tag": "database-orm-modeling", "difficulty": "MEDIUM", "explanation": "Normalization minimizes data redundancy and eliminates update/deletion anomalies.", "options": [("Minimizes data redundancy and prevents update/delete anomalies", True), ("Increases file storage size to maximize backup redundancy", False), ("Converts SQL tables into MongoDB JSON documents", False), ("Translates all numbers into floating point values", False)]},
                    {"text": "In a relational schema, what does `ON DELETE CASCADE` specify on a Foreign Key?", "topic_tag": "database-orm-modeling", "difficulty": "MEDIUM", "explanation": "When a referenced row in the parent table is deleted, all matching rows in the child table are deleted automatically.", "options": [("Deleting a parent row automatically deletes all related child rows", True), ("Prevents the parent row from ever being deleted", False), ("Sets child foreign key references to null", False), ("Archives deleted records to an external cloud bucket", False)]},
                    {"text": "Why should sensitive JWT tokens NOT be stored in standard browser localStorage if XSS vulnerabilities exist?", "topic_tag": "fullstack-security-deployment", "difficulty": "HARD", "explanation": "Any JavaScript code running on the page (including malicious injected scripts) can read localStorage; HttpOnly cookies prevent script access.", "options": [("Malicious scripts injected via XSS can read localStorage directly; HttpOnly cookies mitigate this", True), ("localStorage is limited to exactly 16 bytes of data", False), ("localStorage values are automatically sent to third-party ad networks", False), ("localStorage is wiped every time a user refreshes the tab", False)]},
                    {"text": "What does Content Security Policy (CSP) header protect against in full stack applications?", "topic_tag": "fullstack-security-deployment", "difficulty": "HARD", "explanation": "CSP restricts the resources (such as JavaScript, CSS, Images) that the browser is allowed to load, preventing Cross-Site Scripting (XSS).", "options": [("Restricts unauthorized script sources, preventing Cross-Site Scripting (XSS) and data injection", True), ("Encrypts all database backups at rest", False), ("Enforces multi-factor SMS authentication", False), ("Prevents server-side memory leaks in Node.js", False)]}
                ]
                seed_assessment_with_questions(
                    course=course_fullstack,
                    assessment_type='FINAL_ASSESSMENT',
                    title="Full Stack Web Engineering Certification Exam",
                    duration=30,
                    pass_pct=70.0,
                    questions_data=fs_final_q
                )

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("POPULATION OF MATERIALS & ASSESSMENTS COMPLETE!"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"Total Courses in DB: {Course.objects.count()}")
        self.stdout.write(f"Total Modules in DB: {Module.objects.count()}")
        self.stdout.write(f"Total Lessons in DB: {Lesson.objects.count()}")
        self.stdout.write(f"Total Video Resources: {VideoResource.objects.count()}")
        self.stdout.write(f"Total Study Materials: {StudyMaterial.objects.count()}")
        self.stdout.write(f"Total Practice Tasks: {PracticeTask.objects.count()}")
        self.stdout.write(f"Total Assessments: {Assessment.objects.count()}")
        self.stdout.write(f"Total Assessment Questions: {Question.objects.count()}")
        self.stdout.write(f"Total Question Options: {QuestionOption.objects.count()}")
