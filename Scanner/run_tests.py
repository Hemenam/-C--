#!/usr/bin/env python3
"""
run_tests.py

Run Lexical/lexical.py on Tests/T01..T10 without modifying the Tests/ folders.
Normalization of both expected and produced files is ENABLED by default.

UPDATED LOGIC:
1. symbol_table.txt is SORTED alphabetically.
2. Leading indices (e.g., "1. ", "10. ") are STRIPPED from symbol_table.txt
   before comparison. This ensures that if the identifiers are correct, 
   the test passes regardless of the ID number assigned.

Place this script in the repo root.
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
LEXICAL_SCRIPT = "compiler.py"
EXPECTED_FILES = ["parse_tree.txt", "syntax_errors.txt"]
RUN_TIMEOUT_SECONDS = 15

# ---------- Helpers: read file safely ----------
def read_file_safe(path: Path):
    """Return list of lines (with newline) or None if missing."""
    try:
        with path.open("rb") as f:
            raw = f.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        return text.splitlines(True)
    except FileNotFoundError:
        return None
    except Exception as e:
        return [f"<ERROR READING FILE: {e}>\n"]

# ---------- Normalization ----------
_whitespace_re = re.compile(r"[ \t\f\v]+")
_symbol_index_re = re.compile(r"^\d+\.\s*") # Matches "1. ", "12. " at start of line

def normalize_text_lines(lines):
    if lines is None:
        return None
    joined = "".join(lines)
    raw_lines = joined.splitlines()
    normalized = []
    for ln in raw_lines:
        ln_stripped = ln.strip()
        ln_collapsed = _whitespace_re.sub(" ", ln_stripped)
        normalized.append(ln_collapsed + "\n")
    while normalized and normalized[-1].strip() == "":
        normalized.pop()
    return normalized

def strip_symbol_indices(lines):
    """Remove '1. ', '2. ' prefixes from lines to compare only identifier names."""
    if lines is None: 
        return None
    cleaned = []
    for ln in lines:
        # Remove the number and dot at the start (e.g. "1. break" -> "break")
        new_ln = _symbol_index_re.sub("", ln)
        cleaned.append(new_ln)
    return cleaned

# ---------- Diff helper ----------
def unified_diff_str(expected_lines, produced_lines, fromfile, tofile):
    if expected_lines is None and produced_lines is None:
        return ""
    if expected_lines is None:
        return f"Expected file {fromfile} is MISSING; produced {tofile} exists.\n"
    if produced_lines is None:
        return f"Produced file {tofile} is MISSING; expected {fromfile} exists.\n"
    diff = list(difflib.unified_diff(expected_lines, produced_lines,
                                     fromfile=fromfile, tofile=tofile, lineterm=''))
    return "\n".join(diff)

# ---------- Single test runner ----------
def run_single_test(test_dir: Path, lexical_script: Path, normalize: bool):
    display_test_dir = str(test_dir).replace("\\", "/")
    print(f"\n=== Running test: {display_test_dir} ===")

    # Read expected files
    expected_contents = {fname: read_file_safe(test_dir / fname) for fname in EXPECTED_FILES}

    input_path = test_dir / "input.txt"
    if not input_path.exists():
        print(f"ERROR: test {display_test_dir} missing input.txt; skipping.")
        return False

    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        shutil.copy2(str(input_path), str(tmpdir / "input.txt"))

        if not lexical_script.exists():
            print(f"ERROR: script not found at {lexical_script}. Aborting.")
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
            print(f"ERROR: scanner timed out.")
            return False
        except Exception as e:
            print(f"ERROR: failed to run scanner: {e}")
            return False

        if proc.stdout.strip():
            print("--- scanner stdout ---")
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print("--- scanner stderr ---")
            print(proc.stderr.strip())

        produced_contents = {fname: read_file_safe(tmpdir / fname) for fname in EXPECTED_FILES}

        all_pass = True
        for fname in EXPECTED_FILES:
            expected = expected_contents.get(fname)
            produced = produced_contents.get(fname)

            if normalize:
                lines_exp = normalize_text_lines(expected)
                lines_prod = normalize_text_lines(produced)
            else:
                lines_exp = list(expected) if expected else None
                lines_prod = list(produced) if produced else None

            # --- SPECIAL HANDLING FOR symbol_table.txt ---
            label_extra = ""
            if fname == "symbol_table.txt":
                # 1. Strip the "1. ", "2. " prefixes so we only compare variable names
                lines_exp = strip_symbol_indices(lines_exp)
                lines_prod = strip_symbol_indices(lines_prod)
                
                # 2. Sort alphabetical so order doesn't matter
                if lines_exp: lines_exp.sort()
                if lines_prod: lines_prod.sort()
                
                label_extra = " [Indices Ignored & Sorted]"

            # Labels for diff
            norm_label = ' , normalized' if normalize else ''
            fromfile_label = f"{display_test_dir}/{fname} (expected{norm_label}{label_extra})"
            tofile_label = f"{display_test_dir}/{fname} (produced{norm_label}{label_extra})"

            diff = unified_diff_str(lines_exp, lines_prod, fromfile_label, tofile_label)

            if diff:
                all_pass = False
                print(f"\n--- DIFF for {fname} ---")
                print(diff)
            else:
                print(f"\n{fname}: OK")

        if all_pass and proc.returncode == 0:
            print(f"\n>>> TEST {display_test_dir} PASS")
            return True
        else:
            print(f"\n>>> TEST {display_test_dir} FAIL (return code {proc.returncode})")
            return False

# ---------- Main ----------
def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Disable normalization.")
    parser.add_argument("-t", "--tests", type=int, default=NUM_TESTS)
    args = parser.parse_args(argv)

    lexical_script = LEXICAL_SCRIPT
    if not lexical_script.exists():
        script_parent = Path(__file__).parent.resolve()
        maybe = (script_parent / LEXICAL_SCRIPT).resolve()
        if maybe.exists(): lexical_script = maybe

    print(f"Scanner: {lexical_script.resolve()}")
    
    results = []
    for i in range(1, args.tests + 1):
        test_name = f"T{i:02d}"
        test_dir = TESTS_DIR / test_name
        if not test_dir.exists():
            results.append((test_name, False, "missing"))
            continue
        ok = run_single_test(test_dir, lexical_script, not args.strict)
        results.append((test_name, ok, None))

    print("\n\n==== SUMMARY ====")
    passed = 0
    for name, ok, reason in results:
        if ok: passed += 1
        status = "PASS" if ok else f"FAIL ({reason or 'diff'})"
        print(f"{name}: {status}")
    print(f"\nPassed {passed}/{len(results)} tests.")

if __name__ == "__main__":
    main(sys.argv[1:])