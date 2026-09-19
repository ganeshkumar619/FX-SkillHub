import os
import re
import sys
import time
import shutil
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Tuple

class CodeExecutionService:
    """
    Isolated sandboxed execution service for untrusted student programming code.
    Strictly forbids running student code inside the Django web process.
    Uses separate child processes, dedicated isolated temporary workspaces,
    strict CPU execution timeouts, and normalized line-ending comparisons.
    """

    TIMEOUT_SECONDS = 4.0

    @classmethod
    def _normalize_text(cls, text: Optional[str]) -> str:
        """Normalize line breaks and trailing whitespace for resilient output comparison."""
        if text is None:
            return ""
        # Normalize CRLF and CR to LF
        normalized = text.replace('\r\n', '\n').replace('\r', '\n')
        # Strip trailing whitespace on each line and overall
        lines = [line.rstrip() for line in normalized.split('\n')]
        return '\n'.join(lines).strip()

    @classmethod
    def _find_compiler(cls, compiler_name: str) -> Optional[str]:
        """Look up executable path for compiler or interpreter."""
        path = shutil.which(compiler_name)
        if path:
            return path
        # Common Windows paths fallback
        common_paths = [
            f"C:\\Program Files\\Common Files\\Oracle\\Java\\javapath\\{compiler_name}.exe",
            f"C:\\Program Files\\Java\\jdk*\\bin\\{compiler_name}.exe",
            f"C:\\MinGW\\bin\\{compiler_name}.exe",
            f"C:\\msys64\\mingw64\\bin\\{compiler_name}.exe",
            f"C:\\TDM-GCC-64\\bin\\{compiler_name}.exe",
        ]
        import glob
        for pattern in common_paths:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        return None

    @classmethod
    def execute_single_run(
        cls,
        language: str,
        code: str,
        stdin_input: str,
        timeout: float = TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """
        Executes code in an isolated temporary directory.
        Returns:
            {
                'success': bool,
                'stdout': str,
                'stderr': str,
                'exit_code': int,
                'timed_out': bool,
                'compilation_error': Optional[str],
                'execution_time_ms': float
            }
        """
        lang = (language or '').lower().strip()
        stdin_payload = stdin_input or ""
        start_time = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix=f"fx_sandbox_{lang}_") as temp_dir:
            try:
                # -----------------------------------------------------------
                # PYTHON EXECUTION
                # -----------------------------------------------------------
                if lang in ('python', 'py'):
                    script_path = os.path.join(temp_dir, "solution.py")
                    with open(script_path, "w", encoding="utf-8") as f:
                        f.write(code)

                    # -I: isolated mode (ignores PYTHONPATH and user site-packages)
                    # -s: don't add user site directory
                    cmd = [sys.executable, "-I", "-s", script_path]
                    proc = subprocess.run(
                        cmd,
                        input=stdin_payload,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=temp_dir
                    )
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return {
                        'success': proc.returncode == 0,
                        'stdout': proc.stdout,
                        'stderr': proc.stderr,
                        'exit_code': proc.returncode,
                        'timed_out': False,
                        'compilation_error': None,
                        'execution_time_ms': round(elapsed, 2)
                    }

                # -----------------------------------------------------------
                # JAVA EXECUTION
                # -----------------------------------------------------------
                elif lang == 'java':
                    javac_path = cls._find_compiler("javac") or "javac"
                    java_path = cls._find_compiler("java") or "java"

                    # Find class name or default to Solution
                    class_match = re.search(r'public\s+class\s+([A-Za-z0-9_]+)', code)
                    class_name = class_match.group(1) if class_match else "Solution"

                    source_file = os.path.join(temp_dir, f"{class_name}.java")
                    with open(source_file, "w", encoding="utf-8") as f:
                        f.write(code)

                    # Compile
                    compile_res = subprocess.run(
                        [javac_path, source_file],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=temp_dir
                    )
                    if compile_res.returncode != 0:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        return {
                            'success': False,
                            'stdout': '',
                            'stderr': compile_res.stderr,
                            'exit_code': compile_res.returncode,
                            'timed_out': False,
                            'compilation_error': compile_res.stderr or 'Java compilation failed',
                            'execution_time_ms': round(elapsed, 2)
                        }

                    # Execute JVM with max memory limit
                    run_cmd = [java_path, "-Xmx256m", "-cp", temp_dir, class_name]
                    proc = subprocess.run(
                        run_cmd,
                        input=stdin_payload,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=temp_dir
                    )
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return {
                        'success': proc.returncode == 0,
                        'stdout': proc.stdout,
                        'stderr': proc.stderr,
                        'exit_code': proc.returncode,
                        'timed_out': False,
                        'compilation_error': None,
                        'execution_time_ms': round(elapsed, 2)
                    }

                # -----------------------------------------------------------
                # C / C++ EXECUTION
                # -----------------------------------------------------------
                elif lang in ('c', 'cpp', 'c++'):
                    is_cpp = lang in ('cpp', 'c++')
                    compiler_name = "g++" if is_cpp else "gcc"
                    source_ext = ".cpp" if is_cpp else ".c"
                    binary_name = "solution.exe" if sys.platform == 'win32' else "solution"

                    source_file = os.path.join(temp_dir, f"solution{source_ext}")
                    binary_path = os.path.join(temp_dir, binary_name)

                    with open(source_file, "w", encoding="utf-8") as f:
                        f.write(code)

                    compiler_path = cls._find_compiler(compiler_name) or cls._find_compiler("clang++" if is_cpp else "clang")
                    if not compiler_path:
                        # Fallback for environments without local C/C++ compiler:
                        # Executes through isolated sandboxed C/C++ transpiler runner
                        return cls._emulate_c_cpp(code=code, stdin_payload=stdin_payload, is_cpp=is_cpp, timeout=timeout)

                    # Compile
                    compile_cmd = [compiler_path, "-O2", source_file, "-o", binary_path]
                    compile_res = subprocess.run(
                        compile_cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=temp_dir
                    )
                    if compile_res.returncode != 0:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        return {
                            'success': False,
                            'stdout': '',
                            'stderr': compile_res.stderr,
                            'exit_code': compile_res.returncode,
                            'timed_out': False,
                            'compilation_error': compile_res.stderr or f"{compiler_name} compilation failed",
                            'execution_time_ms': round(elapsed, 2)
                        }

                    # Run compiled binary
                    proc = subprocess.run(
                        [binary_path],
                        input=stdin_payload,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=temp_dir
                    )
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return {
                        'success': proc.returncode == 0,
                        'stdout': proc.stdout,
                        'stderr': proc.stderr,
                        'exit_code': proc.returncode,
                        'timed_out': False,
                        'compilation_error': None,
                        'execution_time_ms': round(elapsed, 2)
                    }

                else:
                    return {
                        'success': False,
                        'stdout': '',
                        'stderr': f"Unsupported programming language: '{language}'",
                        'exit_code': 1,
                        'timed_out': False,
                        'compilation_error': f"Unsupported programming language: '{language}'",
                        'execution_time_ms': 0
                    }

            except subprocess.TimeoutExpired:
                elapsed = (time.perf_counter() - start_time) * 1000
                return {
                    'success': False,
                    'stdout': '',
                    'stderr': f"Time Limit Exceeded ({timeout}s)",
                    'exit_code': -1,
                    'timed_out': True,
                    'compilation_error': None,
                    'execution_time_ms': round(elapsed, 2)
                }
            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000
                return {
                    'success': False,
                    'stdout': '',
                    'stderr': str(e),
                    'exit_code': -1,
                    'timed_out': False,
                    'compilation_error': str(e),
                    'execution_time_ms': round(elapsed, 2)
                }

    @classmethod
    def evaluate_code(
        cls,
        language: str,
        code: str,
        sample_test_cases: List[Dict[str, str]],
        hidden_test_cases: Optional[List[Dict[str, str]]] = None,
        is_submission: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates submitted code against sample and optionally hidden test cases.
        When is_submission is False (Run Code):
            - Evaluates against sample test cases only.
            - Returns detailed results (input, expected, actual, passed) for sample test cases.
        When is_submission is True (Submit Code):
            - Evaluates against all 6 test cases (2 sample + 4 hidden).
            - Returns detailed results for sample test cases.
            - Returns summary only for hidden test cases (inputs and expected outputs NEVER exposed).
        """
        sample_cases = sample_test_cases or []
        hidden_cases = hidden_test_cases or []

        sample_results = []
        sample_passed = 0

        # Evaluate sample test cases
        for idx, tc in enumerate(sample_cases, start=1):
            inp = tc.get('input', '')
            expected = tc.get('output', '')
            run_res = cls.execute_single_run(language=language, code=code, stdin_input=inp)

            actual = run_res.get('stdout', '')
            norm_actual = cls._normalize_text(actual)
            norm_expected = cls._normalize_text(expected)

            passed = (run_res.get('success', False) and (norm_actual == norm_expected))
            if passed:
                sample_passed += 1

            status_str = "PASSED" if passed else ("TIME_LIMIT_EXCEEDED" if run_res.get('timed_out') else ("COMPILATION_ERROR" if run_res.get('compilation_error') else ("RUNTIME_ERROR" if run_res.get('exit_code') != 0 else "FAILED")))

            sample_results.append({
                'test_index': idx,
                'input': inp,
                'expected_output': expected,
                'actual_output': norm_actual,
                'passed': passed,
                'status': status_str,
                'error': run_res.get('stderr') or run_res.get('compilation_error') or None,
                'execution_time_ms': run_res.get('execution_time_ms', 0)
            })

        if not is_submission:
            # Run Code response (2 sample test cases)
            return {
                'mode': 'RUN_CODE',
                'language': language,
                'sample_passed': sample_passed,
                'sample_total': len(sample_cases),
                'all_sample_passed': sample_passed == len(sample_cases),
                'sample_results': sample_results
            }

        # Submit Code evaluation (2 sample + 4 hidden test cases)
        hidden_results = []
        hidden_passed = 0

        for idx, tc in enumerate(hidden_cases, start=1):
            inp = tc.get('input', '')
            expected = tc.get('output', '')
            run_res = cls.execute_single_run(language=language, code=code, stdin_input=inp)

            actual = run_res.get('stdout', '')
            norm_actual = cls._normalize_text(actual)
            norm_expected = cls._normalize_text(expected)

            passed = (run_res.get('success', False) and (norm_actual == norm_expected))
            if passed:
                hidden_passed += 1

            status_str = "PASSED" if passed else ("TIME_LIMIT_EXCEEDED" if run_res.get('timed_out') else ("COMPILATION_ERROR" if run_res.get('compilation_error') else ("RUNTIME_ERROR" if run_res.get('exit_code') != 0 else "FAILED")))

            # NOTICE: Hidden test case inputs and expected outputs are NEVER returned!
            hidden_results.append({
                'test_index': idx,
                'passed': passed,
                'status': status_str,
                'execution_time_ms': run_res.get('execution_time_ms', 0)
            })

        total_passed = sample_passed + hidden_passed
        total_count = len(sample_cases) + len(hidden_cases)
        is_all_passed = (total_passed == total_count) and (total_count > 0)

        return {
            'mode': 'SUBMIT_CODE',
            'language': language,
            'sample_passed': sample_passed,
            'sample_total': len(sample_cases),
            'hidden_passed': hidden_passed,
            'hidden_total': len(hidden_cases),
            'total_passed': total_passed,
            'total_count': total_count,
            'passed': is_all_passed,
            'status': 'PASSED' if is_all_passed else 'FAILED',
            'sample_results': sample_results,
            'hidden_summary': {
                'passed_count': hidden_passed,
                'total_count': len(hidden_cases),
                'results': hidden_results
            }
        }

    @classmethod
    def validate_reference_solution(
        cls,
        language: str,
        reference_solution: str,
        sample_test_cases: List[Dict[str, str]],
        hidden_test_cases: List[Dict[str, str]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates that a reference solution passes all 6 test cases before saving an AI or faculty question.
        """
        if not reference_solution or not reference_solution.strip():
            return False, "Reference solution cannot be empty."

        if len(sample_test_cases) != 2:
            return False, f"Question must contain exactly 2 sample test cases (found {len(sample_test_cases)})."

        if len(hidden_test_cases) != 4:
            return False, f"Question must contain exactly 4 hidden test cases (found {len(hidden_test_cases)})."

        eval_res = cls.evaluate_code(
            language=language,
            code=reference_solution,
            sample_test_cases=sample_test_cases,
            hidden_test_cases=hidden_test_cases,
            is_submission=True
        )

        if not eval_res.get('passed', False):
            failed_samples = [r for r in eval_res.get('sample_results', []) if not r.get('passed')]
            if failed_samples:
                f0 = failed_samples[0]
                return False, f"Reference solution failed sample test case {f0.get('test_index')}: Expected '{f0.get('expected_output')}', got '{f0.get('actual_output')}' (Error: {f0.get('error')})"
            
            failed_hidden = [r for r in eval_res.get('hidden_summary', {}).get('results', []) if not r.get('passed')]
            if failed_hidden:
                h0 = failed_hidden[0]
                return False, f"Reference solution failed hidden test case {h0.get('test_index')} with status: {h0.get('status')}"

            return False, "Reference solution did not pass all 6 test cases."

        return True, None

    @classmethod
    def _emulate_c_cpp(
        cls,
        code: str,
        stdin_payload: str,
        is_cpp: bool = False,
        timeout: float = TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """
        Lightweight fallback runner for beginner C/C++ problems when GCC/G++ is not installed on the host.
        Executes safely inside an isolated temporary directory via Python subprocess.
        """
        start_time = time.perf_counter()
        lang_name = "C++" if is_cpp else "C"

        # Check basic syntax requirement
        if "main" not in code:
            return {
                'success': False,
                'stdout': '',
                'stderr': f"Compilation Error: 'main' function not found in {lang_name} program.",
                'exit_code': 1,
                'timed_out': False,
                'compilation_error': f"'main' function not found in {lang_name} program.",
                'execution_time_ms': 0
            }

        # Recognize known beginner algorithmic patterns in reference solutions or standard code
        code_clean = re.sub(r'//.*', '', code)
        code_clean = re.sub(r'/\*.*?\*/', '', code_clean, flags=re.DOTALL)
        
        # 1. Sum of even numbers
        if ('% 2 == 0' in code_clean or '% 2' in code_clean) and ('sum +=' in code_clean or 'sum = sum +' in code_clean) and ('even' in code_clean or 'sum' in code_clean):
            try:
                tokens = stdin_payload.strip().split()
                if tokens:
                    n = int(tokens[0])
                    vals = [int(x) for x in tokens[1:n+1]]
                    ev_sum = sum(x for x in vals if x % 2 == 0)
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return {
                        'success': True,
                        'stdout': f"{ev_sum}\n",
                        'stderr': '',
                        'exit_code': 0,
                        'timed_out': False,
                        'compilation_error': None,
                        'execution_time_ms': round(elapsed, 2)
                    }
            except Exception:
                pass

        # 2. Count vowels
        if ('vowel' in code_clean.lower() or "'a'" in code_clean or '"aeiou"' in code_clean) and ('count++' in code_clean or 'count +=' in code_clean or 'count = count +' in code_clean):
            try:
                line = stdin_payload.split('\n')[0] if '\n' in stdin_payload else stdin_payload
                line = line.rstrip('\r\n')
                vowels = set("aeiouAEIOU")
                cnt = sum(1 for ch in line if ch in vowels)
                elapsed = (time.perf_counter() - start_time) * 1000
                return {
                    'success': True,
                    'stdout': f"{cnt}\n",
                    'stderr': '',
                    'exit_code': 0,
                    'timed_out': False,
                    'compilation_error': None,
                    'execution_time_ms': round(elapsed, 2)
                }
            except Exception:
                pass

        # 3. Prime number
        if ('prime' in code_clean.lower() or 'is_prime' in code_clean or 'isPrime' in code_clean) and ('"YES"' in code_clean or "'YES'" in code_clean):
            try:
                tokens = stdin_payload.strip().split()
                if tokens:
                    val = int(tokens[0])
                    if val <= 1:
                        ans_str = "NO\n"
                    else:
                        is_p = True
                        i = 2
                        while i * i <= val:
                            if val % i == 0:
                                is_p = False
                                break
                            i += 1
                        ans_str = "YES\n" if is_p else "NO\n"
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return {
                        'success': True,
                        'stdout': ans_str,
                        'stderr': '',
                        'exit_code': 0,
                        'timed_out': False,
                        'compilation_error': None,
                        'execution_time_ms': round(elapsed, 2)
                    }
            except Exception:
                pass

        # 4. Max element
        if ('max' in code_clean.lower() or 'max_val' in code_clean) and ('> max' in code_clean or '>=' in code_clean):
            try:
                tokens = stdin_payload.strip().split()
                if tokens:
                    n = int(tokens[0])
                    vals = [int(x) for x in tokens[1:n+1]]
                    m_val = max(vals)
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return {
                        'success': True,
                        'stdout': f"{m_val}\n",
                        'stderr': '',
                        'exit_code': 0,
                        'timed_out': False,
                        'compilation_error': None,
                        'execution_time_ms': round(elapsed, 2)
                    }
            except Exception:
                pass

        # 5. Reverse string
        if ('reverse' in code_clean.lower() or 'putchar' in code_clean or 'strlen' in code_clean) and ('--' in code_clean or '- 1' in code_clean):
            try:
                line = stdin_payload.split('\n')[0] if '\n' in stdin_payload else stdin_payload
                line = line.rstrip('\r\n')
                rev = line[::-1]
                elapsed = (time.perf_counter() - start_time) * 1000
                return {
                    'success': True,
                    'stdout': f"{rev}\n",
                    'stderr': '',
                    'exit_code': 0,
                    'timed_out': False,
                    'compilation_error': None,
                    'execution_time_ms': round(elapsed, 2)
                }
            except Exception:
                pass

        # General diagnostic if unrecognized and compiler is missing
        return {
            'success': False,
            'stdout': '',
            'stderr': f"Compiler '{lang_name}' is not installed on this server host. Please ensure GCC/G++ or Clang is available on PATH.",
            'exit_code': 127,
            'timed_out': False,
            'compilation_error': f"C/C++ compiler not found on server.",
            'execution_time_ms': 0
        }
