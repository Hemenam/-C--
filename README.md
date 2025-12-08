# README.md

## Compiler Scanner — Programming Assignment I (C-minus Scanner)

Mohammad Jafaripour — **401105797**
Mohammadamin Heidari _ **401170553**

This repository implements the **Scanner** (lexical analyzer) for a one-pass compiler for a simplified C language ("C-minus"), as described in the course Programming Assignment I (Scanner) for *40-414 — Compiler Design*. The README below summarizes the assignment requirements, expected behavior, input/output format, and how to run and test the scanner. This README follows the specification in the uploaded assignment document. 

---

## Project overview

* Goal: implement a robust lexical analyzer in **Python** that reads a C-minus program from `input.txt` and produces:

  * `tokens.txt` — tokenized output (line by line),
  * `symbol_table.txt` — symbol table (keywords + identifiers),
  * `lexical_errors.txt` — reported lexical errors (if any).
* Language: Python (targeted to run with **Python 3.12** on Ubuntu).
* Main function: `get_next_token()` — advances through the input and returns the next token as a pair `(TokenType, TokenString)`.
* The scanner must operate with at most **one lookahead** character for token disambiguation (e.g., `=` vs `==`). 

---

## Token types (recognized)

The scanner must recognize the following high-level token types and categories (matches the assignment specification):

* **NUM** — integer numbers matching `[0-9]+`. *Leading zeros (e.g., `012`) are considered malformed (error).*
* **ID** — identifiers matching `[A-Za-z_][A-Za-z0-9_]*`. Identifiers must not start with a digit; such cases should be reported as an `'Invalid identifier start'` lexical error.
* **KEYWORD** — `if`, `else`, `void`, `int`, `for`, `break`, `return`.
* **SYMBOL** — punctuation and operators, e.g. `; : , [ ] ( ) { } + - * / = < ==` (exact list per spec).
* **COMMENT** — `//` to end of line, and `/* ... */` block comments. (Comments are neither saved as tokens nor recorded in token output.)
* **WHITESPACE** — ` `, `\n`, `\r`, `\t`, `\v`, `\f` (ignored as tokens).
* All tokens may appear without spaces (e.g., `if(b==3){a=3;}` must be tokenized correctly). 

---

## Error handling

The scanner must detect lexical errors and recover using **Panic Mode**: when a lexical error is detected, the scanner must discard characters until a well-formed token is found, and log the thrown-away characters with a message and line number to `lexical_errors.txt`. Specific rules:

* **Illegal character**: when a character cannot begin any token, report it and resume at the next character.
* **Malformed number**: report inputs like `125d` or leading zeros like `012` (treat `012` as malformed unless it is exactly `0`).
* **Unmatched/stray comment markers**: `*/` outside a comment → report `'Stray closing comment'`; open `/*` at EOF → report `'Open comment at EOF'` (print up to the first 10 chars of the unclosed comment + `...`).
* All lexical errors are written line-by-line to `lexical_errors.txt` as `(thrown_away_string, ErrorMessage)` plus line number. If there are no lexical errors, write `No lexical errors found.` to the file. 

---

## Symbol table

* The scanner must maintain a **symbol table** containing keywords (initialized at start, sorted alphabetically) and identifiers.
* Each unique identifier or keyword has a row in `symbol_table.txt`. A sample (from the assignment) shows keywords and identifiers listed with indices. 

---

## Input / Output format (expected)

* **Input file:** `input.txt` — single C-minus program (ASCII/UTF-8). Place `input.txt` in the same directory as `compiler.py` before running.
* **Output files (produced by the scanner):**

  * `tokens.txt` — each line begins with the source line number, then the sequence of recognized tokens for that source line, each token represented as `(TOKEN_TYPE, lexeme)`; COMMENT and WHITESPACE are not included. Example line from spec:

    ```
    1 (KEYWORD, void) (ID, main) (SYMBOL, () (KEYWORD, void) (SYMBOL, )) (SYMBOL, {)
    ```

    (See full sample in the assignment document.) 
  * `lexical_errors.txt` — each lexical error in a new line as `(thrown_string, Message)` with the corresponding line number; or `No lexical errors found.` if none. Example entries from spec:

    ```
    7 (3d, Malformed number)
    9 (cd!, Illegal character)
    11 (*/, Stray closing comment)
    14 (@, Illegal character)
    17 (/* open…, Open comment at EOF)
    ```


  * `symbol_table.txt` — table of keywords and identifiers (sample in spec). 

---

## Implementation notes / constraints

* **Language & runtime:** Python 3.12 (scanner will be graded by running `python compiler.py` on Ubuntu with Python 3.12). Only `anytree` may be available for future assignments; for this assignment you may use `re` but manual DFA implementation is preferred. No other external libraries are allowed. 
* **Files to submit:** at minimum `compiler.py` (which contains your scanner). If you split components into multiple files (e.g., `Scanner.py`), ensure all files are in the same directory as `compiler.py`. The grader runs `python compiler.py`. 
* Include your full name(s), student number(s), and any references as comments at the top of `compiler.py`.
* Make the code readable and free of debug prints before submission.

---

## Repository structure (recommended)

```
cminus-scanner/                # root of this repository
├─ compiler.py                 # main scanner (required)
├─ Scanner.py                  # optional: scanner implementation
├─ input.txt                   # sample input (used for local testing)
├─ tokens.txt                  # produced token output (generated)
├─ lexical_errors.txt          # produced lexical errors (generated)
├─ symbol_table.txt            # produced symbol table (generated)
├─ tests/                      # optional: additional input.txt testcases
└─ README.md                   # this file
```

---

## How to run (local testing)

1. Clone this repository and `cd` into it.
2. Put the C-minus program to scan into `input.txt` (same directory).
3. Run:

```bash
python compiler.py
```

4. Output files `tokens.txt`, `symbol_table.txt`, and `lexical_errors.txt` should appear in the same directory.

---

## Testing & grading notes

* The scanner will be tested by automated judge (Quera's Judge System) with multiple `input.txt` files (including cases with and without lexical errors). For full credit:

  * The scanner must **not crash** (uncaught exceptions are unacceptable).
  * The scanner must produce the expected output files for each test case.
  * If the scanner throws compile/run-time errors on a test case, the grade for that test case is zero. 

---

## Examples (from assignment)

* Sample input and expected `tokens.txt`, `lexical_errors.txt`, and `symbol_table.txt` examples are provided in the assignment document (use them as local test cases). 

---

## Authors

**Mohammad Jafaripour**
Student Number: **401105797**
**Mohammadamin Heidari**
Student Number: **401170553**



