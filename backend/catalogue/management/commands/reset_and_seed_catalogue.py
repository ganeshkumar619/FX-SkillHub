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
from learning.models import (
    Enrollment,
    ModuleProgress,
    VideoProgress,
    MaterialProgress,
    PracticeProgress
)
from assessments.models import (
    Assessment,
    Question,
    QuestionOption,
    AssessmentAttempt,
    StudentAnswer
)
from proctoring.models import (
    ProctoringEvent,
    RiskScore,
    MentorReviewRecord
)
from certificates.models import (
    Certificate,
    CertificateVerification
)

User = get_user_model()


def generate_pdf_handbook(filepath, title, subtitle, sections):
    """Generates a real PDF study material using ReportLab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

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
    help = "Safely resets existing development catalogue records and seeds a fresh, structured, module-based catalogue."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write(self.style.WARNING("FX SKILLHUB — SAFE CATALOGUE RESET & REBUILD"))
        self.stdout.write(self.style.WARNING("=" * 70))

        with transaction.atomic():
            # 1. Show what will be cleared
            self.stdout.write("Inspecting existing demo/development records...")
            self.stdout.write(f" - Skills: {Skill.objects.count()}")
            self.stdout.write(f" - Courses: {Course.objects.count()}")
            self.stdout.write(f" - Modules: {Module.objects.count()}")
            self.stdout.write(f" - Lessons: {Lesson.objects.count()}")
            self.stdout.write(f" - Enrollments: {Enrollment.objects.count()}")
            self.stdout.write(f" - Assessments: {Assessment.objects.count()}")

            self.stdout.write(self.style.SUCCESS("Preserving User accounts, Authentication, and Departments..."))

            # 2. Clear dependent proctoring, certificates, and attempts first
            MentorReviewRecord.objects.all().delete()
            RiskScore.objects.all().delete()
            ProctoringEvent.objects.all().delete()
            CertificateVerification.objects.all().delete()
            Certificate.objects.all().delete()
            StudentAnswer.objects.all().delete()
            AssessmentAttempt.objects.all().delete()
            QuestionOption.objects.all().delete()
            Question.objects.all().delete()
            Assessment.objects.all().delete()

            # Clear learning progress
            VideoProgress.objects.all().delete()
            MaterialProgress.objects.all().delete()
            PracticeProgress.objects.all().delete()
            ModuleProgress.objects.all().delete()
            Enrollment.objects.all().delete()

            # Clear catalogue
            VideoResource.objects.all().delete()
            StudyMaterial.objects.all().delete()
            PracticeTask.objects.all().delete()
            LearningResource.objects.all().delete()
            Lesson.objects.all().delete()
            Module.objects.all().delete()
            Course.objects.all().delete()
            Skill.objects.all().delete()

            self.stdout.write(self.style.SUCCESS("Existing demo catalogue and progress records safely cleared!"))

            # Ensure admin / faculty users exist
            admin_user = User.objects.filter(role='ADMIN').first()
            faculty_user = User.objects.filter(role='MENTOR').first()
            if not faculty_user:
                faculty_user = admin_user

            # Retrieve departments
            cse_dept = Department.objects.filter(code='CSE').first()
            it_dept = Department.objects.filter(code='IT').first()
            aids_dept = Department.objects.filter(code='AIDS').first()

            # Ensure categories and domains
            cat_prog, _ = SkillCategory.objects.get_or_create(
                name="Programming & Software Engineering",
                defaults={'description': 'Core software development, object-oriented principles, and scalable system design.', 'order': 1}
            )
            cat_web, _ = SkillCategory.objects.get_or_create(
                name="Web & Cloud Technologies",
                defaults={'description': 'Full stack architectures, cloud platforms, and distributed systems.', 'order': 2}
            )

            domain_prog, _ = SkillDomain.objects.get_or_create(
                category=cat_prog,
                name="Software Development",
                defaults={'description': 'Modern object-oriented and functional programming.'}
            )
            domain_enterprise, _ = SkillDomain.objects.get_or_create(
                category=cat_prog,
                name="Enterprise Systems",
                defaults={'description': 'Enterprise architecture, design patterns, and JVM frameworks.'}
            )
            domain_web, _ = SkillDomain.objects.get_or_create(
                category=cat_web,
                name="Full Stack Engineering",
                defaults={'description': 'Frontend UI, REST APIs, and transactional databases.'}
            )

            # Generate real PDF study materials in backend/media/materials/
            media_dir = Path(settings.MEDIA_ROOT)
            materials_dir = media_dir / 'materials'
            materials_dir.mkdir(parents=True, exist_ok=True)

            handbook_pdf_path = materials_dir / 'python_fundamentals_handbook.pdf'
            generate_pdf_handbook(
                handbook_pdf_path,
                "Python Fundamentals Official Handbook",
                "Department of Computer Science & Engineering",
                [
                    ("1. Course Syllabus & Architecture", "Python is an interpreted, high-level, dynamically typed language created by Guido van Rossum. It supports multiple programming paradigms including structured, object-oriented, and functional programming."),
                    ("2. Data Structures & Types", "Standard scalar types include int, float, str, and bool. Built-in compound collections include list (mutable, ordered), tuple (immutable, ordered), set (mutable, unordered, unique), and dict (mutable key-value mappings)."),
                    ("3. Execution Model", "Source code (.py) is compiled to bytecode (.pyc) and executed on the Python Virtual Machine (PVM). Memory management is automated via reference counting and a generational cyclic garbage collector."),
                    ("4. Standard Library", "Python features a rich standard library ('batteries included') providing OS interfaces, math, datetime, json, collections, and concurrent execution primitives.")
                ]
            )

            oop_pdf_path = materials_dir / 'python_oop_guide.pdf'
            generate_pdf_handbook(
                oop_pdf_path,
                "Object-Oriented Design in Python",
                "Centre for Training & Skills Development",
                [
                    ("1. Classes and Objects", "A class is a blueprint for creating objects. State is encapsulated in instance variables initialized via __init__, while behavior is defined in methods taking self as the first parameter."),
                    ("2. Inheritance & Polymorphism", "Python supports single and multiple inheritance using the C3 Linearization Method Resolution Order (MRO). Polymorphism allows functions to operate on objects of different classes as long as they implement the expected interface."),
                    ("3. Encapsulation & Properties", "Private attributes use leading double underscores (__attr) for name mangling. Controlled attribute access is achieved using the @property decorator."),
                    ("4. Magic Methods (Dunder)", "Special methods such as __str__, __repr__, __len__, and __eq__ integrate custom classes cleanly with Python built-in functions and operators.")
                ]
            )

            # =========================================================
            # SKILL 1: Python Programming
            # =========================================================
            skill_python = Skill.objects.create(
                name="Python Programming",
                slug="python-programming",
                short_description="Comprehensive Python mastery from foundational algorithms to advanced OOP and data processing.",
                description="The institutional Python Programming skill track provides a rigorous foundation in computational thinking, software design, object-oriented modeling, exception safety, and standard library tools for high-performance software engineering.",
                category=cat_prog,
                domain=domain_prog,
                department=cse_dept,
                level="BEGINNER",
                skill_type="CORE",
                learning_outcomes=[
                    "Write idiomatic, PEP 8 compliant Python software",
                    "Design modular programs with functions and object-oriented abstractions",
                    "Implement robust exception handling and resource-safe file I/O",
                    "Apply core data structures for algorithmic problem solving"
                ],
                estimated_duration="6 Weeks",
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                source_title="FXEC Autonomous Computer Science Curriculum",
                source_url="https://www.francisxavier.ac.in/",
                created_by=faculty_user
            )

            # Course 1A: Python Fundamentals
            course_py_fund = Course.objects.create(
                skill=skill_python,
                title="Python Fundamentals",
                slug="python-fundamentals",
                instructor_name="Prof. Ramesh M.E., CSE",
                description="A comprehensive, module-based foundational course in Python. Covers variables, control structures, loops, functions, OOP, exception handling, and a capstone mini-project. All modules must be completed to unlock the final certification exam.",
                level="BEGINNER",
                estimated_hours=12,
                course_types=['CORE_SKILL', 'VALUE_ADDED'],
                outcomes=[
                    "Master core Python syntax, variables, and expressions",
                    "Construct branch logic and iterative algorithms",
                    "Decompose complex problems using modular functions",
                    "Architect classes and instantiate objects with OOP",
                    "Pass the rigorous FXEC Proctored Certification Exam"
                ],
                thumbnail_url="https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&auto=format&fit=crop&q=60",
                is_published=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                source_title="FXEC Centre for Training & Skills Development",
                source_url="https://www.francisxavier.ac.in/",
                created_by=faculty_user
            )
            course_py_fund.departments.add(cse_dept, it_dept)

            # Course 1B: Python for Data Analysis
            course_py_data = Course.objects.create(
                skill=skill_python,
                title="Python for Data Analysis",
                slug="python-data-analysis",
                instructor_name="Dr. S. Priya Ph.D., AIDS",
                description="Intermediate Python curriculum focusing on NumPy array computation, Pandas DataFrame transformation, and exploratory statistical data analysis.",
                level="INTERMEDIATE",
                estimated_hours=14,
                course_types=['CORE_SKILL', 'PLACEMENT'],
                outcomes=[
                    "Execute vectorized array math with NumPy",
                    "Filter, aggregate, and join complex tabular datasets with Pandas",
                    "Clean real-world missing and outlier data",
                    "Generate statistical visualizations with Matplotlib & Seaborn"
                ],
                thumbnail_url="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&auto=format&fit=crop&q=60",
                is_published=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                source_title="FXEC Department of AI & Data Science",
                source_url="https://www.francisxavier.ac.in/",
                created_by=faculty_user
            )
            course_py_data.departments.add(aids_dept, cse_dept)

            # =========================================================
            # SKILL 2: Java Enterprise Development
            # =========================================================
            skill_java = Skill.objects.create(
                name="Java Enterprise Development",
                slug="java-enterprise-development",
                short_description="Enterprise-grade Java programming, JVM internals, Collections, and Spring Boot REST APIs.",
                description="Designed for high-scale enterprise applications, this skill track covers strong static typing, JVM memory layout, the Collections Framework, multithreading, and RESTful service engineering.",
                category=cat_prog,
                domain=domain_enterprise,
                department=it_dept,
                level="INTERMEDIATE",
                skill_type="CORE",
                learning_outcomes=[
                    "Develop type-safe object-oriented systems with Java 17+",
                    "Leverage Java Collections and Stream API for data manipulation",
                    "Build robust multithreaded and concurrent applications",
                    "Implement enterprise REST APIs with Spring Boot"
                ],
                estimated_duration="8 Weeks",
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                source_title="FXEC IT Department Curriculum",
                source_url="https://www.francisxavier.ac.in/",
                created_by=faculty_user
            )

            # Course 2A: Java Fundamentals
            course_java_fund = Course.objects.create(
                skill=skill_java,
                title="Java Fundamentals",
                slug="java-fundamentals",
                instructor_name="Prof. K. Anand M.Tech, IT",
                description="Complete foundation in Java programming: JVM bytecode architecture, class definitions, inheritance, interface contracts, Collections Framework, and exception handling.",
                level="BEGINNER",
                estimated_hours=14,
                course_types=['CORE_SKILL'],
                outcomes=[
                    "Understand JVM, JRE, and JDK architecture",
                    "Write robust class hierarchies with inheritance and polymorphism",
                    "Handle runtime exceptions gracefully",
                    "Apply Lists, Sets, and Maps appropriately"
                ],
                thumbnail_url="https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&auto=format&fit=crop&q=60",
                is_published=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                source_title="FXEC Information Technology Syllabus",
                source_url="https://www.francisxavier.ac.in/",
                created_by=faculty_user
            )
            course_java_fund.departments.add(it_dept, cse_dept)

            # Course 2B: Advanced Java Enterprise
            course_java_adv = Course.objects.create(
                skill=skill_java,
                title="Advanced Java Enterprise",
                slug="advanced-java-enterprise",
                instructor_name="Dr. V. Murugan Ph.D., CSE",
                description="Enterprise application engineering covering Spring Boot 3, Spring Data JPA, RESTful microservices, and JWT security.",
                level="ADVANCED",
                estimated_hours=18,
                course_types=['CORE_SKILL', 'PLACEMENT'],
                outcomes=[
                    "Build Spring Boot microservices",
                    "Manage relational persistence with Spring Data JPA",
                    "Implement stateless token authentication with Spring Security",
                    "Containerize and deploy enterprise backend services"
                ],
                thumbnail_url="https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=800&auto=format&fit=crop&q=60",
                is_published=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                source_title="FXEC Centre for Placement & Higher Education",
                source_url="https://www.francisxavier.ac.in/",
                created_by=faculty_user
            )
            course_java_adv.departments.add(cse_dept, it_dept)

            # =========================================================
            # SKILL 3: Full Stack Web Engineering
            # =========================================================
            skill_web = Skill.objects.create(
                name="Full Stack Web Engineering",
                slug="full-stack-web-engineering",
                short_description="End-to-end full stack software engineering using React, Node.js, and relational database systems.",
                description="Covers responsive user interfaces with React, state management, asynchronous REST microservices with Node.js/Express, transactional database design, and end-to-end system security.",
                category=cat_web,
                domain=domain_web,
                department=cse_dept,
                is_cross_department=True,
                level="INTERMEDIATE",
                skill_type="PLACEMENT",
                learning_outcomes=[
                    "Design dynamic single-page applications with React and TypeScript",
                    "Build secure, non-blocking REST APIs with Express and Node.js",
                    "Architect relational database schemas with migrations and indexing",
                    "Deploy full stack applications with continuous integration"
                ],
                estimated_duration="8 Weeks",
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                source_title="FXEC Interdisciplinary Skill Matrix",
                source_url="https://www.francisxavier.ac.in/",
                created_by=faculty_user
            )
            skill_web.departments.add(cse_dept, it_dept, aids_dept)

            course_fullstack = Course.objects.create(
                skill=skill_web,
                title="Enterprise Full Stack (React & Node.js)",
                slug="enterprise-fullstack-react-node",
                instructor_name="Prof. S. Karthik M.E., IT & CSE Team",
                description="Rigorous full stack engineering track covering modern TypeScript React frontends, Express REST services, database persistence with ORM, and JWT authentication.",
                level="INTERMEDIATE",
                estimated_hours=16,
                course_types=['INTERDISCIPLINARY', 'PLACEMENT', 'VALUE_ADDED'],
                outcomes=[
                    "Build responsive React frontends with hooks and context",
                    "Write production-grade Express.js REST APIs",
                    "Implement secure JWT authentication and audit logging",
                    "Pass the comprehensive full stack proctored assessment"
                ],
                thumbnail_url="https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800&auto=format&fit=crop&q=60",
                is_published=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                source_title="FXEC Autonomous Curriculum 2026",
                source_url="https://www.francisxavier.ac.in/",
                created_by=faculty_user
            )
            course_fullstack.departments.add(cse_dept, it_dept, aids_dept)

            # =========================================================
            # BUILD STRUCTURED MODULES FOR "Python Fundamentals"
            # 8 Modules as specified in User Requirement
            # =========================================================
            py_modules_spec = [
                {
                    "order": 1,
                    "title": "Introduction to Python",
                    "topic_tag": "python-intro",
                    "duration": 30,
                    "desc": "Installation, virtual environments, the Python interpreter, execution model, and basic output.",
                    "video_title": "Python Architecture & Interactive Execution",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                    "video_dur": 300,
                    "mat_title": "Python Architecture Handbook & Environment Setup",
                    "mat_type": "PDF",
                    "mat_file": "materials/python_fundamentals_handbook.pdf",
                    "practice_title": "Python Syntax & Print Output Concept Check",
                    "practice_mcqs": [
                        {
                            "id": 1,
                            "question": "Which of the following creates a valid single-line comment in Python?",
                            "options": ["// Comment", "/* Comment */", "# Comment", "-- Comment"],
                            "correct_option": "# Comment"
                        },
                        {
                            "id": 2,
                            "question": "What is the primary execution model of standard CPython?",
                            "options": ["Direct machine code compilation", "Source code is compiled to bytecode and executed on the PVM", "Pure interpretation without bytecode", "Transpiled to C++"],
                            "correct_option": "Source code is compiled to bytecode and executed on the PVM"
                        }
                    ]
                },
                {
                    "order": 2,
                    "title": "Variables and Data Types",
                    "topic_tag": "variables-datatypes",
                    "duration": 35,
                    "desc": "Dynamic typing, integers, floats, strings, booleans, and type conversion mechanics.",
                    "video_title": "Working with Dynamic Typing & Memory References",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                    "video_dur": 360,
                    "mat_title": "Data Types Cheatsheet & Memory Layout Guide",
                    "mat_type": "PDF",
                    "mat_file": "materials/python_fundamentals_handbook.pdf",
                    "practice_title": "Data Types & Type Conversion Practice",
                    "practice_mcqs": [
                        {
                            "id": 1,
                            "question": "What is the output of type(10 / 2) in Python 3?",
                            "options": ["<class 'int'>", "<class 'float'>", "<class 'double'>", "<class 'number'>"],
                            "correct_option": "<class 'float'>"
                        },
                        {
                            "id": 2,
                            "question": "Which collection type in Python is ordered and immutable?",
                            "options": ["list", "set", "dict", "tuple"],
                            "correct_option": "tuple"
                        }
                    ]
                },
                {
                    "order": 3,
                    "title": "Operators and Conditions",
                    "topic_tag": "operators-conditions",
                    "duration": 30,
                    "desc": "Arithmetic, logical, comparison, identity, and conditional if-elif-else branching.",
                    "video_title": "Control Flow and Conditional Branching Mechanics",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
                    "video_dur": 300,
                    "mat_title": "Conditional Branching Truth Tables & Best Practices",
                    "mat_type": "NOTES",
                    "mat_file": "materials/python_fundamentals_handbook.pdf",
                    "practice_title": "Conditional Logic & Short-Circuit Evaluation Practice",
                    "practice_mcqs": [
                        {
                            "id": 1,
                            "question": "What does the expression `True or False and False` evaluate to in Python?",
                            "options": ["False", "True", "SyntaxError", "None"],
                            "correct_option": "True"
                        },
                        {
                            "id": 2,
                            "question": "What is the difference between `==` and `is` in Python?",
                            "options": ["`==` checks object identity; `is` checks value equality", "`==` checks value equality; `is` checks object memory identity", "They are completely interchangeable", "`is` is deprecated"],
                            "correct_option": "`==` checks value equality; `is` checks object memory identity"
                        }
                    ]
                },
                {
                    "order": 4,
                    "title": "Loops and Iterations",
                    "topic_tag": "loops-iterations",
                    "duration": 40,
                    "desc": "While loops, for loops with range, iteration over collections, break, continue, and else clauses.",
                    "video_title": "Mastering Iterables, Range, and Loop Optimization",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4",
                    "video_dur": 420,
                    "mat_title": "Iteration Patterns & Generator Efficiency Notes",
                    "mat_type": "ARTICLE",
                    "mat_file": "materials/python_fundamentals_handbook.pdf",
                    "practice_title": "Loop Control & Iterable Processing Check",
                    "practice_mcqs": [
                        {
                            "id": 1,
                            "question": "When does the `else` block of a `for` loop execute in Python?",
                            "options": ["Only if the loop terminates via a `break` statement", "Only if the loop exhausts all elements without encountering a `break`", "At the beginning of every iteration", "Only when an exception is raised"],
                            "correct_option": "Only if the loop exhausts all elements without encountering a `break`"
                        }
                    ]
                },
                {
                    "order": 5,
                    "title": "Functions and Scope",
                    "topic_tag": "functions-scope",
                    "duration": 45,
                    "desc": "Function definitions, positional & keyword arguments, default values, *args, **kwargs, and LEGB scope.",
                    "video_title": "Modular Python: Parameter Passing and Scope Rules",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
                    "video_dur": 450,
                    "mat_title": "LEGB Scope Resolution & First-Class Functions Reference",
                    "mat_type": "PDF",
                    "mat_file": "materials/python_fundamentals_handbook.pdf",
                    "practice_title": "Functions, Default Arguments & Scope Exercises",
                    "practice_mcqs": [
                        {
                            "id": 1,
                            "question": "Why is using a mutable default argument (like `def func(lst=[]):`) dangerous in Python?",
                            "options": ["It raises a TypeError at runtime", "The default list is created once at function definition and shared across subsequent calls", "It causes a memory leak immediately", "Python does not allow default arguments"],
                            "correct_option": "The default list is created once at function definition and shared across subsequent calls"
                        }
                    ]
                },
                {
                    "order": 6,
                    "title": "Object-Oriented Programming",
                    "topic_tag": "oop-concepts",
                    "duration": 50,
                    "desc": "Classes, constructors, instance vs class attributes, inheritance, method overriding, and encapsulation.",
                    "video_title": "Object-Oriented Design and Encapsulation in Python",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
                    "video_dur": 480,
                    "mat_title": "Object-Oriented Design in Python Guide",
                    "mat_type": "PDF",
                    "mat_file": "materials/python_oop_guide.pdf",
                    "practice_title": "OOP Class Architecture & Inheritance Check",
                    "practice_mcqs": [
                        {
                            "id": 1,
                            "question": "Which method is the primary constructor called when instantiating a new object in Python?",
                            "options": ["__new__", "__init__", "__construct__", "__start__"],
                            "correct_option": "__init__"
                        },
                        {
                            "id": 2,
                            "question": "How do you access a parent class method inside an overridden subclass method?",
                            "options": ["parent.method()", "super().method()", "base.method()", "this.method()"],
                            "correct_option": "super().method()"
                        }
                    ]
                },
                {
                    "order": 7,
                    "title": "Exception Handling and File I/O",
                    "topic_tag": "exceptions-file-io",
                    "duration": 35,
                    "desc": "Try-except-finally blocks, custom exceptions, reading/writing files, and context managers (with).",
                    "video_title": "Robust Error Handling and Context Managers",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackSeeTheWorld.mp4",
                    "video_dur": 360,
                    "mat_title": "Exception Hierarchy & Safe File Operations Notes",
                    "mat_type": "NOTES",
                    "mat_file": "materials/python_fundamentals_handbook.pdf",
                    "practice_title": "Exception Handling & File Safety Practice",
                    "practice_mcqs": [
                        {
                            "id": 1,
                            "question": "What is the primary benefit of using `with open('file.txt') as f:`?",
                            "options": ["It increases file reading speed by 50%", "It automatically closes the file descriptor even if an error or exception occurs", "It writes file contents to memory immediately", "It disables write permissions automatically"],
                            "correct_option": "It automatically closes the file descriptor even if an error or exception occurs"
                        }
                    ]
                },
                {
                    "order": 8,
                    "title": "Mini Project: Automated Gradebook",
                    "topic_tag": "mini-project-gradebook",
                    "duration": 60,
                    "desc": "Capstone integration: build an automated student grade calculation and report generator using functions, OOP, and file I/O.",
                    "video_title": "Capstone Gradebook Project Architecture & Walkthrough",
                    "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
                    "video_dur": 300,
                    "mat_title": "Capstone Gradebook Project Specification & Starter Code",
                    "mat_type": "CODE_FILE",
                    "mat_file": "materials/python_fundamentals_handbook.pdf",
                    "practice_title": "Gradebook Logic Verification & Capstone Check",
                    "practice_mcqs": [
                        {
                            "id": 1,
                            "question": "In the Gradebook architecture, how should student records be stored for O(1) roll number lookup?",
                            "options": ["A singly linked list", "A dictionary mapping roll_number to Student object", "A tuple of tuples", "A sorted array with linear search"],
                            "correct_option": "A dictionary mapping roll_number to Student object"
                        }
                    ]
                }
            ]

            for m_spec in py_modules_spec:
                mod = Module.objects.create(
                    course=course_py_fund,
                    order=m_spec["order"],
                    title=m_spec["title"],
                    topic_tag=m_spec["topic_tag"],
                    description=m_spec["desc"],
                    duration_minutes=m_spec["duration"],
                    estimated_minutes=m_spec["duration"],
                    learning_objectives=[f"Master {m_spec['title']}", "Apply concepts in practical exercises"],
                    is_required=True,
                    status="PUBLISHED",
                    source_type="FXEC_OFFICIAL",
                    created_by=faculty_user
                )

                # Lesson
                lsn = Lesson.objects.create(
                    module=mod,
                    order=1,
                    title=f"Core Concepts: {m_spec['title']}",
                    description=m_spec["desc"],
                    content_type="VIDEO",
                    duration_minutes=15,
                    estimated_minutes=15,
                    is_required=True,
                    status="PUBLISHED",
                    source_type="FXEC_OFFICIAL",
                    created_by=faculty_user
                )

                # Video Resource (Required, 80% threshold)
                VideoResource.objects.create(
                    module=mod,
                    lesson=lsn,
                    title=m_spec["video_title"],
                    description=f"Curated academic lecture on {m_spec['title']} with theoretical foundations and live demonstration.",
                    video_type="EXTERNAL_VIDEO",
                    external_url=m_spec["video_url"],
                    duration_seconds=m_spec["video_dur"],
                    completion_threshold_percent=80.0,
                    order=1,
                    is_required=True,
                    status="PUBLISHED",
                    source_type="FXEC_OFFICIAL",
                    created_by=faculty_user
                )

                # Study Material (Required)
                StudyMaterial.objects.create(
                    module=mod,
                    lesson=lsn,
                    title=m_spec["mat_title"],
                    description=f"Authoritative reading material and reference guidelines for {m_spec['title']}.",
                    resource_type=m_spec["mat_type"],
                    file=m_spec["mat_file"],
                    completion_method="MANUAL_COMPLETE",
                    order=1,
                    is_required=True,
                    status="PUBLISHED",
                    source_type="FXEC_OFFICIAL",
                    uploaded_by=faculty_user
                )

                # Practice Task (Required)
                PracticeTask.objects.create(
                    module=mod,
                    lesson=lsn,
                    title=m_spec["practice_title"],
                    description=f"Formative practice check to verify comprehension of {m_spec['title']}.",
                    task_type="MCQ_PRACTICE",
                    content={"questions": m_spec["practice_mcqs"]},
                    pass_score=70.0,
                    order=1,
                    is_required=True,
                    status="PUBLISHED",
                    source_type="FXEC_OFFICIAL",
                    created_by=faculty_user
                )

            # =========================================================
            # FINAL ASSESSMENT FOR "Python Fundamentals"
            # =========================================================
            final_assessment = Assessment.objects.create(
                course=course_py_fund,
                title="Python Fundamentals Final Certification Assessment",
                assessment_type="FINAL_ASSESSMENT",
                version=1,
                duration_minutes=30,
                pass_percentage=70.0,
                max_attempts=3,
                randomize_questions=True,
                randomize_options=True,
                is_published=True,
                created_by=faculty_user,
                camera_required=True,
                screen_share_required=True,
                fullscreen_required=True,
                face_detection_enabled=True,
                max_camera_warnings=2,
                max_multiple_face_warnings=2,
                max_screen_share_warnings=2,
                max_fullscreen_warnings=2,
                max_tab_switch_warnings=2,
                auto_terminate_on_limit=True
            )

            # Create 10 rigorous assessment questions
            assessment_questions_data = [
                {
                    "text": "What is the output of `bool([])`, `bool([0])`, and `bool('False')` in Python?",
                    "topic_tag": "variables-datatypes",
                    "explanation": "An empty collection [] is falsy. A non-empty list [0] is truthy. A non-empty string 'False' is truthy.",
                    "options": [
                        ("False, True, True", True),
                        ("False, False, False", False),
                        ("True, True, True", False),
                        ("False, True, False", False),
                    ]
                },
                {
                    "text": "Which built-in Python module provides functions for interacting with the operating system and file system paths?",
                    "topic_tag": "python-intro",
                    "explanation": "The os module (along with pathlib) provides standard OS and filesystem abstractions.",
                    "options": [
                        ("os", True),
                        ("syslib", False),
                        ("system", False),
                        ("filesystem", False),
                    ]
                },
                {
                    "text": "What is the result of `list(range(2, 10, 3))` in Python?",
                    "topic_tag": "loops-iterations",
                    "explanation": "range(start, stop, step) starts at 2, steps by 3, yielding 2, 5, 8 (stopping before 10).",
                    "options": [
                        ("[2, 5, 8]", True),
                        ("[2, 5, 8, 11]", False),
                        ("[3, 6, 9]", False),
                        ("[2, 4, 6, 8]", False),
                    ]
                },
                {
                    "text": "How are variable arguments packed into a tuple inside a Python function signature?",
                    "topic_tag": "functions-scope",
                    "explanation": "The single asterisk *args syntax gathers positional arguments into a tuple.",
                    "options": [
                        ("*args", True),
                        ("**kwargs", False),
                        ("&args", False),
                        ("...args", False),
                    ]
                },
                {
                    "text": "In Python object-oriented programming, which method is called automatically when an object is printed with print(obj)?",
                    "topic_tag": "oop-concepts",
                    "explanation": "The __str__ method returns the informal, readable string representation of an object.",
                    "options": [
                        ("__str__", True),
                        ("__print__", False),
                        ("__display__", False),
                        ("__repr__ only", False),
                    ]
                },
                {
                    "text": "Which exception block in Python executes only when NO exception was raised in the try block?",
                    "topic_tag": "exceptions-file-io",
                    "explanation": "The else block executes only if the try clause completed with zero exceptions.",
                    "options": [
                        ("else", True),
                        ("finally", False),
                        ("except", False),
                        ("catch", False),
                    ]
                },
                {
                    "text": "What does the `pass` statement do in a Python block?",
                    "topic_tag": "operators-conditions",
                    "explanation": "pass is a null operation; nothing happens when it executes. It acts as a syntactic placeholder.",
                    "options": [
                        ("It is a no-operation statement used as a placeholder", True),
                        ("It passes execution to the parent function", False),
                        ("It terminates the current loop immediately", False),
                        ("It passes control to the operating system", False),
                    ]
                },
                {
                    "text": "What is the return value of `dict.get(key, default)` if `key` does NOT exist in the dictionary?",
                    "topic_tag": "variables-datatypes",
                    "explanation": "dict.get returns the specified default value (or None if not provided) without raising KeyError.",
                    "options": [
                        ("The specified default value", True),
                        ("Raises KeyError", False),
                        ("Returns False", False),
                        ("Creates the key with value None", False),
                    ]
                },
                {
                    "text": "Which keyword is used to access and modify a global variable inside a local function scope?",
                    "topic_tag": "functions-scope",
                    "explanation": "The `global` keyword declares that a variable in the local scope references the module-level namespace.",
                    "options": [
                        ("global", True),
                        ("nonlocal", False),
                        ("outer", False),
                        ("public", False),
                    ]
                },
                {
                    "text": "In Python, which file mode opens a file for appending binary data without overwriting existing content?",
                    "topic_tag": "exceptions-file-io",
                    "explanation": "'ab' opens a file in append mode ('a') with binary access ('b').",
                    "options": [
                        ("'ab'", True),
                        ("'wb'", False),
                        ("'rb+'", False),
                        ("'a+'", False),
                    ]
                }
            ]

            for idx, q_data in enumerate(assessment_questions_data, start=1):
                q = Question.objects.create(
                    assessment=final_assessment,
                    text=q_data["text"],
                    topic_tag=q_data["topic_tag"],
                    question_type="MCQ_SINGLE",
                    difficulty="EASY",
                    marks=1,
                    explanation=q_data["explanation"],
                    order=idx
                )
                for opt_idx, (opt_text, is_correct) in enumerate(q_data["options"], start=1):
                    QuestionOption.objects.create(
                        question=q,
                        text=opt_text,
                        is_correct=is_correct,
                        order=opt_idx
                    )

            # Build modules for Course 2A (Java Fundamentals) & Course 3A (Full Stack)
            # Java Fundamentals Module 1 & 2
            j_mod1 = Module.objects.create(
                course=course_java_fund,
                order=1,
                title="Java Architecture & Environment Setup",
                topic_tag="java-intro",
                description="JDK, JVM, bytecode, class loaders, and writing your first Java class.",
                duration_minutes=35,
                estimated_minutes=35,
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                created_by=faculty_user
            )
            j_lsn1 = Lesson.objects.create(
                module=j_mod1,
                order=1,
                title="JVM Bytecode & The Compilation Pipeline",
                content_type="VIDEO",
                duration_minutes=20,
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                created_by=faculty_user
            )
            VideoResource.objects.create(
                module=j_mod1,
                lesson=j_lsn1,
                title="Java Virtual Machine Architecture Explained",
                video_type="EXTERNAL_VIDEO",
                external_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4",
                duration_seconds=300,
                completion_threshold_percent=80.0,
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                created_by=faculty_user
            )
            StudyMaterial.objects.create(
                module=j_mod1,
                lesson=j_lsn1,
                title="JVM Internals & Memory Architecture Guide",
                resource_type="PDF",
                file="materials/python_fundamentals_handbook.pdf",
                completion_method="MANUAL_COMPLETE",
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                uploaded_by=faculty_user
            )
            PracticeTask.objects.create(
                module=j_mod1,
                lesson=j_lsn1,
                title="Java Environment Concept Check",
                task_type="MCQ_PRACTICE",
                content={"questions": [{"id": 1, "question": "What is the file extension of compiled Java bytecode?", "options": [".class", ".java", ".jar", ".bin"], "correct_option": ".class"}]},
                pass_score=70.0,
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                created_by=faculty_user
            )

            # Java Fundamentals Final Assessment
            Assessment.objects.create(
                course=course_java_fund,
                title="Java Fundamentals Certification Exam",
                assessment_type="FINAL_ASSESSMENT",
                version=1,
                duration_minutes=30,
                pass_percentage=70.0,
                is_published=True,
                created_by=faculty_user
            )

            # Full Stack Course Module 1
            fs_mod1 = Module.objects.create(
                course=course_fullstack,
                order=1,
                title="Modern React Architecture & Component State",
                topic_tag="react-architecture",
                description="Declarative UI, JSX, component lifecycles, and unidirectional data flow.",
                duration_minutes=45,
                estimated_minutes=45,
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                created_by=faculty_user
            )
            fs_lsn1 = Lesson.objects.create(
                module=fs_mod1,
                order=1,
                title="React Hooks and Reactive State Management",
                content_type="VIDEO",
                duration_minutes=25,
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                created_by=faculty_user
            )
            VideoResource.objects.create(
                module=fs_mod1,
                lesson=fs_lsn1,
                title="Building Scalable React Applications",
                video_type="EXTERNAL_VIDEO",
                external_url="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WhatCarCanYouGetForAGrand.mp4",
                duration_seconds=300,
                completion_threshold_percent=80.0,
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                created_by=faculty_user
            )
            StudyMaterial.objects.create(
                module=fs_mod1,
                lesson=fs_lsn1,
                title="Modern React Design Patterns Handbook",
                resource_type="PDF",
                file="materials/python_fundamentals_handbook.pdf",
                completion_method="MANUAL_COMPLETE",
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                uploaded_by=faculty_user
            )
            PracticeTask.objects.create(
                module=fs_mod1,
                lesson=fs_lsn1,
                title="React State & Props Verification Practice",
                task_type="MCQ_PRACTICE",
                content={"questions": [{"id": 1, "question": "Which hook in React is used to execute side effects after rendering?", "options": ["useEffect", "useState", "useMemo", "useCallback"], "correct_option": "useEffect"}]},
                pass_score=70.0,
                is_required=True,
                status="PUBLISHED",
                source_type="FXEC_OFFICIAL",
                created_by=faculty_user
            )

            # Full Stack Final Assessment
            Assessment.objects.create(
                course=course_fullstack,
                title="Full Stack Web Engineering Certification Exam",
                assessment_type="FINAL_ASSESSMENT",
                version=1,
                duration_minutes=40,
                pass_percentage=70.0,
                is_published=True,
                created_by=faculty_user
            )

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("CATALOGUE RESET & REBUILD COMPLETE!"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"Created Skills: {Skill.objects.count()}")
        self.stdout.write(f"Created Courses: {Course.objects.count()}")
        self.stdout.write(f"Created Modules: {Module.objects.count()}")
        self.stdout.write(f"Created Video Resources: {VideoResource.objects.count()}")
        self.stdout.write(f"Created Study Materials: {StudyMaterial.objects.count()}")
        self.stdout.write(f"Created Practice Tasks: {PracticeTask.objects.count()}")
        self.stdout.write(f"Created Final Assessments: {Assessment.objects.count()}")
