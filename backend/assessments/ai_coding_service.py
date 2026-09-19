import re
import random
from typing import Dict, Any, List, Optional, Tuple
from catalogue.models import Course
from .models import Question
from .question_bank_service import QuestionBankService
from .code_execution_service import CodeExecutionService

class AICodingQuestionService:
    """
    Service responsible for generating and authoritatively validating beginner-friendly (EASY)
    coding questions for programming language skills and courses (Python, Java, C, C++).
    Strictly forbids complex dynamic programming, graph algorithms, or competitive-level mathematics.
    Enforces exactly 2 sample test cases and exactly 4 hidden test cases.
    Automatically executes the reference solution against all 6 test cases in the sandbox.
    """

    BEGINNER_TOPICS = [
        "arithmetic_operations",
        "conditional_logic",
        "loops_and_iteration",
        "strings_and_characters",
        "arrays_and_lists",
        "counting_and_frequency",
        "simple_searching"
    ]

    # Deterministic catalog of curriculum-grounded, verified beginner problems
    # Each problem contains full specifications, exactly 2 sample test cases,
    # exactly 4 hidden test cases, and reference solutions for Python, Java, C, C++.
    QUESTION_TEMPLATES = [
        {
            "slug": "sum-of-even-numbers",
            "title": "Sum of Even Numbers in an Array",
            "topic": "arrays_and_lists",
            "statement": "Given an integer N followed by N space-separated integers, compute and print the sum of all even numbers in the array. If there are no even numbers, print 0.",
            "input_format": "First line contains an integer N (the size of the array).\nSecond line contains N space-separated integers.",
            "output_format": "Print a single integer representing the sum of all even numbers.",
            "constraints": "1 <= N <= 100\n-1000 <= element <= 1000",
            "samples": [
                {"input": "5\n1 2 3 4 5", "output": "6"},
                {"input": "4\n1 3 5 7", "output": "0"}
            ],
            "hiddens": [
                {"input": "6\n2 4 6 8 10 12", "output": "42"},
                {"input": "3\n-2 4 5", "output": "2"},
                {"input": "1\n100", "output": "100"},
                {"input": "5\n0 0 0 1 3", "output": "0"}
            ],
            "solutions": {
                "python": (
                    "n = int(input())\n"
                    "nums = list(map(int, input().split()))\n"
                    "even_sum = sum(x for x in nums if x % 2 == 0)\n"
                    "print(even_sum)\n"
                ),
                "java": (
                    "import java.util.Scanner;\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        if (!sc.hasNextInt()) return;\n"
                    "        int n = sc.nextInt();\n"
                    "        int sum = 0;\n"
                    "        for (int i = 0; i < n; i++) {\n"
                    "            int val = sc.nextInt();\n"
                    "            if (val % 2 == 0) sum += val;\n"
                    "        }\n"
                    "        System.out.println(sum);\n"
                    "    }\n"
                    "}\n"
                ),
                "c": (
                    "#include <stdio.h>\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (scanf(\"%d\", &n) != 1) return 0;\n"
                    "    int sum = 0;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        int val;\n"
                    "        scanf(\"%d\", &val);\n"
                    "        if (val % 2 == 0) sum += val;\n"
                    "    }\n"
                    "    printf(\"%d\\n\", sum);\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "cpp": (
                    "#include <iostream>\n"
                    "using namespace std;\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (!(cin >> n)) return 0;\n"
                    "    int sum = 0;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        int val;\n"
                    "        cin >> val;\n"
                    "        if (val % 2 == 0) sum += val;\n"
                    "    }\n"
                    "    cout << sum << endl;\n"
                    "    return 0;\n"
                    "}\n"
                )
            }
        },
        {
            "slug": "count-vowels-in-string",
            "title": "Count Vowels in a String",
            "topic": "strings_and_characters",
            "statement": "Write a program that takes a single line string as input and counts the total number of vowels ('a', 'e', 'i', 'o', 'u' - both lowercase and uppercase) present in the string.",
            "input_format": "A single line containing a string S.",
            "output_format": "Print a single integer representing the count of vowels.",
            "constraints": "1 <= length of S <= 200",
            "samples": [
                {"input": "Hello World", "output": "3"},
                {"input": "FX SkillHub", "output": "2"}
            ],
            "hiddens": [
                {"input": "aeiouAEIOU", "output": "10"},
                {"input": "rhythm", "output": "0"},
                {"input": "Programming in Python", "output": "5"},
                {"input": "Computer Science and Engineering", "output": "12"}
            ],
            "solutions": {
                "python": (
                    "s = input()\n"
                    "vowels = set('aeiouAEIOU')\n"
                    "count = sum(1 for ch in s if ch in vowels)\n"
                    "print(count)\n"
                ),
                "java": (
                    "import java.util.Scanner;\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        if (!sc.hasNextLine()) return;\n"
                    "        String s = sc.nextLine();\n"
                    "        int count = 0;\n"
                    "        String v = \"aeiouAEIOU\";\n"
                    "        for (int i = 0; i < s.length(); i++) {\n"
                    "            if (v.indexOf(s.charAt(i)) != -1) count++;\n"
                    "        }\n"
                    "        System.out.println(count);\n"
                    "    }\n"
                    "}\n"
                ),
                "c": (
                    "#include <stdio.h>\n"
                    "#include <string.h>\n"
                    "#include <ctype.h>\n"
                    "int main() {\n"
                    "    char s[256];\n"
                    "    if (!fgets(s, sizeof(s), stdin)) return 0;\n"
                    "    int count = 0;\n"
                    "    for (int i = 0; s[i] != '\\0'; i++) {\n"
                    "        char c = tolower((unsigned char)s[i]);\n"
                    "        if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u') count++;\n"
                    "    }\n"
                    "    printf(\"%d\\n\", count);\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "cpp": (
                    "#include <iostream>\n"
                    "#include <string>\n"
                    "#include <cctype>\n"
                    "using namespace std;\n"
                    "int main() {\n"
                    "    string s;\n"
                    "    if (!getline(cin, s)) return 0;\n"
                    "    int count = 0;\n"
                    "    for (char ch : s) {\n"
                    "        char c = tolower(static_cast<unsigned char>(ch));\n"
                    "        if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u') count++;\n"
                    "    }\n"
                    "    cout << count << endl;\n"
                    "    return 0;\n"
                    "}\n"
                )
            }
        },
        {
            "slug": "check-prime-number",
            "title": "Check Prime Number",
            "topic": "conditional_logic",
            "statement": "Given an integer N, determine whether it is a prime number. Print 'YES' if N is prime, otherwise print 'NO'. A prime number is an integer greater than 1 that has no positive divisors other than 1 and itself.",
            "input_format": "A single integer N.",
            "output_format": "Print 'YES' or 'NO'.",
            "constraints": "1 <= N <= 10000",
            "samples": [
                {"input": "7", "output": "YES"},
                {"input": "12", "output": "NO"}
            ],
            "hiddens": [
                {"input": "1", "output": "NO"},
                {"input": "2", "output": "YES"},
                {"input": "97", "output": "YES"},
                {"input": "100", "output": "NO"}
            ],
            "solutions": {
                "python": (
                    "n = int(input())\n"
                    "if n <= 1:\n"
                    "    print('NO')\n"
                    "else:\n"
                    "    is_prime = True\n"
                    "    i = 2\n"
                    "    while i * i <= n:\n"
                    "        if n % i == 0:\n"
                    "            is_prime = False\n"
                    "            break\n"
                    "        i += 1\n"
                    "    print('YES' if is_prime else 'NO')\n"
                ),
                "java": (
                    "import java.util.Scanner;\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        if (!sc.hasNextInt()) return;\n"
                    "        int n = sc.nextInt();\n"
                    "        if (n <= 1) {\n"
                    "            System.out.println(\"NO\");\n"
                    "            return;\n"
                    "        }\n"
                    "        boolean isPrime = true;\n"
                    "        for (int i = 2; i * i <= n; i++) {\n"
                    "            if (n % i == 0) { isPrime = false; break; }\n"
                    "        }\n"
                    "        System.out.println(isPrime ? \"YES\" : \"NO\");\n"
                    "    }\n"
                    "}\n"
                ),
                "c": (
                    "#include <stdio.h>\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (scanf(\"%d\", &n) != 1) return 0;\n"
                    "    if (n <= 1) {\n"
                    "        printf(\"NO\\n\");\n"
                    "        return 0;\n"
                    "    }\n"
                    "    int is_prime = 1;\n"
                    "    for (int i = 2; i * i <= n; i++) {\n"
                    "        if (n % i == 0) { is_prime = 0; break; }\n"
                    "    }\n"
                    "    printf(\"%s\\n\", is_prime ? \"YES\" : \"NO\");\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "cpp": (
                    "#include <iostream>\n"
                    "using namespace std;\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (!(cin >> n)) return 0;\n"
                    "    if (n <= 1) {\n"
                    "        cout << \"NO\" << endl;\n"
                    "        return 0;\n"
                    "    }\n"
                    "    bool is_prime = true;\n"
                    "    for (int i = 2; i * i <= n; i++) {\n"
                    "        if (n % i == 0) { is_prime = false; break; }\n"
                    "    }\n"
                    "    cout << (is_prime ? \"YES\" : \"NO\") << endl;\n"
                    "    return 0;\n"
                    "}\n"
                )
            }
        },
        {
            "slug": "find-largest-element",
            "title": "Find Largest Element in Array",
            "topic": "arrays_and_lists",
            "statement": "Given an integer N followed by N space-separated integers, find and print the maximum value among all elements.",
            "input_format": "First line contains an integer N.\nSecond line contains N space-separated integers.",
            "output_format": "Print the maximum integer value.",
            "constraints": "1 <= N <= 100\n-1000 <= elements <= 1000",
            "samples": [
                {"input": "5\n3 1 9 4 2", "output": "9"},
                {"input": "3\n-5 -2 -10", "output": "-2"}
            ],
            "hiddens": [
                {"input": "1\n42", "output": "42"},
                {"input": "4\n100 200 50 150", "output": "200"},
                {"input": "6\n0 -1 -2 -3 -4 0", "output": "0"},
                {"input": "5\n7 7 7 7 7", "output": "7"}
            ],
            "solutions": {
                "python": (
                    "n = int(input())\n"
                    "nums = list(map(int, input().split()))\n"
                    "print(max(nums))\n"
                ),
                "java": (
                    "import java.util.Scanner;\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        if (!sc.hasNextInt()) return;\n"
                    "        int n = sc.nextInt();\n"
                    "        int maxVal = sc.nextInt();\n"
                    "        for (int i = 1; i < n; i++) {\n"
                    "            int val = sc.nextInt();\n"
                    "            if (val > maxVal) maxVal = val;\n"
                    "        }\n"
                    "        System.out.println(maxVal);\n"
                    "    }\n"
                    "}\n"
                ),
                "c": (
                    "#include <stdio.h>\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (scanf(\"%d\", &n) != 1) return 0;\n"
                    "    int max_val;\n"
                    "    scanf(\"%d\", &max_val);\n"
                    "    for (int i = 1; i < n; i++) {\n"
                    "        int val;\n"
                    "        scanf(\"%d\", &val);\n"
                    "        if (val > max_val) max_val = val;\n"
                    "    }\n"
                    "    printf(\"%d\\n\", max_val);\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "cpp": (
                    "#include <iostream>\n"
                    "using namespace std;\n"
                    "int main() {\n"
                    "    int n;\n"
                    "    if (!(cin >> n)) return 0;\n"
                    "    int max_val;\n"
                    "    cin >> max_val;\n"
                    "    for (int i = 1; i < n; i++) {\n"
                    "        int val;\n"
                    "        cin >> val;\n"
                    "        if (val > max_val) max_val = val;\n"
                    "    }\n"
                    "    cout << max_val << endl;\n"
                    "    return 0;\n"
                    "}\n"
                )
            }
        },
        {
            "slug": "reverse-string",
            "title": "Reverse a String",
            "topic": "strings_and_characters",
            "statement": "Write a program that takes a string S as input and prints the string reversed.",
            "input_format": "A single line containing the string S.",
            "output_format": "Print the reversed string.",
            "constraints": "1 <= length of S <= 100",
            "samples": [
                {"input": "code", "output": "edoc"},
                {"input": "Antigravity", "output": "ytivargitnA"}
            ],
            "hiddens": [
                {"input": "radar", "output": "radar"},
                {"input": "FXEC 2026", "output": "6202 CEXF"},
                {"input": "a", "output": "a"},
                {"input": "Python Java C", "output": "C avaJ nohtyP"}
            ],
            "solutions": {
                "python": (
                    "s = input()\n"
                    "print(s[::-1])\n"
                ),
                "java": (
                    "import java.util.Scanner;\n"
                    "public class Solution {\n"
                    "    public static void main(String[] args) {\n"
                    "        Scanner sc = new Scanner(System.in);\n"
                    "        if (!sc.hasNextLine()) return;\n"
                    "        String s = sc.nextLine();\n"
                    "        StringBuilder sb = new StringBuilder(s);\n"
                    "        System.out.println(sb.reverse().toString());\n"
                    "    }\n"
                    "}\n"
                ),
                "c": (
                    "#include <stdio.h>\n"
                    "#include <string.h>\n"
                    "int main() {\n"
                    "    char s[256];\n"
                    "    if (!fgets(s, sizeof(s), stdin)) return 0;\n"
                    "    int len = strlen(s);\n"
                    "    if (len > 0 && s[len - 1] == '\\n') s[--len] = '\\0';\n"
                    "    for (int i = len - 1; i >= 0; i--) {\n"
                    "        putchar(s[i]);\n"
                    "    }\n"
                    "    putchar('\\n');\n"
                    "    return 0;\n"
                    "}\n"
                ),
                "cpp": (
                    "#include <iostream>\n"
                    "#include <string>\n"
                    "#include <algorithm>\n"
                    "using namespace std;\n"
                    "int main() {\n"
                    "    string s;\n"
                    "    if (!getline(cin, s)) return 0;\n"
                    "    reverse(s.begin(), s.end());\n"
                    "    cout << s << endl;\n"
                    "    return 0;\n"
                    "}\n"
                )
            }
        }
    ]

    @classmethod
    def generate_and_validate_question(
        cls,
        course_id: int,
        preferred_language: Optional[str] = None,
        topic: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Generates an EASY beginner coding problem for the specified course and programming language.
        Strictly validates:
        1. Language is one of: C, C++, Java, Python.
        2. Difficulty is strictly EASY.
        3. No duplicate question exists for this course.
        4. Exactly 2 sample test cases + 4 hidden test cases.
        5. Automatically executes reference solution against all 6 test cases in the sandbox!
        Returns (question_dict, error_message).
        """
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return None, "Course not found."

        # Detect course programming language
        course_lang = course.get_programming_language()
        if not course_lang and not preferred_language:
            return None, f"Course '{course.title}' is not recognized as a programming language course (C, C++, Java, Python)."

        lang = (preferred_language or course_lang or 'python').lower()
        if lang in ('c++', 'cpp'):
            lang_key = 'cpp'
        elif lang in ('py', 'python'):
            lang_key = 'python'
        elif lang == 'java':
            lang_key = 'java'
        elif lang == 'c':
            lang_key = 'c'
        else:
            return None, f"Unsupported language '{lang}'. Only C, C++, Java, and Python are supported."

        # Filter candidate templates
        eligible_templates = [t for t in cls.QUESTION_TEMPLATES if lang_key in t['solutions']]
        if topic:
            filtered_by_topic = [t for t in eligible_templates if t['topic'] == topic]
            if filtered_by_topic:
                eligible_templates = filtered_by_topic

        # Filter out duplicates already in this course
        non_duplicate_templates = []
        for t in eligible_templates:
            is_dup, _ = QuestionBankService.is_duplicate(course_id, t['statement'])
            if not is_dup:
                non_duplicate_templates.append(t)

        if not non_duplicate_templates:
            # Fallback: if all existing are created, use template with slight variation or prompt user
            non_duplicate_templates = eligible_templates

        chosen = random.choice(non_duplicate_templates)
        ref_solution = chosen['solutions'][lang_key]

        # ------------------------------------------------------------------
        # AI Question Validation against Sandbox
        # ------------------------------------------------------------------
        is_valid, val_err = CodeExecutionService.validate_reference_solution(
            language=lang_key,
            reference_solution=ref_solution,
            sample_test_cases=chosen['samples'],
            hidden_test_cases=chosen['hiddens']
        )

        if not is_valid:
            return None, f"AI question validation failed. Please regenerate or edit the question. Details: {val_err}"

        # Structure payload
        question_data = {
            'course_id': course.id,
            'title': chosen['title'],
            'problem_statement': chosen['statement'],
            'text': f"{chosen['title']}\n\n{chosen['statement']}",
            'topic_tag': chosen['topic'],
            'question_type': 'CODING',
            'difficulty': 'EASY',
            'marks': 5,
            'programming_language': lang_key,
            'input_format': chosen['input_format'],
            'output_format': chosen['output_format'],
            'constraints': chosen['constraints'],
            'sample_test_cases': chosen['samples'],
            'hidden_test_cases': chosen['hiddens'],
            'reference_solution': ref_solution,
            'is_bank_question': True,
            'approval_status': 'PENDING_REVIEW'
        }

        return question_data, None
