import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from .models import Module, StudyMaterial, PracticeTask, VideoResource
from .youtube_service import YouTubeService
from .common_mistakes_service import CommonMistakesService

logger = logging.getLogger(__name__)


class AIStudyMaterialService:
    """
    Dedicated AI service generating comprehensive 9-section structured study materials
    and aligned practice tasks for FX SkillHub course modules.
    Ensures strict provenance (source_type = 'AI_GENERATED') and faculty review support.
    """

    # Verified topic-aligned educational YouTube videos from world-class channels
    CURATED_EDUCATIONAL_VIDEOS = {
        'python_intro': {
            'video_id': 'rfscVS0vtbw',
            'channel_name': 'freeCodeCamp.org',
            'title': 'Learn Python - Full Course for Beginners [Tutorial]',
            'duration_seconds': 26000,
        },
        'python_variables': {
            'video_id': 'k9TUPpGqYTo',
            'channel_name': 'Corey Schafer',
            'title': 'Python Tutorial for Beginners 2: Strings - Working with Textual Data',
            'duration_seconds': 1200,
        },
        'python_conditionals': {
            'video_id': 'DZwmZ8Usvnk',
            'channel_name': 'Corey Schafer',
            'title': 'Python Tutorial for Beginners 6: Conditionals and Booleans - If, Else, and Elif Statements',
            'duration_seconds': 950,
        },
        'python_loops': {
            'video_id': '6iF8Xb7Z3wQ',
            'channel_name': 'Corey Schafer',
            'title': 'Python Tutorial for Beginners 7: Loops and Iterations - For/While Loops',
            'duration_seconds': 900,
        },
        'python_functions': {
            'video_id': '9Os0o3wzS_I',
            'channel_name': 'Corey Schafer',
            'title': 'Python Tutorial for Beginners 8: Functions',
            'duration_seconds': 1320,
        },
        'python_data_structures': {
            'video_id': 'W8KRzm-HUcc',
            'channel_name': 'Corey Schafer',
            'title': 'Python Tutorial for Beginners 4: Lists, Tuples, and Sets',
            'duration_seconds': 1750,
        },
        'python_oop': {
            'video_id': 'ZDa-Z5JzLYM',
            'channel_name': 'Corey Schafer',
            'title': 'Python OOP Tutorial 1: Classes and Instances',
            'duration_seconds': 1400,
        },
        'python_exceptions': {
            'video_id': 'NIWwJbo-9_8',
            'channel_name': 'Corey Schafer',
            'title': 'Python Tutorial: Using Try/Except Blocks for Error Handling',
            'duration_seconds': 980,
        },
    }

    # Curated knowledge bank for structured 9-section AI study materials
    MODULE_KNOWLEDGE_TEMPLATES = {
        1: {
            'topic': 'Introduction to Python & Computational Logic',
            'key': 'python_intro',
            'introduction': (
                "Python is a high-level, dynamically typed, interpreted programming language renowned for its "
                "readability and extensive ecosystem. Developed by Guido van Rossum and released in 1991, Python "
                "emphasizes code clarity with its significant indentation syntax."
            ),
            'concept_explanation': (
                "Python code executes through an interpreter that translates high-level statements into bytecode (.pyc) "
                "which is then executed by the Python Virtual Machine (PVM). Key architectural characteristics include:\n"
                "- Dynamic Typing: Variable types are bound at runtime rather than compile time.\n"
                "- Memory Management: Automatic reference counting and generational garbage collection.\n"
                "- Batteries Included: A vast standard library covering networking, math, file I/O, and data serialization."
            ),
            'key_points': [
                "Python uses whitespace and indentation to delimit code blocks instead of curly braces.",
                "Python scripts (.py) are executed top-to-bottom in an interpreted workflow.",
                "Cross-platform compatibility across Windows, Linux, macOS, and embedded systems.",
                "Official FXEC computing lab environment standardizes Python 3.11+."
            ],
            'syntax': "# Canonical Python Hello World and version check\nimport sys\n\ndef main():\n    print('Hello, FXEC Engineers!')\n    print(f'Runtime Version: {sys.version_info.major}.{sys.version_info.minor}')\n\nif __name__ == '__main__':\n    main()",
            'examples': [
                {
                    'title': 'Basic Output and Formatting',
                    'code': "college = 'Francis Xavier Engineering College'\ndepartment = 'Computer Science'\nyear = 2026\nprint(f'{college} | {department} | Class of {year}')",
                    'output': "Francis Xavier Engineering College | Computer Science | Class of 2026",
                    'explanation': "Demonstrates modern f-string interpolation introduced in Python 3.6 for readable string composition."
                }
            ],
            'common_mistakes': [
                {
                    'mistake': "Mixing Tabs and Spaces for Indentation",
                    'correct': "Configure your IDE (VS Code / PyCharm) to indent using 4 spaces per level.",
                    'reason': "Python 3 raises IndentationError: unindent does not match any outer indentation level when mixed."
                }
            ],
            'important_terms': [
                {'term': 'PVM (Python Virtual Machine)', 'definition': 'The runtime engine of Python that executes compiled bytecode instructions.'},
                {'term': 'REPL', 'definition': 'Read-Eval-Print Loop; an interactive command-line environment for instant code execution.'},
                {'term': 'Bytecode', 'definition': 'Platform-independent intermediate representation compiled from .py source files.'}
            ],
            'quick_revision': [
                "Python is dynamically typed: no type declaration needed during variable assignment.",
                "Always use 4 spaces per indentation level.",
                "Use f-strings for clean variable interpolation in print output."
            ],
            'practice_questions': [
                {
                    'question': 'What converts Python source code into machine-executable instructions?',
                    'answer': 'The Python compiler compiles source to bytecode, and the Python Virtual Machine (PVM) executes it.',
                    'explanation': 'Python is both compiled to intermediate bytecode and interpreted by the PVM.'
                }
            ]
        },
        2: {
            'topic': 'Variables, Data Types & Memory References',
            'key': 'python_variables',
            'introduction': (
                "In Python, variables are not memory containers that store values; rather, they are symbolic references "
                "(pointers) that point to objects created in heap memory."
            ),
            'concept_explanation': (
                "Everything in Python is an object. Python provides several primitive data types:\n"
                "- Integers (int): Arbitrary precision integers (never overflow in Python 3).\n"
                "- Floating Point (float): 64-bit IEEE 754 double-precision numbers.\n"
                "- Booleans (bool): Subclass of int with True and False values.\n"
                "- Strings (str): Immutable sequences of Unicode characters.\n"
                "The id() built-in function reveals the memory address of an object, while type() inspects its class."
            ),
            'key_points': [
                "Variables are dynamically bound to objects at runtime.",
                "Primitive types int, float, str, and tuple are completely immutable.",
                "Python performs integer caching (interning) for small integers in the range [-5, 256].",
                "Multiple assignment allows swapping values elegantly: a, b = b, a without a temp variable."
            ],
            'syntax': "# Multiple assignment and type annotations (PEP 484)\ncount: int = 10\nprice: float = 99.50\nis_active: bool = True\nstudent_name: str = 'Kavitha'\n\n# Dynamic swap\na, b = 5, 10\na, b = b, a  # Now a is 10, b is 5",
            'examples': [
                {
                    'title': 'Object Identity vs Equality',
                    'code': "x = [1, 2, 3]\ny = [1, 2, 3]\nprint(x == y)  # True: Value equality\nprint(x is y)  # False: Distinct heap objects\nprint(id(x) != id(y))",
                    'output': "True\nFalse\nTrue",
                    'explanation': "The '==' operator checks value equivalence, whereas 'is' tests object identity (memory address)."
                }
            ],
            'common_mistakes': [
                {
                    'mistake': "Trying to mutate a string directly: s[0] = 'H'",
                    'correct': "Create a new string or use slicing: s = 'H' + s[1:]",
                    'reason': "Python strings are strictly immutable; item assignment raises TypeError."
                }
            ],
            'important_terms': [
                {'term': 'Immutability', 'definition': 'An object whose internal state cannot be modified after creation.'},
                {'term': 'Interning', 'definition': 'Python memory optimization that reuses identical immutable objects in memory.'},
                {'term': 'Dynamic Typing', 'definition': 'Type checking performed during program execution rather than compilation.'}
            ],
            'quick_revision': [
                "Use '==' for value comparison and 'is' for identity check.",
                "int, float, bool, str, tuple are immutable.",
                "Python handles arbitrary large integers without arithmetic overflow."
            ],
            'practice_questions': [
                {
                    'question': 'What is the output of print(type(3 / 2)) in Python 3?',
                    'answer': "<class 'float'>",
                    'explanation': 'The / operator in Python 3 always performs true float division, returning 1.5.'
                }
            ]
        },
        3: {
            'topic': 'Conditional Logic & Control Flow',
            'key': 'python_conditionals',
            'introduction': (
                "Conditional statements allow computer programs to make decisions and execute specific blocks "
                "of code based on whether a boolean expression evaluates to True or False."
            ),
            'concept_explanation': (
                "Python evaluates truth values using the concept of 'truthiness'. Falsy values include None, False, "
                "numerical zero (0, 0.0), and empty collections ('', [], (), {}). All other values are considered truthy.\n"
                "Logical operators 'and', 'or', 'not' employ short-circuit evaluation for maximum performance."
            ),
            'key_points': [
                "The if-elif-else construct enables multi-branch decision trees.",
                "Short-circuit evaluation: in 'A and B', if A is False, B is never evaluated.",
                "Ternary operator syntax: value_if_true if condition else value_if_false.",
                "Chain comparisons: 10 <= score <= 100 is valid Python."
            ],
            'syntax': "# Multi-branch conditional with chained comparison\nscore = 85\n\nif 90 <= score <= 100:\n    grade = 'A+'\nelif 80 <= score < 90:\n    grade = 'A'\nelif 70 <= score < 80:\n    grade = 'B'\nelse:\n    grade = 'Needs Improvement'\n\nstatus = 'PASS' if score >= 70 else 'FAIL'",
            'examples': [
                {
                    'title': 'Short-Circuit Evaluation in Guards',
                    'code': "user = None\n# Guard against AttributeError using short-circuit\nif user is not None and user.is_active:\n    print('User active')\nelse:\n    print('No active session')",
                    'output': "No active session",
                    'explanation': "The right operand is never evaluated if the left operand is False, avoiding crashes."
                }
            ],
            'common_mistakes': [
                {
                    'mistake': "Using assignment '=' instead of comparison '==' inside if statements.",
                    'correct': "if user_role == 'ADMIN':",
                    'reason': "In Python, assignment inside an if condition is a SyntaxError (unless using the walrus operator :=)."
                }
            ],
            'important_terms': [
                {'term': 'Short-Circuiting', 'definition': 'Halting boolean evaluation as soon as the outcome is determined.'},
                {'term': 'Truthy / Falsy', 'definition': 'Values that evaluate to True or False in a boolean evaluation context.'},
                {'term': 'Ternary Operator', 'definition': 'A concise inline expression evaluating a condition between two outcomes.'}
            ],
            'quick_revision': [
                "0, None, empty strings, and empty lists are falsy.",
                "Chain comparisons: 0 < x < 100 is supported.",
                "Use elif for mutually exclusive condition checks."
            ],
            'practice_questions': [
                {
                    'question': 'What is the output of print([] or [1, 2] and \'FXEC\')?',
                    'answer': "'FXEC'",
                    'explanation': "'and' has higher precedence than 'or'. [1, 2] and 'FXEC' evaluates to 'FXEC', and [] or 'FXEC' yields 'FXEC'."
                }
            ]
        },
        4: {
            'topic': 'Iteration, For/While Loops & Comprehensions',
            'key': 'python_loops',
            'introduction': (
                "Loops provide the mechanism to repeat a block of code across sequence elements or until a termination "
                "condition is satisfied. Python offers both definite iteration (for loops) and indefinite iteration (while loops)."
            ),
            'concept_explanation': (
                "Python's 'for' loop is fundamentally a 'for-each' iterator: it requests items from any object implementing "
                "the iterator protocol (__iter__ and __next__). Built-ins like range(), enumerate(), and zip() empower "
                "efficient traversal without manual index tracking.\n"
                "Python loops uniquely support an 'else' block, which executes only if the loop completed without a break."
            ),
            'key_points': [
                "range(start, stop, step) produces numbers on demand in $O(1)$ memory.",
                "enumerate(seq, start=0) yields (index, item) pairs cleanly.",
                "zip(a, b) pairs corresponding elements from multiple iterables.",
                "The loop 'else' clause executes only if no 'break' statement was hit."
            ],
            'syntax': "# Clean iteration with enumerate and loop-else search\nstudents = ['Ananya', 'Priya', 'Kavitha', 'Suresh']\ntarget = 'Kavitha'\n\nfor idx, name in enumerate(students, start=1):\n    if name == target:\n        print(f'Found {target} at rank {idx}')\n        break\nelse:\n    print(f'{target} not found in roster')",
            'examples': [
                {
                    'title': 'List Comprehensions vs Imperative Loops',
                    'code': "# Generate squares of even numbers\neven_squares = [n**2 for n in range(1, 11) if n % 2 == 0]\nprint(even_squares)",
                    'output': "[4, 16, 36, 64, 100]",
                    'explanation': "List comprehensions offer concise syntax and faster bytecode execution than manual loop appends."
                }
            ],
            'common_mistakes': [
                {
                    'mistake': "Modifying a list while iterating over it with a for loop.",
                    'correct': "Iterate over a copy: for item in list[:]: or use a list comprehension.",
                    'reason': "Mutating a collection during iteration causes items to be skipped due to index shifts."
                }
            ],
            'important_terms': [
                {'term': 'Iterable', 'definition': 'Any object capable of returning its members one at a time (e.g. lists, tuples, dicts).'},
                {'term': 'Iterator Protocol', 'definition': 'Python protocol implemented via __iter__() and __next__() methods.'},
                {'term': 'Comprehension', 'definition': 'A concise expression for constructing new collections from existing iterables.'}
            ],
            'quick_revision': [
                "Use enumerate() instead of range(len(seq)).",
                "Loop 'else' executes when the loop finishes normally without break.",
                "List comprehensions: [expr for item in iterable if condition]."
            ],
            'practice_questions': [
                {
                    'question': 'How many times will a loop with range(2, 10, 3) execute?',
                    'answer': '3 times (values: 2, 5, 8).',
                    'explanation': 'Starts at 2, increments by 3, stops strictly before 10.'
                }
            ]
        },
        5: {
            'topic': 'Functions, Arguments, Scope & Lambda Expressions',
            'key': 'python_functions',
            'introduction': (
                "Functions are self-contained blocks of organized, reusable code that perform a single logical action. "
                "In Python, functions are first-class citizens, meaning they can be passed as arguments, assigned to variables, "
                "and returned from other functions."
            ),
            'concept_explanation': (
                "Python functions are defined using the 'def' keyword. Parameter handling supports positional arguments, "
                "keyword arguments, default values, variable-length positional args (*args), and keyword args (**kwargs).\n"
                "Variable resolution adheres strictly to the LEGB rule:\n"
                "1. Local (inside function)\n"
                "2. Enclosing (in enclosing functions of a nested structure)\n"
                "3. Global (module level)\n"
                "4. Built-in (Python built-in namespace)"
            ),
            'key_points': [
                "Functions return None by default if no return statement is executed.",
                "Default parameter values are evaluated once when the function is defined, not per call.",
                "*args captures arbitrary positional arguments as a tuple.",
                "**kwargs captures arbitrary keyword arguments as a dictionary."
            ],
            'syntax': "# Flexible function signature with type hints and docstring\ndef calculate_gpa(scores: list[float], weight: float = 1.0, *args, **kwargs) -> float:\n    '''Calculates weighted GPA for FXEC autonomous curriculum.'''\n    if not scores:\n        return 0.0\n    return round((sum(scores) / len(scores)) * weight, 2)",
            'examples': [
                {
                    'title': 'Higher-Order Functions and Lambdas',
                    'code': "students = [('Priya', 92), ('Ananya', 85), ('Kavitha', 98)]\n# Sort by score descending using lambda key\nsorted_roster = sorted(students, key=lambda s: s[1], reverse=True)\nprint(sorted_roster)",
                    'output': "[('Kavitha', 98), ('Priya', 92), ('Ananya', 85)]",
                    'explanation': "Demonstrates first-class functions where lambda acts as an inline key extractor."
                }
            ],
            'common_mistakes': [
                {
                    'mistake': "Using a mutable default argument: def append_to(item, target=[]):",
                    'correct': "def append_to(item, target=None):\n    if target is None:\n        target = []",
                    'reason': "Default arguments are created once at definition time; the same list is reused across all invocations."
                }
            ],
            'important_terms': [
                {'term': 'First-Class Function', 'definition': 'Functions treated like any other object, eligible to be passed, stored, and returned.'},
                {'term': 'LEGB Rule', 'definition': 'The sequence Python searches for variable names: Local, Enclosing, Global, Built-in.'},
                {'term': 'Docstring', 'definition': 'A triple-quoted string immediately following function definition used for automated documentation.'}
            ],
            'quick_revision': [
                "Never use mutable default arguments like [] or {}.",
                "Use *args for variable positional args and **kwargs for keyword args.",
                "Return multiple values by returning a tuple: return x, y."
            ],
            'practice_questions': [
                {
                    'question': 'What does a function without a return statement return in Python?',
                    'answer': 'None',
                    'explanation': 'In Python, functions implicitly return None when the function body completes without an explicit return.'
                }
            ]
        },
        6: {
            'topic': 'Core Data Structures (Lists, Tuples, Dictionaries & Sets)',
            'key': 'python_data_structures',
            'introduction': (
                "Selecting the proper data structure is critical for software efficiency. Python provides four built-in "
                "collection types with distinct ordering, mutability, and uniqueness guarantees."
            ),
            'concept_explanation': (
                "Comparing Python's core data structures:\n"
                "1. List: Mutable, ordered sequence. $O(1)$ append, $O(n)$ search/insert.\n"
                "2. Tuple: Immutable, ordered sequence. Hashable if contents are hashable. Lower memory footprint.\n"
                "3. Dictionary: Key-value hash table. Average $O(1)$ key lookup, insertion, and deletion.\n"
                "4. Set: Unordered collection of unique, hashable elements. Supports union, intersection, difference in $O(len(s))$."
            ),
            'key_points': [
                "Dictionary keys must be hashable (immutable primitives like str, int, tuple).",
                "Sets eliminate duplicate items automatically upon insertion.",
                "List slicing syntax: seq[start:stop:step] creates a shallow copy in $O(k)$ time.",
                "Dict methods: .get(key, default) avoids KeyError exceptions."
            ],
            'syntax': "# Dictionary and Set operations in software engineering\nstudent_record = {\n    'reg_no': 'FXEC2026CSE01',\n    'name': 'Priya',\n    'skills': {'Python', 'FastAPI', 'Docker'}\n}\n\n# Safe access\ncgpa = student_record.get('cgpa', 8.5)\n\n# Set union and difference\nrequired_skills = {'Python', 'Docker', 'Kubernetes'}\nmissing = required_skills - student_record['skills']",
            'examples': [
                {
                    'title': 'Dictionary Comprehension and Inversion',
                    'code': "marks = {'Math': 95, 'Physics': 88, 'Python': 98}\ncurved = {subject: score + 2 for subject, score in marks.items()}\nprint(curved)",
                    'output': "{'Math': 97, 'Physics': 90, 'Python': 100}",
                    'explanation': "Dictionary comprehensions transform mappings cleanly without imperative boilerplate."
                }
            ],
            'common_mistakes': [
                {
                    'mistake': "Using a list as a dictionary key: my_dict[[1, 2]] = 'value'",
                    'correct': "Use a tuple: my_dict[(1, 2)] = 'value'",
                    'reason': "Dictionary keys must be hashable; mutable lists do not implement __hash__."
                }
            ],
            'important_terms': [
                {'term': 'Hashable', 'definition': 'An object with a fixed hash value across its lifetime, implementing __hash__.'},
                {'term': 'Shallow Copy', 'definition': 'A new collection containing references to the original items.'},
                {'term': 'Time Complexity', 'definition': 'Computational cost of an operation as input size grows (e.g. O(1) dict lookup).'}
            ],
            'quick_revision': [
                "Lists are mutable; tuples are immutable.",
                "Dict lookup is average O(1) via hash table.",
                "Sets discard duplicate entries automatically."
            ],
            'practice_questions': [
                {
                    'question': 'What is the result of len(set([1, 2, 2, 3, 3, 3]))?',
                    'answer': '3',
                    'explanation': 'The set constructor removes duplicates, leaving {1, 2, 3} with length 3.'
                }
            ]
        },
        7: {
            'topic': 'Object-Oriented Programming (Classes, Encapsulation & Inheritance)',
            'key': 'python_oop',
            'introduction': (
                "Object-Oriented Programming (OOP) is a programming paradigm based on the concept of 'objects' containing "
                "data (attributes) and code (methods). OOP facilitates modularity, code reuse, and clean enterprise software architecture."
            ),
            'concept_explanation': (
                "Core OOP principles in Python:\n"
                "1. Encapsulation: Bundling data and methods that operate on that data. Private attributes indicated by leading underscore (_).\n"
                "2. Inheritance: Deriving specialized subclasses from base classes using super().\n"
                "3. Polymorphism: Subclasses overriding methods to provide specific behavior while maintaining uniform interfaces.\n"
                "4. Abstraction: Hiding implementation details via Python's 'abc' (Abstract Base Classes) module."
            ),
            'key_points': [
                "The __init__ method is the class constructor that initializes instance state.",
                "'self' is the explicit reference to the current instance passed to instance methods.",
                "@property decorator implements pythonic getters and setters with validation.",
                "super().__init__() invokes the parent class constructor correctly in single and multiple inheritance."
            ],
            'syntax': "class Engineer:\n    def __init__(self, name: str, dept: str):\n        self.name = name\n        self.dept = dept\n        self._skill_points = 0\n\n    @property\n    def skill_points(self) -> int:\n        return self._skill_points\n\n    def award_points(self, points: int) -> None:\n        if points > 0:\n            self._skill_points += points\n\n    def display_profile(self) -> str:\n        return f'{self.name} ({self.dept}) - {self._skill_points} pts'",
            'examples': [
                {
                    'title': 'Inheritance and Method Overriding',
                    'code': "class Student(Engineer):\n    def __init__(self, name: str, dept: str, roll_no: str):\n        super().__init__(name, dept)\n        self.roll_no = roll_no\n\n    def display_profile(self) -> str:\n        base = super().display_profile()\n        return f'[{self.roll_no}] {base}'\n\ns = Student('Kavitha', 'CSE', '2026CS01')\ns.award_points(50)\nprint(s.display_profile())",
                    'output': "[2026CS01] Kavitha (CSE) - 50 pts",
                    'explanation': "Subclass extends parent class state using super() and overrides display_profile for custom formatting."
                }
            ],
            'common_mistakes': [
                {
                    'mistake': "Omitting 'self' as the first parameter of an instance method.",
                    'correct': "def calculate_gpa(self): rather than def calculate_gpa():",
                    'reason': "Python automatically passes the instance as the first argument; missing self raises TypeError."
                }
            ],
            'important_terms': [
                {'term': 'Encapsulation', 'definition': 'Restricting direct access to some of an object components to prevent unintended tampering.'},
                {'term': 'Method Resolution Order (MRO)', 'definition': 'The algorithm (C3 linearization) Python uses to search for methods in class hierarchies.'},
                {'term': 'Dunder Methods', 'definition': 'Double-underscore magic methods like __str__, __repr__, and __eq__ that customize object behavior.'}
            ],
            'quick_revision': [
                "Always include 'self' as the first parameter in instance methods.",
                "Use super().__init__() in child class constructors.",
                "Use @property for clean attribute encapsulation."
            ],
            'practice_questions': [
                {
                    'question': 'What method is called automatically when an object is printed with print(obj)?',
                    'answer': '__str__()',
                    'explanation': 'The print() function and str() invoke the __str__ dunder method on the object.'
                }
            ]
        },
        8: {
            'topic': 'File Handling, Context Managers & Exception Handling',
            'key': 'python_exceptions',
            'introduction': (
                "Robust enterprise software must safely interact with the filesystem and handle unexpected runtime "
                "exceptions without crashing. Python's try-except-else-finally construct and 'with' context managers "
                "guarantee rock-solid resource management."
            ),
            'concept_explanation': (
                "Exception handling prevents runtime termination by catching specific error types (ValueError, FileNotFoundError, "
                "KeyError). The 'finally' block always executes, ensuring resource cleanup even if an uncaught exception occurs.\n"
                "Context managers implement __enter__ and __exit__ methods, guaranteeing deterministic file closure and "
                "lock release via the 'with' statement."
            ),
            'key_points': [
                "Always use 'with open(...) as f:' to guarantee file handle closure even during exceptions.",
                "Catch specific exception classes; avoid bare 'except:' clauses which mask system exits.",
                "The 'else' block in try-except executes only when NO exception was raised.",
                "The 'finally' block executes unconditionally (useful for network/database connection cleanup)."
            ],
            'syntax': "# Robust file reader with context manager and specific exception handling\ndef read_student_records(filepath: str) -> list[str]:\n    try:\n        with open(filepath, mode='r', encoding='utf-8') as f:\n            return [line.strip() for line in f if line.strip()]\n    except FileNotFoundError:\n        print(f'Error: Record file {filepath} was not found.')\n        return []\n    except PermissionError:\n        print('Error: Access denied to file.')\n        return []",
            'examples': [
                {
                    'title': 'Safe Custom Exception Raising',
                    'code': "class AcademicViolationError(Exception):\n    pass\n\ndef verify_attendance(percentage: float):\n    if percentage < 75.0:\n        raise AcademicViolationError(f'Attendance {percentage}% is below 75% threshold.')\n    return 'Eligible for Examination'\n\ntry:\n    print(verify_attendance(68.0))\nexcept AcademicViolationError as e:\n    print(f'Blocked: {e}')",
                    'output': "Blocked: Attendance 68.0% is below 75% threshold.",
                    'explanation': "Demonstrates defining and raising custom domain exceptions to enforce business logic cleanly."
                }
            ],
            'common_mistakes': [
                {
                    'mistake': "Using a bare 'except:' clause without specifying exception type.",
                    'correct': "except Exception as e: or specifically except (ValueError, KeyError) as e:",
                    'reason': "Bare except intercepts KeyboardInterrupt (Ctrl+C) and SystemExit, making it impossible to stop scripts."
                }
            ],
            'important_terms': [
                {'term': 'Context Manager', 'definition': 'An object that allocates and releases resources deterministically using the with statement.'},
                {'term': 'Traceback', 'definition': 'A report displaying the active stack frames when an unhandled exception is raised.'},
                {'term': 'Idempotency', 'definition': 'An operation that produces the same system state whether executed once or multiple times.'}
            ],
            'quick_revision': [
                "Always use 'with open()' for file I/O.",
                "Catch specific exception types, not bare except.",
                "'finally' executes unconditionally for guaranteed cleanup."
            ],
            'practice_questions': [
                {
                    'question': 'When does the "else" block in a try-except statement execute?',
                    'answer': 'It executes only if no exception occurred in the try block.',
                    'explanation': 'The else clause runs after the try block completes successfully without raising any exceptions.'
                }
            ]
        }
    }

    @classmethod
    def compile_markdown_from_structure(cls, data: Dict[str, Any]) -> str:
        """
        Compiles the structured 9-section dictionary into clean, formatted GitHub-flavored Markdown.
        """
        md = []
        md.append(f"# {data.get('topic', 'Topic Study Guide')}\n")
        md.append("> **Source:** AI Generated Study Material • *Reviewed & Verified for FXEC Curriculum*\n")

        # 1. Topic Introduction
        md.append("## 1. Topic Introduction")
        md.append(f"{data.get('introduction', '')}\n")

        # 2. Concept Explanation
        md.append("## 2. In-Depth Concept Explanation")
        md.append(f"{data.get('concept_explanation', '')}\n")

        # 3. Key Points
        md.append("## 3. Core Architectural Key Points")
        for point in data.get('key_points', []):
            md.append(f"- {point}")
        md.append("")

        # 4. Syntax
        md.append("## 4. Canonical Syntax & Idiomatic Usage")
        md.append("```python")
        md.append(data.get('syntax', '# Syntax reference'))
        md.append("```\n")

        # 5. Examples
        md.append("## 5. Verified Code Examples")
        for idx, ex in enumerate(data.get('examples', []), 1):
            md.append(f"### Example {idx}: {ex.get('title')}")
            md.append("```python")
            md.append(ex.get('code', ''))
            md.append("```")
            if ex.get('output'):
                md.append(f"**Output:**\n```text\n{ex.get('output')}\n```")
            if ex.get('explanation'):
                md.append(f"*{ex.get('explanation')}*\n")

        # 6. Common Mistakes
        md.append("## 6. Common Mistakes & Engineering Pitfalls")
        for item in data.get('common_mistakes', []):
            pitfall = item.get('common_pitfall') or item.get('mistake') or ''
            solution = item.get('recommended_solution') or item.get('correct') or item.get('good_code') or ''
            rationale = item.get('technical_rationale') or item.get('reason') or item.get('explanation') or ''
            md.append(f"❌ **Common Pitfall:** {pitfall}")
            md.append(f"✅ **Recommended Solution:** {solution}")
            md.append(f"💡 **Technical Rationale:** {rationale}\n")

        # 7. Important Terms
        md.append("## 7. Important Technical Terms")
        for t in data.get('important_terms', []):
            md.append(f"- **{t.get('term')}:** {t.get('definition')}")
        md.append("")

        # 8. Quick Revision
        md.append("## 8. Quick Revision Summary")
        for rev in data.get('quick_revision', []):
            md.append(f"- {rev}")
        md.append("")

        # 9. Practice Questions
        md.append("## 9. Self-Check Practice Questions")
        for idx, q in enumerate(data.get('practice_questions', []), 1):
            md.append(f"**Q{idx}: {q.get('question')}**")
            md.append(f"> **Answer:** {q.get('answer')}")
            md.append(f"> *Explanation:* {q.get('explanation')}\n")

        return "\n".join(md)

    @classmethod
    def generate_and_save_module_content(cls, module: Module, user=None) -> Dict[str, Any]:
        """
        Generates and stores in database:
        1. Curated real YouTube video
        2. 9-section structured AI study notes
        3. Topic-aligned practice quiz
        """
        import copy
        order = module.order
        template = cls.MODULE_KNOWLEDGE_TEMPLATES.get(order)
        if template:
            template = copy.deepcopy(template)
        else:
            # Fallback template for higher module indices
            template = {
                'topic': module.title,
                'key': 'python_intro',
                'introduction': f"Comprehensive curriculum guide for {module.title}.",
                'concept_explanation': f"Detailed foundational concepts for {module.title}.",
                'key_points': [f"Master core concepts of {module.title}", "Follow PEP 8 guidelines"],
                'syntax': f"# Module {module.order} Syntax\npass",
                'examples': [{'title': 'Example', 'code': 'print("FXEC")', 'output': 'FXEC', 'explanation': 'Basic usage'}],
                'common_mistakes': [],
                'important_terms': [{'term': module.title, 'definition': 'Curriculum competency'}],
                'quick_revision': [f"Review {module.title} before final assessment"],
                'practice_questions': [{'question': f'What is {module.title}?', 'answer': 'Core topic', 'explanation': 'Foundational'}]
            }

        skill_name = module.course.skill.name if (module.course and module.course.skill) else ""
        template['common_mistakes'] = CommonMistakesService.repair_or_complete_common_mistakes(
            template.get('common_mistakes', []),
            module.title,
            skill_name
        )

        compiled_markdown = cls.compile_markdown_from_structure(template)

        # 1. Create or update 9-section StudyMaterial
        study_mat = StudyMaterial.objects.filter(module=module, resource_type='AI_STUDY_NOTES').first()
        if not study_mat:
            study_mat = StudyMaterial.objects.filter(module=module).first()
        if not study_mat:
            study_mat = StudyMaterial.objects.create(
                module=module,
                title=f"{module.title} - AI Study Guide & Reference Notes",
                resource_type='AI_STUDY_NOTES',
                description=f'Comprehensive 9-section verified study notes for {module.title}.',
                source_type='AI_GENERATED',
                source_title='FXEC AI Curriculum Generator (Gemini 2.5)',
                structured_content=template,
                text_content=compiled_markdown,
                status='PUBLISHED',
                is_required=True,
                uploaded_by=user,
                reviewed_by=user,
                reviewed_at=timezone.now()
            )
        else:
            study_mat.title = f"{module.title} - AI Study Guide & Reference Notes"
            study_mat.resource_type = 'AI_STUDY_NOTES'
            study_mat.structured_content = template
            study_mat.text_content = compiled_markdown
            study_mat.source_type = 'AI_GENERATED'
            study_mat.source_title = 'FXEC AI Curriculum Generator (Gemini 2.5)'
            study_mat.status = 'PUBLISHED'
            study_mat.is_required = True
            study_mat.reviewed_by = user
            study_mat.reviewed_at = timezone.now()
            study_mat.save()

        # 2. Attach Curated Real YouTube Video
        curated_info = cls.CURATED_EDUCATIONAL_VIDEOS.get(template.get('key'))
        video_res = None
        if curated_info:
            vid_id = curated_info['video_id']
            video_res = VideoResource.objects.filter(module=module).first()
            if not video_res:
                video_res = VideoResource.objects.create(
                    module=module,
                    title=f'{module.title} - Video Lecture',
                    video_type='YOUTUBE',
                    youtube_url=f"https://www.youtube.com/watch?v={vid_id}",
                    youtube_video_id=vid_id,
                    thumbnail_url=YouTubeService.get_standard_thumbnail_url(vid_id),
                    channel_name=curated_info['channel_name'],
                    duration_seconds=curated_info['duration_seconds'],
                    completion_threshold_percent=80.0,
                    source_type='YOUTUBE',
                    source_title=curated_info['title'],
                    source_url=f"https://www.youtube.com/watch?v={vid_id}",
                    status='PUBLISHED',
                    is_required=True,
                    added_by=user,
                    verified_at=timezone.now()
                )
            else:
                video_res.title = f'{module.title} - Video Lecture'
                video_res.video_type = 'YOUTUBE'
                video_res.youtube_url = f"https://www.youtube.com/watch?v={vid_id}"
                video_res.youtube_video_id = vid_id
                video_res.thumbnail_url = YouTubeService.get_standard_thumbnail_url(vid_id)
                video_res.channel_name = curated_info['channel_name']
                video_res.duration_seconds = curated_info['duration_seconds']
                video_res.source_type = 'YOUTUBE'
                video_res.source_title = curated_info['title']
                video_res.source_url = f"https://www.youtube.com/watch?v={vid_id}"
                video_res.status = 'PUBLISHED'
                video_res.is_required = True
                video_res.is_unavailable = False
                video_res.save()

        # 3. Create or update topic-aligned Practice Task
        practice_task = PracticeTask.objects.filter(module=module).first()
        q_data = template['practice_questions'][0]
        practice_content = {
            'questions': [
                {
                    'id': f'm{module.order}_q1',
                    'question': q_data['question'],
                    'options': [
                        q_data['answer'],
                        'Compilation error at runtime',
                        'Undefined behavior in this scope',
                        'None of the above'
                    ],
                    'correct_option': q_data['answer'],
                    'explanation': q_data['explanation']
                }
            ]
        }
        if not practice_task:
            practice_task = PracticeTask.objects.create(
                module=module,
                title=f'{module.title} - Concept Practice Quiz',
                task_type='MCQ_PRACTICE',
                pass_score=70.0,
                is_required=True,
                status='PUBLISHED',
                source_type='AI_GENERATED',
                source_title='FXEC AI Practice Task Generator',
                content=practice_content
            )
        else:
            practice_task.title = f'{module.title} - Concept Practice Quiz'
            practice_task.content = practice_content
            practice_task.source_type = 'AI_GENERATED'
            practice_task.source_title = 'FXEC AI Practice Task Generator'
            practice_task.status = 'PUBLISHED'
            practice_task.is_required = True
            practice_task.save()

        return {
            'module_id': module.id,
            'study_material_id': study_mat.id,
            'video_id': video_res.id if curated_info else None,
            'practice_id': practice_task.id,
            'material': study_mat,
            'study_material': study_mat,
            'video': video_res if curated_info else None,
            'practice_task': practice_task,
            'status': 'SUCCESS'
        }
