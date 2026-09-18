import re
from typing import List, Dict, Any, Tuple, Optional

class CommonMistakesService:
    """
    Authoritative service for generating, validating, and repairing 
    Common Mistakes & Best Practice Fixes across all courses and modules.
    Ensures every item strictly adheres to:
    - common_pitfall (WHAT IS WRONG)
    - recommended_solution (WHAT TO DO)
    - technical_rationale (WHY IT WORKS / WHY IT MATTERS)
    """

    DISALLOWED_PLACEHOLDERS = {
        "", "null", "none", "n/a", "not available", "coming soon", 
        "to be added", "tbd", "todo", "follow best practices.", 
        "write good code.", "be careful.", "follow guidelines."
    }

    # Curated knowledge mapping for topics across Python, Full Stack, Java, Data Analysis, and Core CS
    TOPIC_KNOWLEDGE_BASE = {
        # Python Fundamentals & Syntax
        "syntax": [
            {
                "common_pitfall": "Mixing tab characters and space characters for indentation within the same scope.",
                "recommended_solution": "Configure your editor/IDE to standardize on 4 spaces per indentation level and convert tabs to spaces on save.",
                "technical_rationale": "Python 3 disallows mixing tabs and spaces, raising IndentationError at parse time because visual tab width varies across environments."
            },
            {
                "common_pitfall": "Using mutable default arguments in function definitions (e.g., def append_item(val, items=[])).",
                "recommended_solution": "Use None as the default value and initialize a fresh list inside the function body if items is None.",
                "technical_rationale": "Default argument expressions are evaluated once when the function is defined, sharing the same mutable list object across all invocations."
            },
            {
                "common_pitfall": "Shadowing built-in functions or types with local variable names (e.g., list = [1, 2, 3] or id = 101).",
                "recommended_solution": "Use descriptive identifier names such as item_list or entity_id instead of reserved built-in names.",
                "technical_rationale": "Overwriting built-ins hides the standard constructor in local scope, causing unexpected TypeErrors in subsequent operations."
            }
        ],
        "variables": [
            {
                "common_pitfall": "Attempting in-place mutation of immutable sequences like strings or tuples (e.g., s[0] = 'H').",
                "recommended_solution": "Construct a new string or tuple using slicing, concatenation, or list conversions.",
                "technical_rationale": "Python strings and tuples are immutable; direct item assignment raises TypeError to guarantee hash stability and thread safety."
            },
            {
                "common_pitfall": "Assuming assignment creates an independent copy of a list or dictionary (e.g., list_b = list_a).",
                "recommended_solution": "Use list_a.copy() or copy.deepcopy(data) when independent duplicate objects are required.",
                "technical_rationale": "Assignment in Python binds an additional reference (pointer) to the existing heap object rather than duplicating memory."
            },
            {
                "common_pitfall": "Using 'is' for value comparison instead of '==' when comparing numbers or strings.",
                "recommended_solution": "Use '==' to test value equivalence and reserve 'is' exclusively for singleton identity checks (e.g., 'is None').",
                "technical_rationale": "The 'is' operator checks whether two variables point to the identical memory address, which fails for non-interned objects."
            }
        ],
        "loops": [
            {
                "common_pitfall": "Modifying a collection (adding or deleting items) while iterating over it in a loop.",
                "recommended_solution": "Iterate over a shallow copy of the collection (e.g., for item in list(data):) or use a list comprehension.",
                "technical_rationale": "Mutating collection length during iteration shifts internal indices, causing skipped elements or runtime mutation errors."
            },
            {
                "common_pitfall": "Creating unbounded while loops by forgetting to update the loop condition variable.",
                "recommended_solution": "Ensure the loop invariant variable is systematically updated in every branch or enforce a maximum iteration threshold.",
                "technical_rationale": "Unbounded loops cause 100% CPU thread starvation, blocking application event loops and freezing runtime processes."
            },
            {
                "common_pitfall": "Using manual index counters (i = 0; i += 1) when iterating over sequence items.",
                "recommended_solution": "Use Python's built-in enumerate(items) or zip(seq1, seq2) for idiomatic indexed traversal.",
                "technical_rationale": "Manual index tracking is error-prone, introduces off-by-one bugs, and bypasses optimized C-level iteration protocols."
            }
        ],
        "data_structures": [
            {
                "common_pitfall": "Omitting validation or boundary checks in Data Structures.",
                "recommended_solution": "Validate indexes, node references, empty structures, and boundary conditions before performing operations. Handle cases such as empty arrays, empty stacks, and out-of-range indexes explicitly.",
                "technical_rationale": "Boundary validation prevents invalid memory access, runtime errors, incorrect traversal, and inconsistent data-structure state."
            },
            {
                "common_pitfall": "Using lists for frequent membership lookups (e.g., if item in large_list) inside hot loops.",
                "recommended_solution": "Convert the collection to a set or dict to achieve O(1) average-time complexity lookups.",
                "technical_rationale": "List membership tests require O(n) sequential scanning, leading to quadratic O(n^2) degradation in repetitive iterations."
            },
            {
                "common_pitfall": "Using dictionary keys without validating existence, causing unhandled KeyError crashes.",
                "recommended_solution": "Use dict.get(key, default) or employ collections.defaultdict for safe access with fallbacks.",
                "technical_rationale": "Direct subscripting (dict[key]) raises KeyError if the key is absent, whereas .get() returns a fallback gracefully."
            }
        ],
        "functions": [
            {
                "common_pitfall": "Relying on global variables inside function bodies instead of passing parameters and returning values.",
                "recommended_solution": "Pass required data explicitly as arguments and return computation results through return statements.",
                "technical_rationale": "Global state coupling destroys pure functional contracts, prevents unit testing isolation, and causes race conditions."
            },
            {
                "common_pitfall": "Returning multiple divergent types inconsistently from the same function (e.g., returning string error or dict data).",
                "recommended_solution": "Use consistent return schemas, Optional[T] typing, or raise structured custom exceptions on error states.",
                "technical_rationale": "Inconsistent return types force callers to write defensive runtime type checks, increasing cognitive load and error risk."
            },
            {
                "common_pitfall": "Forgetting to return a value from branches in non-void functions, implicitly returning None.",
                "recommended_solution": "Ensure all conditional execution branches terminate with an explicit return statement or raise an exception.",
                "technical_rationale": "Implicit None returns propagate silently until downstream operations fail with AttributeError on NoneType."
            }
        ],
        "oop": [
            {
                "common_pitfall": "Defining instance attributes directly in the class body rather than inside __init__().",
                "recommended_solution": "Declare and initialize all instance-specific state on self inside the __init__() constructor.",
                "technical_rationale": "Attributes defined in the class body are class-level attributes shared across all instances, causing accidental cross-instance data bleeding."
            },
            {
                "common_pitfall": "Accessing private/protected attributes directly instead of using property accessors and public methods.",
                "recommended_solution": "Encapsulate internal state with @property getters/setters and validate invariants on assignment.",
                "technical_rationale": "Direct state mutation violates encapsulation, bypassing validation rules and breaking backward compatibility when refactoring."
            },
            {
                "common_pitfall": "Overriding a parent class method in a subclass without invoking super().__init__() or super().method().",
                "recommended_solution": "Invoke super().__init__(*args) in child constructors to initialize inherited parent class attributes.",
                "technical_rationale": "Omitting super() bypasses parent initialization, leaving inherited properties unassigned and raising AttributeErrors."
            }
        ],
        "exceptions": [
            {
                "common_pitfall": "Using bare except: or catch-all except Exception: that silently ignores critical errors with 'pass'.",
                "recommended_solution": "Catch specific exception types (e.g., ValueError, FileNotFoundError) and log error details with logging.exception().",
                "technical_rationale": "Silent broad exception suppression conceals bugs, hides syntax errors, and interferes with keyboard interrupts (SIGINT)."
            },
            {
                "common_pitfall": "Failing to close unmanaged file descriptors or network sockets after exceptions occur.",
                "recommended_solution": "Always use context managers ('with open(...) as f:') to guarantee deterministic resource cleanup.",
                "technical_rationale": "Context managers invoke __enter__ and __exit__ protocols, releasing operating system file locks even if exceptions are raised."
            },
            {
                "common_pitfall": "Using exceptions for ordinary control flow instead of defensive conditional checks.",
                "recommended_solution": "Use conditional statements for expected business conditions and reserve exceptions for truly anomalous events.",
                "technical_rationale": "Exception construction builds full stack traces in runtime memory, causing substantial CPU overhead in high-throughput paths."
            }
        ],
        # React & Frontend
        "react": [
            {
                "common_pitfall": "Mutating React component state directly (e.g., state.items.push(newItem)) instead of using setter functions.",
                "recommended_solution": "Always update state immutably using setState(prev => [...prev, newItem]) or functional updates.",
                "technical_rationale": "Direct object mutation does not change object references, preventing React's shallow comparison from triggering re-renders."
            },
            {
                "common_pitfall": "Missing key props or using array index as keys in mapped list elements.",
                "recommended_solution": "Use stable, unique entity identifiers (such as item.id) as the key prop for mapped elements.",
                "technical_rationale": "Using array indices as keys confuses React's virtual DOM reconciliation algorithm during insertions or sorting, causing stale UI state."
            },
            {
                "common_pitfall": "Omitting dependencies in useEffect dependency arrays or creating infinite render loops.",
                "recommended_solution": "List all referenced variables and functions in the dependency array or wrap callback handlers in useCallback.",
                "technical_rationale": "Incomplete dependency arrays cause stale closure bugs, while unmemoized object dependencies trigger infinite re-render loops."
            }
        ],
        # Node & Express
        "node": [
            {
                "common_pitfall": "Executing synchronous blocking operations (e.g., fs.readFileSync) in request handlers.",
                "recommended_solution": "Use asynchronous non-blocking APIs (e.g., fs.promises.readFile or async/await) for all I/O.",
                "technical_rationale": "Node.js runs on a single event loop; synchronous I/O blocks the entire thread, halting all concurrent client requests."
            },
            {
                "common_pitfall": "Failing to handle asynchronous Promise rejections or unhandled rejections in Express middleware.",
                "recommended_solution": "Wrap asynchronous routes in try/catch and forward errors to next(err) or use express-async-handler.",
                "technical_rationale": "Unhandled promise rejections leave client HTTP sockets hanging without response and can crash the Node.js process."
            },
            {
                "common_pitfall": "Storing plain text passwords or secrets in application source repositories.",
                "recommended_solution": "Store secrets in environment variables (.env) and hash user passwords using bcrypt with a salt factor >= 12.",
                "technical_rationale": "Plaintext passwords in source code create critical security vulnerabilities and fail security compliance benchmarks."
            }
        ],
        # Java & Spring
        "java": [
            {
                "common_pitfall": "Comparing Java Strings using '==' instead of .equals().",
                "recommended_solution": "Always compare String content using str1.equals(str2) or Objects.equals(str1, str2).",
                "technical_rationale": "In Java, '==' compares object reference addresses, which fails for strings created outside the JVM String Constant Pool."
            },
            {
                "common_pitfall": "Failing to handle NullPointerException defensively when retrieving values from maps or optional entities.",
                "recommended_solution": "Use Optional.ofNullable(val), null-checks, or Objects.requireNonNull() with descriptive messages.",
                "technical_rationale": "Dereferencing null references causes immediate unchecked NullPointerExceptions, crashing worker threads."
            },
            {
                "common_pitfall": "Using raw collection types (e.g., List list = new ArrayList()) instead of parameterized generics.",
                "recommended_solution": "Specify generic type parameters (e.g., List<String> list = new ArrayList<>()) for all collections.",
                "technical_rationale": "Raw types disable compile-time type checking, deferring type errors to ClassCastExceptions at runtime."
            }
        ],
        # Spring Boot & Enterprise Java
        "spring": [
            {
                "common_pitfall": "Using field injection with @Autowired instead of constructor injection.",
                "recommended_solution": "Use constructor injection (or Lombok @RequiredArgsConstructor) to inject Spring beans.",
                "technical_rationale": "Constructor injection ensures dependencies are immutable (final), prevents partial initialization, and enables simple mock testing."
            },
            {
                "common_pitfall": "Invoking @Transactional methods from within the same class (self-invocation).",
                "recommended_solution": "Place transactional methods in a separate service bean or inject the self-proxy to invoke them.",
                "technical_rationale": "Spring manages transactions via dynamic AOP proxies; direct internal method calls bypass the proxy boundary entirely."
            },
            {
                "common_pitfall": "Returning JPA/Hibernate entity objects directly from @RestController endpoints.",
                "recommended_solution": "Map entity models to dedicated Data Transfer Objects (DTOs) before returning API responses.",
                "technical_rationale": "Exposing entities directly causes infinite circular JSON serialization loops and exposes internal database schema details."
            }
        ],
        # NumPy & Pandas Data Analysis
        "data_analysis": [
            {
                "common_pitfall": "Iterating over Pandas DataFrame rows using for loops or .iterrows() for data transformations.",
                "recommended_solution": "Use vectorized NumPy/Pandas operations (e.g., df['c'] = df['a'] + df['b']) or .apply() for complex logic.",
                "technical_rationale": "Vectorized operations execute in optimized compiled C/Fortran routines, achieving 100x to 1000x faster execution than Python loops."
            },
            {
                "common_pitfall": "Modifying a sliced DataFrame without .copy(), triggering SettingWithCopyWarning.",
                "recommended_solution": "Explicitly create a copy with df.copy() or use .loc[row_indexer, col_indexer] for direct assignment.",
                "technical_rationale": "Slices may return a view or a copy; modifying a view without .loc risks ambiguous assignment and silent corruption."
            },
            {
                "common_pitfall": "Ignoring missing data (NaN) before performing mathematical or aggregative operations.",
                "recommended_solution": "Inspect missing values with df.isna().sum() and handle them via .fillna(), .interpolate(), or .dropna().",
                "technical_rationale": "Unhandled NaN values distort summary statistics (means, correlations) and cause scikit-learn models to throw runtime ValueErrors."
            }
        ],
        # General Software Engineering Fallback
        "general": [
            {
                "common_pitfall": "Omitting input boundary and type validation on external user inputs or API payloads.",
                "recommended_solution": "Validate all incoming data against strict schemas and boundary limits before passing to core logic.",
                "technical_rationale": "Unchecked inputs cause memory corruption, injection attacks, unexpected runtime crashes, and unpredictable application state."
            },
            {
                "common_pitfall": "Hardcoding configuration constants, secrets, and URLs directly in business logic.",
                "recommended_solution": "Externalize configuration parameters into environment variables or dedicated settings profiles.",
                "technical_rationale": "Hardcoded values prevent environment portability across development, staging, and production, and risk exposing credentials."
            },
            {
                "common_pitfall": "Neglecting automated unit tests for edge cases and failure modes.",
                "recommended_solution": "Implement comprehensive test suites covering nominal paths, boundary conditions, and expected exception states.",
                "technical_rationale": "Without automated tests, code refactoring inevitably introduces regressions that go undetected until reaching production."
            }
        ]
    }

    @classmethod
    def validate_common_mistakes(cls, items: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validates that a common_mistakes collection meets the mandatory requirements:
        1. Must contain at least 3 items.
        2. Every item must have non-empty common_pitfall, recommended_solution, technical_rationale.
        3. No placeholder strings like 'Coming soon', 'Not available', or generic fluff.
        """
        if not items or not isinstance(items, list):
            return False, ["Common mistakes collection must be a non-empty list of items."]

        if len(items) < 3:
            return False, [f"Must contain at least 3 common mistakes (found {len(items)})."]

        errors = []
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                errors.append(f"Item #{idx} is not a valid dictionary structure.")
                continue

            pitfall = str(item.get('common_pitfall') or item.get('mistake') or '').strip()
            solution = str(item.get('recommended_solution') or item.get('correct') or item.get('good_code') or '').strip()
            rationale = str(item.get('technical_rationale') or item.get('reason') or item.get('explanation') or '').strip()

            if not pitfall:
                errors.append(f"Item #{idx} is missing mandatory 'common_pitfall'.")
            elif pitfall.lower() in cls.DISALLOWED_PLACEHOLDERS or len(pitfall) < 10:
                errors.append(f"Item #{idx} contains invalid placeholder 'common_pitfall': '{pitfall}'.")

            if not solution:
                errors.append(f"Item #{idx} is missing mandatory 'recommended_solution'.")
            elif solution.lower() in cls.DISALLOWED_PLACEHOLDERS or len(solution) < 10:
                errors.append(f"Item #{idx} contains invalid placeholder 'recommended_solution': '{solution}'.")

            if not rationale:
                errors.append(f"Item #{idx} is missing mandatory 'technical_rationale'.")
            elif rationale.lower() in cls.DISALLOWED_PLACEHOLDERS or len(rationale) < 10:
                errors.append(f"Item #{idx} contains invalid placeholder 'technical_rationale': '{rationale}'.")

        return len(errors) == 0, errors

    @classmethod
    def resolve_domain_key(cls, topic_title: str, skill_name: str = "") -> str:
        """Determines the most accurate domain knowledge key for a given topic."""
        combined = f"{topic_title} {skill_name}".lower()
        is_java = 'java' in combined or 'spring' in combined or 'jvm' in combined or 'hibernate' in combined
        is_python = 'python' in combined or 'pandas' in combined or 'numpy' in combined

        if any(k in combined for k in ['react', 'component', 'frontend', 'hook', 'dom', 'router', 'state management']):
            return 'react'
        elif any(k in combined for k in ['node', 'express', 'restful', 'jwt', 'auth', 'endpoint', 'server']):
            return 'node'
        elif any(k in combined for k in ['spring', 'hibernate', 'jpa', 'microservice', 'bean', 'boot']):
            return 'spring'
        elif any(k in combined for k in ['numpy', 'pandas', 'dataframe', 'matplotlib', 'seaborn', 'data analysis', 'eda', 'cleaning']):
            return 'data_analysis'
        elif any(k in combined for k in ['oop', 'object-oriented', 'metaclass', 'inheritance', 'polymorphism', 'encapsulation', 'class']):
            if is_java:
                return 'java'
            return 'oop'
        elif is_java and any(k in combined for k in ['java', 'interface', 'jvm', 'generics', 'collection']):
            return 'java'
        elif any(k in combined for k in ['loop', 'iteration', 'while', 'for']):
            return 'loops'
        elif any(k in combined for k in ['variable', 'type', 'string', 'immutable', 'memory reference', 'pointer']):
            return 'variables'
        elif any(k in combined for k in ['data structure', 'array', 'sequence', 'list', 'dictionary', 'stack', 'queue', 'linked list', 'hash']):
            return 'data_structures'
        elif any(k in combined for k in ['function', 'lambda', 'scope', 'parameter', 'decorator']):
            return 'functions'
        elif any(k in combined for k in ['exception', 'error', 'try', 'catch', 'file i/o']):
            return 'exceptions'
        elif is_java:
            return 'java'
        elif is_python or any(k in combined for k in ['python', 'syntax', 'interpreter', 'environment']):
            return 'syntax'
        return 'general'

    @classmethod
    def generate_topic_common_mistakes(cls, topic_title: str, skill_name: str = "") -> List[Dict[str, str]]:
        """
        Generates 3 to 5 comprehensive, pedagogical common-mistake items 
        tailored to the topic with both canonical keys and legacy aliases.
        """
        domain = cls.resolve_domain_key(topic_title, skill_name)
        base_items = cls.TOPIC_KNOWLEDGE_BASE.get(domain, cls.TOPIC_KNOWLEDGE_BASE['general'])

        results = []
        for item in base_items:
            pitfall = item['common_pitfall']
            solution = item['recommended_solution']
            rationale = item['technical_rationale']

            results.append({
                'common_pitfall': pitfall,
                'recommended_solution': solution,
                'technical_rationale': rationale,
                # Legacy compatibility aliases
                'mistake': pitfall,
                'correct': solution,
                'reason': rationale,
                'bad_code': f"# Anti-pattern in {topic_title}\n# {pitfall}",
                'good_code': f"# Best Practice in {topic_title}\n# {solution}",
                'explanation': rationale
            })
        return results

    @classmethod
    def repair_or_complete_common_mistakes(
        cls, 
        existing_items: Optional[List[Dict[str, Any]]], 
        topic_title: str, 
        skill_name: str = "",
        max_retries: int = 3
    ) -> List[Dict[str, str]]:
        """
        Audit, repair, and regenerate common mistakes:
        1. Preserves existing valid common_pitfall (or mistake).
        2. Generates missing recommended_solution or technical_rationale tailored to topic.
        3. Fills up to at least 3 to 5 high-quality items.
        4. Validates completeness with retry mechanism.
        """
        domain = cls.resolve_domain_key(topic_title, skill_name)
        domain_items = cls.TOPIC_KNOWLEDGE_BASE.get(domain, cls.TOPIC_KNOWLEDGE_BASE['general'])

        for attempt in range(max_retries):
            repaired: List[Dict[str, str]] = []
            seen_pitfalls = set()

            # 1. Inspect and preserve existing items
            if existing_items and isinstance(existing_items, list):
                for idx, item in enumerate(existing_items):
                    if not isinstance(item, dict):
                        continue
                    pitfall = (item.get('common_pitfall') or item.get('mistake') or '').strip()
                    solution = (item.get('recommended_solution') or item.get('correct') or item.get('good_code') or '').strip()
                    rationale = (item.get('technical_rationale') or item.get('reason') or item.get('explanation') or '').strip()

                    # Discard empty placeholders or raw code snippets masquerading as solutions
                    if pitfall.lower() in cls.DISALLOWED_PLACEHOLDERS:
                        pitfall = ""
                    if solution.lower() in cls.DISALLOWED_PLACEHOLDERS or solution.startswith('#') or solution.startswith('//') or ('\n' in solution and 'is_valid' in solution):
                        solution = ""
                    if rationale.lower() in cls.DISALLOWED_PLACEHOLDERS or "always assert preconditions" in rationale.lower():
                        rationale = ""

                    # If pitfall is present but solution or rationale are missing, generate them
                    if pitfall:
                        seen_pitfalls.add(pitfall.lower())
                        if not solution or not rationale:
                            matching = next((m for m in domain_items if pitfall.lower() in m['common_pitfall'].lower() or m['common_pitfall'].lower() in pitfall.lower()), None)
                            if not matching:
                                matching = domain_items[idx % len(domain_items)]
                            if not solution:
                                solution = matching['recommended_solution']
                            if not rationale:
                                rationale = matching['technical_rationale']

                        repaired.append({
                            'common_pitfall': pitfall,
                            'recommended_solution': solution,
                            'technical_rationale': rationale,
                            'mistake': pitfall,
                            'correct': solution,
                            'reason': rationale,
                            'bad_code': item.get('bad_code') or f"# Anti-pattern in {topic_title}",
                            'good_code': item.get('good_code') or f"# Best Practice in {topic_title}",
                            'explanation': rationale
                        })

            # 2. Supplement with domain knowledge to ensure at least 3-5 items
            for d_item in domain_items:
                if len(repaired) >= 5:
                    break
                p_text = d_item['common_pitfall']
                if p_text.lower() not in seen_pitfalls:
                    seen_pitfalls.add(p_text.lower())
                    repaired.append({
                        'common_pitfall': p_text,
                        'recommended_solution': d_item['recommended_solution'],
                        'technical_rationale': d_item['technical_rationale'],
                        'mistake': p_text,
                        'correct': d_item['recommended_solution'],
                        'reason': d_item['technical_rationale'],
                        'bad_code': f"# Anti-pattern in {topic_title}\n# {p_text}",
                        'good_code': f"# Best Practice in {topic_title}\n# {d_item['recommended_solution']}",
                        'explanation': d_item['technical_rationale']
                    })

            is_valid, errors = cls.validate_common_mistakes(repaired)
            if is_valid:
                return repaired

        # If retries fail, return repaired with fallback and mark status
        for r in repaired:
            if not r.get('recommended_solution'):
                r['recommended_solution'] = f"Validate and adhere to official production best practices for {topic_title}."
            if not r.get('technical_rationale'):
                r['technical_rationale'] = f"Ensures architectural consistency, type stability, and defensive resource handling in {topic_title}."
        return repaired
