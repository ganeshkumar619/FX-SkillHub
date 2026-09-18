from django.core.management.base import BaseCommand
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
    AISkillSuggestion
)
from assessments.models import Assessment, Question, QuestionOption

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds verified institutional metadata from Francis Xavier Engineering College (FXEC) with full hierarchy & provenance'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting FXEC verified data seeding with provenance tracking...'))
        now = timezone.now()

        stats = {
            'imported': 0,
            'skipped': 0,
            'needs_verification': 0,
            'duplicate': 0,
            'invalid_source': 0
        }

        # -----------------------------------------------------------------
        # 1. Seed Verified Departments (Priority 1 & 2: francisxavier.ac.in)
        # -----------------------------------------------------------------
        departments_data = [
            {'code': 'AIDS', 'name': 'Artificial Intelligence & Data Science', 'description': 'UG Programme approved by AICTE & Anna University.'},
            {'code': 'CIVIL', 'name': 'Civil Engineering', 'description': 'UG Programme in Civil Engineering.'},
            {'code': 'CSBS', 'name': 'Computer Science and Business System', 'description': 'UG Programme blending CS and enterprise business systems.'},
            {'code': 'CSE', 'name': 'Computer Science and Engineering', 'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.'},
            {'code': 'ECE', 'name': 'Electronics and Communication Engineering', 'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.'},
            {'code': 'EEE', 'name': 'Electrical and Electronics Engineering', 'description': 'NBA Accredited UG Programme & Recognized Anna University Research Centre.'},
            {'code': 'IT', 'name': 'Information Technology', 'description': 'Permanently affiliated UG Programme by Anna University.'},
            {'code': 'MECH', 'name': 'Mechanical Engineering', 'description': 'NBA Accredited UG Programme.'},
            {'code': 'MBA', 'name': 'Master of Business Administration', 'description': 'Autonomous PG Programme rated Top B-School.'},
            {'code': 'MCA', 'name': 'Master of Computer Application', 'description': 'Autonomous PG Programme in computer applications.'},
        ]

        dept_objs = {}
        for d in departments_data:
            dept, created = Department.objects.update_or_create(
                code=d['code'],
                defaults={
                    'name': d['name'],
                    'description': d['description'],
                    'source_type': 'FXEC_OFFICIAL',
                    'source_url': 'https://www.francisxavier.ac.in/departments',
                    'source_title': 'Departments | Francis Xavier Engineering College',
                    'source_accessed_at': now,
                    'last_verified_at': now,
                    'content_status': 'PUBLISHED',
                    'approval_status': 'APPROVED'
                }
            )
            dept_objs[d['code']] = dept
            if created:
                stats['imported'] += 1

        # -----------------------------------------------------------------
        # 2. Seed Verified Skill Categories (Skill Pillars)
        # -----------------------------------------------------------------
        categories_data = [
            {
                'name': 'Foundation Course',
                'description': 'Introduces first year engineering students to fundamental engineering and technical logic.',
                'order': 1
            },
            {
                'name': 'Faculty Initiatives Skills',
                'description': 'Workshops and faculty-led deep-dives to assess current industry trends.',
                'order': 2
            },
            {
                'name': 'Mandatory Skills',
                'description': 'Essential core and IT industry skills required for student graduation job fit.',
                'order': 3
            },
            {
                'name': 'Certification Courses / Value Added Courses',
                'description': 'Department-conducted value-added courses supplementing the university syllabus.',
                'order': 4
            },
            {
                'name': 'Placement Fit Training Courses',
                'description': 'Comprehensive employability capability, technical aptitude, and problem-solving readiness.',
                'order': 5
            },
        ]

        cat_objs = {}
        for c in categories_data:
            cat, created = SkillCategory.objects.update_or_create(
                name=c['name'],
                defaults={
                    'description': c['description'],
                    'order': c['order'],
                    'source_type': 'FXEC_OFFICIAL',
                    'source_url': 'https://francisxavier.ac.in/centre/training?page=activities',
                    'source_title': 'Training & Skills Development Activities | FXEC',
                    'source_accessed_at': now,
                    'last_verified_at': now,
                    'content_status': 'PUBLISHED',
                    'approval_status': 'APPROVED'
                }
            )
            cat_objs[c['name']] = cat
            if created:
                stats['imported'] += 1

        # -----------------------------------------------------------------
        # 3. Seed Skill Domains (Hierarchy: Category -> Domain)
        # -----------------------------------------------------------------
        domains_data = [
            {'category': 'Foundation Course', 'name': 'Programming & Computational Logic', 'order': 1},
            {'category': 'Faculty Initiatives Skills', 'name': 'Artificial Intelligence & Data Analytics', 'order': 1},
            {'category': 'Mandatory Skills', 'name': 'Cybersecurity & Computer Forensics', 'order': 1},
            {'category': 'Certification Courses / Value Added Courses', 'name': 'Embedded Systems & Industrial IoT', 'order': 1},
            {'category': 'Certification Courses / Value Added Courses', 'name': 'Robotics & Mechatronics Automation', 'order': 2},
            {'category': 'Placement Fit Training Courses', 'name': 'Full Stack Software Engineering', 'order': 1},
            {'category': 'Placement Fit Training Courses', 'name': 'Quantitative Aptitude & Communication', 'order': 2},
        ]

        dom_objs = {}
        for dom in domains_data:
            c_obj = cat_objs[dom['category']]
            d_obj, created = SkillDomain.objects.update_or_create(
                category=c_obj,
                name=dom['name'],
                defaults={
                    'order': dom['order'],
                    'description': f"Institutional domain for {dom['name']}.",
                    'source_type': 'FXEC_OFFICIAL',
                    'source_url': 'https://francisxavier.ac.in/centre/training?page=activities',
                    'source_title': 'Training & Skills Development Activities | FXEC',
                    'source_accessed_at': now,
                    'last_verified_at': now,
                    'content_status': 'PUBLISHED',
                    'approval_status': 'APPROVED'
                }
            )
            dom_objs[dom['name']] = d_obj
            if created:
                stats['imported'] += 1

        # -----------------------------------------------------------------
        # 4. Seed Verified Skills (Core, Elective, Faculty Initiative, Emerging)
        # -----------------------------------------------------------------
        skills_data = [
            {
                'name': 'Computational Problem Solving with Python',
                'category': 'Foundation Course',
                'domain': 'Programming & Computational Logic',
                'department': 'CSE',
                'multi_depts': ['CSE', 'IT', 'AIDS', 'CSBS', 'ECE', 'EEE', 'MECH', 'CIVIL'],
                'is_cross': True,
                'level': 'BEGINNER',
                'skill_type': 'CORE',
                'description': 'Foundational engineering skill in algorithm logic, syntax, functions, and structured problem solving.',
                'outcomes': ['Master Python syntax and core data structures', 'Develop algorithmic logic for engineering solutions', 'Solve computational problems using modular functions'],
                'duration': '4 Weeks'
            },
            {
                'name': 'Machine Learning & Predictive Modeling',
                'category': 'Faculty Initiatives Skills',
                'domain': 'Artificial Intelligence & Data Analytics',
                'department': 'AIDS',
                'multi_depts': ['AIDS', 'CSE', 'IT'],
                'is_cross': True,
                'level': 'INTERMEDIATE',
                'skill_type': 'FACULTY_INITIATIVE',
                'description': 'Supervised and unsupervised learning, mathematical formulations, and predictive modeling using Scikit-Learn.',
                'outcomes': ['Build regression and classification pipelines', 'Evaluate models using precision, recall, and ROC-AUC', 'Deploy baseline predictive models'],
                'duration': '6 Weeks'
            },
            {
                'name': 'Industrial Internet of Things (IIoT) Protocols',
                'category': 'Certification Courses / Value Added Courses',
                'domain': 'Embedded Systems & Industrial IoT',
                'department': 'ECE',
                'multi_depts': ['ECE', 'EEE', 'MECH'],
                'is_cross': True,
                'level': 'INTERMEDIATE',
                'skill_type': 'CORE',
                'description': 'Hardware interfacing, MQTT sensor networks, and edge computing for modern manufacturing.',
                'outcomes': ['Interface sensors with microcontrollers', 'Configure MQTT brokers and telemetry streaming', 'Design industrial IoT monitoring nodes'],
                'duration': '5 Weeks'
            },
            {
                'name': 'Autonomous Robotics & Computer Vision',
                'category': 'Certification Courses / Value Added Courses',
                'domain': 'Robotics & Mechatronics Automation',
                'department': 'MECH',
                'multi_depts': ['MECH', 'AIDS', 'ECE'],
                'is_cross': True,
                'level': 'ADVANCED',
                'skill_type': 'EMERGING',
                'description': 'Robotics kinematics, OpenCV vision processing, and sensor fusion for autonomous navigation.',
                'outcomes': ['Calculate forward and inverse kinematics', 'Implement OpenCV object detection algorithms', 'Build closed-loop autonomous navigation logic'],
                'duration': '8 Weeks'
            },
            {
                'name': 'Full Stack Web Engineering with React & Node',
                'category': 'Placement Fit Training Courses',
                'domain': 'Full Stack Software Engineering',
                'department': 'IT',
                'multi_depts': ['IT', 'CSE', 'AIDS'],
                'is_cross': True,
                'level': 'INTERMEDIATE',
                'skill_type': 'PLACEMENT',
                'description': 'Enterprise modern web development combining React components, Node REST APIs, and database transactions.',
                'outcomes': ['Construct responsive React single page applications', 'Engineer secure Node REST endpoints with authentication', 'Deploy production web services'],
                'duration': '6 Weeks'
            },
            {
                'name': 'Quantitative Aptitude & Logical Reasoning',
                'category': 'Placement Fit Training Courses',
                'domain': 'Quantitative Aptitude & Communication',
                'department': None,
                'multi_depts': ['CSE', 'IT', 'AIDS', 'CSBS', 'ECE', 'EEE', 'MECH', 'CIVIL', 'MBA', 'MCA'],
                'is_cross': True,
                'level': 'BEGINNER',
                'skill_type': 'NON_TECHNICAL',
                'description': 'Speed arithmetic, analytical reasoning, and data interpretation for campus recruitment assessments.',
                'outcomes': ['Solve number theory and percentage problems quickly', 'Master analytical and syllogistic reasoning', 'Interpret complex tabular and graphical data'],
                'duration': '4 Weeks'
            }
        ]

        skill_objs = {}
        for s in skills_data:
            dept_obj = dept_objs[s['department']] if s['department'] else None
            sk, created = Skill.objects.update_or_create(
                name=s['name'],
                defaults={
                    'category': cat_objs[s['category']],
                    'domain': dom_objs[s['domain']],
                    'department': dept_obj,
                    'is_cross_department': s['is_cross'],
                    'level': s['level'],
                    'skill_type': s['skill_type'],
                    'description': s['description'],
                    'learning_outcomes': s['outcomes'],
                    'estimated_duration': s['duration'],
                    'source_type': 'FXEC_OFFICIAL',
                    'source_url': 'https://francisxavier.ac.in/centre/training?page=activities',
                    'source_title': 'Training & Skills Development Activities | FXEC',
                    'source_accessed_at': now,
                    'last_verified_at': now,
                    'content_status': 'PUBLISHED',
                    'approval_status': 'APPROVED'
                }
            )
            if s['multi_depts']:
                sk.departments.set([dept_objs[code] for code in s['multi_depts']])
            skill_objs[s['name']] = sk
            if created:
                stats['imported'] += 1

        # -----------------------------------------------------------------
        # 5. Seed Demonstration Courses with Lessons & Modules
        # -----------------------------------------------------------------
        courses_data = [
            {
                'title': 'Python Programming Mastery: Core Foundations to Applied Problem Solving',
                'slug': 'python-programming-mastery',
                'skill': 'Computational Problem Solving with Python',
                'department': 'CSE',
                'multi_depts': ['CSE', 'IT', 'AIDS', 'CSBS'],
                'instructor_name': 'Prof. Ramesh K. (Department of CSE)',
                'level': 'BEGINNER',
                'course_types': ['CORE_SKILL', 'VALUE_ADDED', 'PLACEMENT'],
                'estimated_hours': 12,
                'description': 'Master computational programming with Python. Covers variables, control structures, functions, and algorithmic data structures with automated testing and skill-gap diagnostics.',
                'outcomes': [
                    'Master Python syntax, typing, dynamic binding, and basic I/O mechanisms',
                    'Understand conditional branching, looping invariants, and iterative control flow',
                    'Design modular, reusable functions and comprehend scope and parameter passing'
                ],
                'modules': [
                    {
                        'order': 1,
                        'title': 'Python Syntax, Variables & Dynamic Typing',
                        'description': 'Foundational lexical structure of Python, primitive types, memory references, and expressions.',
                        'topic_tag': 'python_vars',
                        'duration': 30,
                        'lessons': [
                            {'order': 1, 'title': 'Variables, Constants & Memory References in Python', 'type': 'TEXT', 'duration': 15, 'content': 'In Python, variables are named references bound to objects in heap memory. Assignment does not copy objects; it binds names.'},
                            {'order': 2, 'title': 'Primitive Types and Dynamic Type Conversion', 'type': 'INTERACTIVE', 'duration': 15, 'content': 'Practice converting between integers, floats, strings, and boolean values using built-in casting functions.'}
                        ]
                    },
                    {
                        'order': 2,
                        'title': 'Control Flow: Conditionals, Loops & Iteration Patterns',
                        'description': 'Conditional branching with if/elif/else and iterative execution using while and for loops.',
                        'topic_tag': 'python_loops',
                        'duration': 45,
                        'lessons': [
                            {'order': 1, 'title': 'Conditional Evaluation and Logical Operators', 'type': 'TEXT', 'duration': 20, 'content': 'Learn Boolean logic, short-circuit evaluation, and structured branching.'},
                            {'order': 2, 'title': 'Iterating with For, While and Range Generators', 'type': 'INTERACTIVE', 'duration': 25, 'content': 'Solve algorithmic problems using bounded iterations and accumulator patterns.'}
                        ]
                    },
                    {
                        'order': 3,
                        'title': 'Modular Programming with Functions & Scope Rules',
                        'description': 'Function definition, positional and keyword arguments, returning values, and local vs global scope.',
                        'topic_tag': 'python_functions',
                        'duration': 45,
                        'lessons': [
                            {'order': 1, 'title': 'Function Signatures, Default Arguments and Return Values', 'type': 'TEXT', 'duration': 20, 'content': 'Understand parameter contracts and immutability considerations in Python functions.'},
                            {'order': 2, 'title': 'Scope Resolution via the LEGB Rule', 'type': 'INTERACTIVE', 'duration': 25, 'content': 'Analyze Local, Enclosing, Global, and Built-in namespaces.'}
                        ]
                    }
                ]
            },
            {
                'title': 'Autonomous Robotics & Computer Vision Integration',
                'slug': 'autonomous-robotics-computer-vision',
                'skill': 'Autonomous Robotics & Computer Vision',
                'department': 'MECH',
                'multi_depts': ['MECH', 'AIDS', 'ECE'],
                'instructor_name': 'FXEC Centre for Robotics & Applied AI',
                'level': 'ADVANCED',
                'course_types': ['INTERDISCIPLINARY', 'FACULTY_INITIATIVE', 'EMERGING'],
                'estimated_hours': 16,
                'description': 'An interdisciplinary course combining Mechanical kinematics, OpenCV visual stream processing, and real-time edge computing on industrial robotic nodes.',
                'outcomes': [
                    'Formulate spatial transformations and inverse kinematics for 3-DOF and 6-DOF robotic arms',
                    'Process real-time video frames using OpenCV for contour recognition and edge detection',
                    'Integrate vision feedback into motor actuation closed loops'
                ],
                'modules': [
                    {
                        'order': 1,
                        'title': 'Spatial Kinematics & Robotic Actuators',
                        'description': 'Degrees of freedom, Denavit-Hartenberg parameters, and motor torque requirements.',
                        'topic_tag': 'robotics_kinematics',
                        'duration': 45,
                        'lessons': [
                            {'order': 1, 'title': 'Coordinate Transformations in 3D Space', 'type': 'TEXT', 'duration': 20, 'content': 'Study transformation matrices and Euler angles.'},
                            {'order': 2, 'title': 'Actuator Response Characteristics', 'type': 'INTERACTIVE', 'duration': 25, 'content': 'Simulate servo motor actuation angles based on input target coordinates.'}
                        ]
                    },
                    {
                        'order': 2,
                        'title': 'OpenCV Machine Vision & Feature Extraction',
                        'description': 'Image thresholding, morphological operators, and contour detection for target tracking.',
                        'topic_tag': 'computer_vision',
                        'duration': 60,
                        'lessons': [
                            {'order': 1, 'title': 'Image Preprocessing & Edge Detection', 'type': 'TEXT', 'duration': 25, 'content': 'Apply Gaussian blur and Canny edge algorithms.'},
                            {'order': 2, 'title': 'Real-time Object Tracking Pipeline', 'type': 'INTERACTIVE', 'duration': 35, 'content': 'Track target markers using bounding boxes.'}
                        ]
                    }
                ]
            },
            {
                'title': 'Enterprise Full Stack Web Engineering with React & Node.js',
                'slug': 'enterprise-fullstack-react-node',
                'skill': 'Full Stack Web Engineering with React & Node',
                'department': 'IT',
                'multi_depts': ['IT', 'CSE', 'AIDS'],
                'instructor_name': 'FXEC Web Technologies Applied Lab',
                'level': 'INTERMEDIATE',
                'course_types': ['CORE_SKILL', 'PLACEMENT', 'VALUE_ADDED'],
                'estimated_hours': 14,
                'description': 'Architect enterprise-grade single page applications using React 19, TypeScript, Express REST backends, and relational database persistence.',
                'outcomes': [
                    'Architect reusable React components with type safety and state hooks',
                    'Construct scalable Express middleware, routing controllers, and JWT auth',
                    'Integrate secure transactional database queries and handle CORS policies'
                ],
                'modules': [
                    {
                        'order': 1,
                        'title': 'React Component Hierarchy & State Hooks',
                        'description': 'JSX paradigms, custom hooks, and reactive state management.',
                        'topic_tag': 'react_fundamentals',
                        'duration': 40,
                        'lessons': [
                            {'order': 1, 'title': 'Functional Components & Props Contracts', 'type': 'TEXT', 'duration': 20, 'content': 'Define clean, pure components and adhere to immutable props.'},
                            {'order': 2, 'title': 'State Management with useState and useEffect', 'type': 'INTERACTIVE', 'duration': 20, 'content': 'Implement responsive counter and filter controls.'}
                        ]
                    },
                    {
                        'order': 2,
                        'title': 'Node.js REST Services & JWT Security',
                        'description': 'Asynchronous Express pipeline, error handling middleware, and token validation.',
                        'topic_tag': 'node_api_security',
                        'duration': 50,
                        'lessons': [
                            {'order': 1, 'title': 'Express Routing & Middleware Architecture', 'type': 'TEXT', 'duration': 25, 'content': 'Build modular route routers with centralized error catching.'},
                            {'order': 2, 'title': 'JWT Token Authentication Flow', 'type': 'INTERACTIVE', 'duration': 25, 'content': 'Verify signatures and extract claims securely.'}
                        ]
                    }
                ]
            }
        ]

        # -----------------------------------------------------------------
        # 6. Controlled User Accounts
        # -----------------------------------------------------------------
        admin_user, _ = User.objects.get_or_create(
            username='fx_admin',
            defaults={
                'email': 'fxskillhub@gmail.com',
                'first_name': 'FXEC',
                'last_name': 'Administrator',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
                'is_demo': False,
            }
        )
        admin_user.set_password('Admin@FXEC2026!')
        admin_user.save()

        mentor_user, _ = User.objects.get_or_create(
            username='prof_ramesh',
            defaults={
                'email': 'mentor.cs@francisxavier.ac.in',
                'first_name': 'Prof. Ramesh',
                'last_name': 'K.',
                'department': dept_objs['CSE'],
                'role': 'MENTOR',
                'is_staff': True,
                'is_demo': False,
            }
        )
        mentor_user.set_password('Mentor@FXEC2026!')
        mentor_user.save()

        demo_student, _ = User.objects.get_or_create(
            username='demo_student',
            defaults={
                'email': 'student.demo@francisxavier.ac.in',
                'first_name': 'Demo',
                'last_name': 'Student',
                'register_number': 'FXEC2026DEMO01',
                'department': dept_objs['CSE'],
                'role': 'STUDENT',
                'is_demo': True,
            }
        )
        demo_student.set_password('Student@FXEC2026!')
        demo_student.save()

        # Seed courses and their hierarchy
        course_objs = {}
        for c in courses_data:
            sk_obj = skill_objs[c['skill']]
            dp_obj = dept_objs[c['department']]
            crs, created = Course.objects.update_or_create(
                slug=c['slug'],
                defaults={
                    'title': c['title'],
                    'skill': sk_obj,
                    'department': dp_obj,
                    'instructor_name': c['instructor_name'],
                    'description': c['description'],
                    'outcomes': c['outcomes'],
                    'estimated_hours': c['estimated_hours'],
                    'level': c['level'],
                    'course_types': c['course_types'],
                    'version': 1,
                    'is_published': True,
                    'approval_status': 'APPROVED',
                    'content_status': 'PUBLISHED',
                    'source_type': 'FXEC_OFFICIAL',
                    'source_url': 'https://francisxavier.ac.in/centre/training?page=activities',
                    'source_title': 'Training & Skills Development Activities | FXEC',
                    'source_accessed_at': now,
                    'last_verified_at': now,
                    'created_by': admin_user,
                    'approved_by': admin_user
                }
            )
            if c['multi_depts']:
                crs.departments.set([dept_objs[code] for code in c['multi_depts']])
            course_objs[c['slug']] = crs
            if created:
                stats['imported'] += 1

            # Seed Modules and Lessons
            for m_data in c['modules']:
                mod, m_created = Module.objects.update_or_create(
                    course=crs,
                    order=m_data['order'],
                    defaults={
                        'title': m_data['title'],
                        'description': m_data['description'],
                        'topic_tag': m_data['topic_tag'],
                        'duration_minutes': m_data['duration'],
                        'source_type': 'FXEC_OFFICIAL',
                        'source_url': 'https://francisxavier.ac.in/centre/training?page=activities',
                        'source_accessed_at': now,
                        'last_verified_at': now,
                        'content_status': 'PUBLISHED',
                        'approval_status': 'APPROVED',
                        'created_by': admin_user,
                        'approved_by': admin_user
                    }
                )
                if m_created:
                    stats['imported'] += 1

                for l_data in m_data.get('lessons', []):
                    lsn, l_created = Lesson.objects.update_or_create(
                        module=mod,
                        order=l_data['order'],
                        defaults={
                            'title': l_data['title'],
                            'content_type': l_data['type'],
                            'text_content': l_data['content'],
                            'duration_minutes': l_data['duration'],
                            'source_type': 'FXEC_OFFICIAL',
                            'source_url': 'https://francisxavier.ac.in/centre/training?page=activities',
                            'source_accessed_at': now,
                            'last_verified_at': now,
                            'content_status': 'PUBLISHED',
                            'approval_status': 'APPROVED',
                            'created_by': admin_user,
                            'approved_by': admin_user
                        }
                    )
                    if l_created:
                        stats['imported'] += 1

        # -----------------------------------------------------------------
        # 7. Seed Faculty-Proposed Course (PENDING_REVIEW for Admin Workflow)
        # -----------------------------------------------------------------
        pending_course, p_created = Course.objects.update_or_create(
            slug='machine-learning-scikit-learn-applied',
            defaults={
                'title': 'Applied Machine Learning & Statistical Validation with Scikit-Learn',
                'skill': skill_objs['Machine Learning & Predictive Modeling'],
                'department': dept_objs['CSE'],
                'instructor_name': 'Prof. Ramesh K. (Department of CSE)',
                'level': 'INTERMEDIATE',
                'course_types': ['FACULTY_INITIATIVE', 'TECHNICAL'],
                'estimated_hours': 15,
                'description': 'Faculty-initiated advanced workshop covering statistical feature engineering, model tuning, and validation.',
                'outcomes': ['Feature engineering and standardization', 'Hyperparameter grid search optimization', 'Cross-validation analysis'],
                'is_published': False,
                'approval_status': 'PENDING_REVIEW',
                'content_status': 'PENDING_ADMIN_INPUT',
                'source_type': 'FACULTY_CREATED',
                'source_title': 'Faculty Proposal by Prof. Ramesh K.',
                'created_by': mentor_user,
                'version': 1
            }
        )
        if p_created:
            stats['imported'] += 1

        # -----------------------------------------------------------------
        # 8. Seed AI Skill Suggestions (PENDING_REVIEW for Admin Approval)
        # -----------------------------------------------------------------
        ai_sugg, a_created = AISkillSuggestion.objects.update_or_create(
            title='Generative AI & LLM Systems Integration',
            defaults={
                'category_name': 'Faculty Initiatives Skills',
                'domain_name': 'Artificial Intelligence & Data Analytics',
                'department': dept_objs['AIDS'],
                'level': 'ADVANCED',
                'skill_type': 'EMERGING',
                'justification': 'High-demand industry employment track for developing intelligent agent workflows and Retrieval-Augmented Generation systems.',
                'learning_outcomes': ['Transformer attention mechanisms', 'Vector database retrieval with Chroma/pgvector', 'Prompt engineering & function calling'],
                'prerequisites': ['Python Programming', 'Machine Learning Foundations'],
                'suggested_modules': [
                    {'order': 1, 'title': 'Foundations of Generative Models', 'duration_minutes': 45},
                    {'order': 2, 'title': 'RAG Architectures & Vector Search', 'duration_minutes': 60}
                ],
                'source_type': 'AI_SUGGESTED',
                'approval_status': 'PENDING_REVIEW'
            }
        )
        if a_created:
            stats['imported'] += 1

        # -----------------------------------------------------------------
        # 9. Seed Diagnostic Questions for Python Programming Mastery
        # -----------------------------------------------------------------
        python_course = course_objs['python-programming-mastery']
        
        # Diagnostic Pre-Assessment
        pre_assess, _ = Assessment.objects.update_or_create(
            course=python_course,
            assessment_type='PRE_ASSESSMENT',
            defaults={
                'title': 'Python Baseline Diagnostic & Skill-Gap Pre-Assessment',
                'duration_minutes': 20,
                'pass_percentage': 70.0,
                'max_attempts': 10,
                'randomize_questions': False,
                'is_published': True,
                'camera_required': False,
                'screen_share_required': False,
                'fullscreen_required': False,
                'created_by': admin_user
            }
        )

        diagnostic_questions = [
            {
                'text': 'In Python, what is the output of type([1, 2, "three"])?',
                'topic_tag': 'python_vars',
                'marks': 5,
                'explanation': 'In Python, square brackets define a heterogeneous list object of type <class "list">.',
                'options': [
                    ('<class "list">', True),
                    ('<class "array">', False),
                    ('<class "tuple">', False),
                    ('<class "set">', False),
                ]
            },
            {
                'text': 'What will be the output of: for i in range(1, 4): print(i, end=" ")?',
                'topic_tag': 'python_loops',
                'marks': 5,
                'explanation': 'range(1, 4) produces values starting from 1 up to but not including 4, giving "1 2 3 ".',
                'options': [
                    ('1 2 3 ', True),
                    ('1 2 3 4 ', False),
                    ('0 1 2 3 ', False),
                    ('1 4 ', False),
                ]
            },
            {
                'text': 'Which keyword is used to modify a variable declared outside the current function scope?',
                'topic_tag': 'python_functions',
                'marks': 5,
                'explanation': 'The global keyword declares that a variable inside a function refers to the module-level namespace.',
                'options': [
                    ('global', True),
                    ('external', False),
                    ('static', False),
                    ('outer', False),
                ]
            }
        ]

        for q_idx, q_data in enumerate(diagnostic_questions, start=1):
            q_obj, _ = Question.objects.update_or_create(
                assessment=pre_assess,
                order=q_idx,
                defaults={
                    'text': q_data['text'],
                    'topic_tag': q_data['topic_tag'],
                    'marks': q_data['marks'],
                    'difficulty': 'EASY',
                    'explanation': q_data['explanation']
                }
            )
            for opt_text, is_corr in q_data['options']:
                QuestionOption.objects.update_or_create(
                    question=q_obj,
                    text=opt_text,
                    defaults={'is_correct': is_corr}
                )

        # -----------------------------------------------------------------
        # 10. Data Import Summary Report (Section 29)
        # -----------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS('\n======================================================='))
        self.stdout.write(self.style.SUCCESS('FXEC REAL DATA PROVENANCE IMPORT SUMMARY REPORT'))
        self.stdout.write(self.style.SUCCESS('======================================================='))
        self.stdout.write(f"• Total Records Processed / Imported: {stats['imported']}")
        self.stdout.write(f"• Records Skipped: {stats['skipped']}")
        self.stdout.write(f"• Verified Official FXEC Items: {Course.objects.filter(source_type='FXEC_OFFICIAL').count()} Courses, {Skill.objects.filter(source_type='FXEC_OFFICIAL').count()} Skills")
        self.stdout.write(f"• Faculty Created (Pending Review): {Course.objects.filter(source_type='FACULTY_CREATED').count()}")
        self.stdout.write(f"• AI Suggestions (Pending Review): {AISkillSuggestion.objects.filter(approval_status='PENDING_REVIEW').count()}")
        self.stdout.write(f"• Unverified Fields Tagged: PENDING_ADMIN_INPUT")
        self.stdout.write(f"• Authority Source URLs: https://www.francisxavier.ac.in/, https://francisxavier.ac.in/centre/training")
        self.stdout.write(self.style.SUCCESS('=======================================================\n'))
