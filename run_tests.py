#!/usr/bin/env python3
"""
run_tests.py

Run lexical.py (in Lexical/) on Tests/T01..T10 without modifying the Tests/ folders.
For each test, the scanner runs in a temporary directory containing a copy of input.txt,
so the original test files are never changed.
"""

import os
import sys
import subprocess
import difflib
import shutil
import tempfile
from pathlib import Path

# Config
NUM_TESTS = 10
TESTS_DIR = Path("Tests")
LEXICAL_SCRIPT = Path("Lexical") / "lexical.py"  # edit if your scanner is named differently
EXPECTED_FILES = ["tokens.txt", "lexical_errors.txt", "symbol_table.txt"]
RUN_TIMEOUT_SECONDS = 10  # adjust if needed

def read_file_safe(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        return None
    except Exception as e:
        return [f"<ERROR READING FILE: {e}>\n"]

def unified_diff_str(expected_lines, produced_lines, fromfile, tofile):
    if expected_lines is None and produced_lines is None:
        return ""  # nothing expected and nothing produced => treat as no diff
    if expected_lines is None:
        return f"Expected file {fromfile} is MISSING; produced {tofile} exists.\n"
    if produced_lines is None:
        return f"Produced file {tofile} is MISSING; expected {fromfile} exists.\n"
    diff = list(difflib.unified_diff(expected_lines, produced_lines,
                                     fromfile=fromfile, tofile=tofile, lineterm=''))
    return "\n".join(diff)

def run_single_test(test_dir: Path, lexical_script: Path):
    print(f"\n=== Running test: {test_dir} ===")

    # 1) Read expected files BEFORE running scanner
    expected_contents = {}
    for fname in EXPECTED_FILES:
        p = test_dir / fname
        expected_contents[fname] = read_file_safe(p)

    # Ensure the input exists in the test folder
    input_path = test_dir / "input.txt"
    if not input_path.exists():
        print(f"ERROR: test {test_dir} missing input.txt; skipping.")
        return False

    # 2) Prepare a temporary working directory (so we don't touch test folder files)
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)

        # Copy input.txt to temporary directory
        shutil.copy2(str(input_path), str(tmpdir / "input.txt"))

        # Run the lexical scanner in the temporary directory (cwd=tmpdir).
        # We pass the absolute path to the lexical script so Python executes that file,
        # but the scanner's working directory is the temp dir (so outputs land there).
        if not lexical_script.exists():
            print(f"ERROR: lexical script not found at {lexical_script.resolve()}. Aborting test run.")
            return False

        try:
            proc = subprocess.run(
                [sys.executable, str(lexical_script.resolve())],
                cwd=str(tmpdir),
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            print(f"ERROR: scanner timed out after {RUN_TIMEOUT_SECONDS} seconds.")
            return False
        except Exception as e:
            print(f"ERROR: failed to run scanner: {e}")
            return False

        # print scanner stdout/stderr if present
        if proc.stdout.strip():
            print("--- scanner stdout ---")
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print("--- scanner stderr ---")
            print(proc.stderr.strip())

        # 3) Read produced files from temp dir
        produced_contents = {}
        for fname in EXPECTED_FILES:
            p = tmpdir / fname
            produced_contents[fname] = read_file_safe(p)

        # 4) Compare and print diffs
        all_pass = True
        for fname in EXPECTED_FILES:
            expected = expected_contents.get(fname)
            produced = produced_contents.get(fname)
            fromfile = f"{test_dir}/{fname} (expected)"
            tofile = f"{test_dir}/{fname} (produced)"
            diff = unified_diff_str(expected, produced, fromfile, tofile)
            if diff:
                all_pass = False
                print(f"\n--- DIFF for {fname} ---")
                print(diff)
            else:
                print(f"\n{fname}: OK (no differences)")

        # 5) Return summary boolean (treat nonzero returncode as failure)
        if all_pass and proc.returncode == 0:
            print(f"\n>>> TEST {test_dir.name} PASS")
            return True
        else:
            print(f"\n>>> TEST {test_dir.name} FAIL (return code {proc.returncode})")
            return False

def main():
    root = Path.cwd()
    lexical_script = LEXICAL_SCRIPT
    if not lexical_script.exists():
        # try relative to this script's directory
        script_parent = Path(__file__).parent.resolve()
        maybe = (script_parent / LEXICAL_SCRIPT).resolve()
        if maybe.exists():
            lexical_script = maybe

    print(f"Using lexical scanner: {lexical_script.resolve()}")
    print(f"Tests directory: {TESTS_DIR.resolve()}\n")

    results = []
    for i in range(1, NUM_TESTS + 1):
        test_name = f"T{i:02d}"
        test_dir = TESTS_DIR / test_name
        if not test_dir.exists():
            print(f"Warning: missing test folder {test_dir}; skipping.")
            results.append((test_name, False, "missing"))
            continue
        ok = run_single_test(test_dir, lexical_script)
        results.append((test_name, ok, None))

    # Final summary
    passed = sum(1 for r in results if r[1] is True)
    total = len(results)
    print("\n\n==== SUMMARY ====")
    for name, ok, reason in results:
        status = "PASS" if ok else f"FAIL ({reason})" if reason else "FAIL"
        print(f"{name}: {status}")
    print(f"\nPassed {passed}/{total} tests.")

if __name__ == "__main__":
    main()
