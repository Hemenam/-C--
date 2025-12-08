#!/usr/bin/env python3
"""
run_tests.py

Run Lexical/lexical.py on Tests/T01..T10 without modifying the Tests/ folders.
Optionally normalize whitespace & line endings before diffing with --normalize / -n.

Place this script in the repo root (siblings: Lexical/ and Tests/).
"""

import os
import sys
import subprocess
import difflib
import shutil
import tempfile
import argparse
import re
from pathlib import Path

# ---------- Configuration ----------
NUM_TESTS = 1
TESTS_DIR = Path("Tests")
LEXICAL_SCRIPT = Path("Lexical") / "lexical.py"   # change if your scanner filename differs
EXPECTED_FILES = ["tokens.txt", "lexical_errors.txt", "symbol_table.txt"]
RUN_TIMEOUT_SECONDS = 15  # adjust if your scanner needs more time

# ---------- Helpers: read file safely ----------
def read_file_safe(path: Path):
    """Return list of lines (with newline) or None if missing. Decode tolerant."""
    try:
        with path.open("rb") as f:
            raw = f.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        return text.splitlines(True)  # preserve line endings through splitlines(True)
    except FileNotFoundError:
        return None
    except Exception as e:
        return [f"<ERROR READING FILE: {e}>\n"]

# ---------- Normalization ----------
_whitespace_re = re.compile(r"[ \t\f\v]+")  # horizontal whitespace runs (space, tab, formfeed, vtab)

def normalize_text_lines(lines):
    """
    Normalize lines:
      - convert CRLF/CR to LF by using splitlines
      - strip leading/trailing whitespace on each line
      - collapse internal horizontal whitespace runs to a single space
      - ensure each output line ends with '\n'
      - remove trailing blank lines at EOF
    Input: list of lines (may include newline chars) or None.
    Output: list of normalized lines (each ending with '\n') or None.
    """
    if lines is None:
        return None
    # Join and re-split to normalize different newline styles
    joined = "".join(lines)
    raw_lines = joined.splitlines()  # no newline chars preserved here
    normalized = []
    for ln in raw_lines:
        ln_stripped = ln.strip()                # remove leading/trailing whitespace
        ln_collapsed = _whitespace_re.sub(" ", ln_stripped)  # collapse internal horizontal whitespace
        normalized.append(ln_collapsed + "\n")
    # Remove trailing blank lines
    while normalized and normalized[-1].strip() == "":
        normalized.pop()
    return normalized

# ---------- Diff helper ----------
def unified_diff_str(expected_lines, produced_lines, fromfile, tofile):
    if expected_lines is None and produced_lines is None:
        return ""  # treat as no diff
    if expected_lines is None:
        return f"Expected file {fromfile} is MISSING; produced {tofile} exists.\n"
    if produced_lines is None:
        return f"Produced file {tofile} is MISSING; expected {fromfile} exists.\n"
    diff = list(difflib.unified_diff(expected_lines, produced_lines,
                                     fromfile=fromfile, tofile=tofile, lineterm=''))
    return "\n".join(diff)

# ---------- Single test runner ----------
def run_single_test(test_dir: Path, lexical_script: Path, normalize: bool):
    print(f"\n=== Running test: {test_dir} ===")

    # Read expected files BEFORE running scanner
    expected_contents = {fname: read_file_safe(test_dir / fname) for fname in EXPECTED_FILES}

    # Ensure input exists
    input_path = test_dir / "input.txt"
    if not input_path.exists():
        print(f"ERROR: test {test_dir} missing input.txt; skipping.")
        return False

    # Create temporary working directory (scanner will write outputs here)
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        shutil.copy2(str(input_path), str(tmpdir / "input.txt"))

        if not lexical_script.exists():
            print(f"ERROR: lexical script not found at {lexical_script.resolve()}. Aborting test run.")
            return False

        # Run scanner with cwd set to tmpdir
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

        # Print scanner stdout/stderr (helpful for debugging)
        if proc.stdout.strip():
            print("--- scanner stdout ---")
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print("--- scanner stderr ---")
            print(proc.stderr.strip())

        # Read produced files from temp dir
        produced_contents = {fname: read_file_safe(tmpdir / fname) for fname in EXPECTED_FILES}

        if normalize:
            print("[Normalization enabled] Normalizing whitespace and line endings before diffing.")

        # Compare each expected vs produced (normalized or raw)
        all_pass = True
        for fname in EXPECTED_FILES:
            expected = expected_contents.get(fname)
            produced = produced_contents.get(fname)

            if normalize:
                expected_norm = normalize_text_lines(expected) if expected is not None else None
                produced_norm = normalize_text_lines(produced) if produced is not None else None
                diff = unified_diff_str(expected_norm, produced_norm,
                                        f"{test_dir}/{fname} (expected, normalized)",
                                        f"{test_dir}/{fname} (produced, normalized)")
            else:
                diff = unified_diff_str(expected, produced,
                                        f"{test_dir}/{fname} (expected)",
                                        f"{test_dir}/{fname} (produced)")

            if diff:
                all_pass = False
                print(f"\n--- DIFF for {fname} ---")
                print(diff)
            else:
                print(f"\n{fname}: OK (no differences)")

        # Consider non-zero return code of scanner as a failure
        if all_pass and proc.returncode == 0:
            print(f"\n>>> TEST {test_dir.name} PASS")
            return True
        else:
            print(f"\n>>> TEST {test_dir.name} FAIL (return code {proc.returncode})")
            return False

# ---------- Main ----------
def main(argv):
    parser = argparse.ArgumentParser(description="Run lexical scanner tests (no modification of Tests/).")
    parser.add_argument("-n", "--normalize", action="store_true",
                        help="Normalize whitespace and line endings before diffing")
    parser.add_argument("-t", "--tests", type=int, default=NUM_TESTS,
                        help=f"Number of tests to run (default {NUM_TESTS})")
    args = parser.parse_args(argv)

    # Resolve lexical script path (try relative to caller)
    lexical_script = LEXICAL_SCRIPT
    if not lexical_script.exists():
        script_parent = Path(__file__).parent.resolve()
        maybe = (script_parent / LEXICAL_SCRIPT).resolve()
        if maybe.exists():
            lexical_script = maybe

    print(f"Using lexical scanner: {lexical_script.resolve()}")
    print(f"Tests directory: {TESTS_DIR.resolve()}\n")

    results = []
    for i in range(1, args.tests + 1):
        test_name = f"T{i:02d}"
        test_dir = TESTS_DIR / test_name
        if not test_dir.exists():
            print(f"Warning: missing test folder {test_dir}; skipping.")
            results.append((test_name, False, "missing"))
            continue
        ok = run_single_test(test_dir, lexical_script, args.normalize)
        results.append((test_name, ok, None))

    # Final summary
    passed = sum(1 for r in results if r[1] is True)
    total = len(results)
    print("\n\n==== SUMMARY ====")
    for name, ok, reason in results:
        if reason:
            status = f"FAIL ({reason})"
        else:
            status = "PASS" if ok else "FAIL"
        print(f"{name}: {status}")
    print(f"\nPassed {passed}/{total} tests.")

if __na
