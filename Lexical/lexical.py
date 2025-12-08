import sys
from collections import OrderedDict

# --- Token Definitions based on New Table ---
class TokenType:
    KEYWORD = "KEYWORD"
    ID = "ID"
    NUM = "NUM"
    SYMBOL = "SYMBOL"
    EOF = "EOF"
    ERROR = "ERROR"

# Strict Keyword List (Note: 'while' is missing from your table)
KEYWORDS = {'if', 'else', 'void', 'int', 'for', 'break', 'return'}

# Strict Symbol List
# Note: '>' is NOT included. '==' is the only 2-char symbol allowed.
SYMBOLS = {';', ':', ',', '[', ']', '(', ')', '{', '}', '+', '-', '*', '/', '=', '<', '=='}

# Whitespace characters
WHITESPACE = {' ', '\n', '\r', '\t', '\v', '\f'}


class Scanner:
    def __init__(self, source_code):
        self.src = source_code
        self.pos = 0
        self.length = len(source_code)
        self.lineno = 1
        self.errors_found = False
        self.lex_errors = []  # tuples: (lineno, thrown_string, message)

        # Symbol table: OrderedDict to preserve insertion order.
        # Each entry maps lexeme -> dict { 'class': 'KEYWORD'/'ID', 'first_seen': lineno or None }
        self.symbol_table = OrderedDict()
        self._initialize_symbol_table_with_keywords()

    def _initialize_symbol_table_with_keywords(self):
        """Initialize symbol table with keywords sorted alphabetically."""
        for kw in sorted(KEYWORDS):
            # keywords are present from the beginning; first_seen is None
            self.symbol_table[kw] = {'class': TokenType.KEYWORD, 'first_seen': None}

    def peek(self, offset=0):
        if self.pos + offset >= self.length:
            return None
        return self.src[self.pos + offset]

    def advance(self):
        if self.pos >= self.length:
            return None
        char = self.src[self.pos]
        self.pos += 1
        if char == '\n':
            self.lineno += 1
        return char

    def log_error(self, lineno, thrown, message):
        self.errors_found = True
        self.lex_errors.append((lineno, thrown, message))

    def write_errors_file(self, filename="lexical_errors.txt"):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                if not self.lex_errors:
                    f.write('No lexical errors found.\n')
                    return
                for ln, thrown, msg in self.lex_errors:
                    f.write(f"{ln}. ({thrown}, {msg})\n")
        except IOError as e:
            print(f"Error writing lexical errors file {filename}: {e}")

    def add_symbol(self, lexeme, tokclass, first_seen_line):
        """Ensure lexeme in symbol table. For IDs, store first_seen if not already present."""
        if lexeme in self.symbol_table:
            # If keyword already in table, don't overwrite first_seen (should remain None)
            # If it's already an ID, ensure first_seen is set if previously None
            entry = self.symbol_table[lexeme]
            if entry['class'] == TokenType.ID and entry['first_seen'] is None and first_seen_line is not None:
                entry['first_seen'] = first_seen_line
            return
        # New identifier: add it
        self.symbol_table[lexeme] = {'class': tokclass, 'first_seen': first_seen_line}

    def write_symbol_table(self, filename="symbol_table.txt"):
        """Write the symbol table to a file.

        Format columns: Index. Lexeme    Class    FirstSeen
        FirstSeen is '-' for keywords (initialized entries) or the line number for IDs.
        The output is sorted alphabetically by lexeme for readability (keywords were inserted sorted
        already, but ids are also sorted for consistent output).
        """
        try:
            # sort lexemes alphabetically for output
            items = sorted(self.symbol_table.items(), key=lambda x: x[0])
            with open(filename, 'w', encoding='utf-8') as f:
                for idx, (lex, meta) in enumerate(items, start=1):
                    first_seen = meta['first_seen'] if meta['first_seen'] is not None else '-'
                    f.write(f"{idx}.\t{lex}\n")
        except IOError as e:
            print(f"Error writing symbol table file {filename}: {e}")

    def _is_token_start(self, ch):
        """Return True if character ch can begin a token (or is whitespace/None)."""
        if ch is None:
            return True
        if ch in WHITESPACE:
            return True
        if ch.isalpha() or ch.isdigit() or ch == '_' or ch in SYMBOLS or ch in {'/', '*'}:
            return True
        return False

    def _panic_consume_until_token_start(self):
        """Consume characters (panic mode) until a possible token start is found.
           Returns the consumed string.
        """
        consumed = ""
        while True:
            ch = self.peek()
            if ch is None:
                break
            if self._is_token_start(ch):
                # stop before token start (token start may be whitespace or actual token char)
                break
            consumed += self.advance()
        return consumed

    def get_next_token(self):
        while self.pos < self.length:
            char = self.peek()

            # 0. Safety: if None (EOF)
            if char is None:
                return (TokenType.EOF, "EOF", self.lineno)

            # Special check: '*/' outside a comment should be treated as stray closing comment
            if char == '*' and self.peek(1) == '/':
                start_ln = self.lineno
                self.advance(); self.advance()
                self.log_error(start_ln, "*/", "Stray closing comment")
                continue

            # 1. Handle Whitespace
            if char in WHITESPACE:
                self.advance()
                continue

            # 2. Handle Comments and Division (Starts with /)
            if char == '/':
                next_char = self.peek(1)

                # Case: Line Comment //
                if next_char == '/':
                    self.advance(); self.advance()
                    comment_content = ""
                    while self.peek() is not None and self.peek() not in ['\n', '\f']:
                        comment_content += self.advance()
                    # comment is ignored for tokenization (but in the errors spec comments are a token type)
                    continue

                # Case: Block Comment /* */
                elif next_char == '*':
                    self.advance(); self.advance()  # consume '/*'
                    comment_closed = False
                    start_line = self.lineno
                    comment_chars = ""
                    while self.pos < self.length:
                        if self.peek() == '*' and self.peek(1) == '/':
                            self.advance(); self.advance()
                            comment_closed = True
                            break
                        ch = self.advance()
                        if ch is None:
                            break
                        comment_chars += ch
                    if not comment_closed:
                        # Log open comment at EOF; include at most first 10 chars of comment in thrown string
                        snippet = (comment_chars[:10] + '...') if len(comment_chars) > 10 else comment_chars
                        thrown = "/*" + snippet
                        self.log_error(start_line, thrown, "Open comment at EOF")
                        return (TokenType.EOF, "EOF", self.lineno)
                    continue

                # Case: Division / (if '/' is a symbol)
                else:
                    return (TokenType.SYMBOL, self.advance(), self.lineno)

            # 3. Handle Identifiers and Keywords (Starts with Letter or Underscore)
            if char.isalpha() or char == '_':
                lexeme = ""
                start_ln = self.lineno
                while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                    lexeme += self.advance()

                if lexeme in KEYWORDS:
                    # Add keyword to symbol table (it's already init'd, but ensure presence)
                    self.add_symbol(lexeme, TokenType.KEYWORD, None)
                    return (TokenType.KEYWORD, lexeme, start_ln)
                else:
                    # Identifier: add to symbol table with first seen line if new
                    self.add_symbol(lexeme, TokenType.ID, start_ln)
                    return (TokenType.ID, lexeme, start_ln)

            # 4. Handle Numbers
            if char.isdigit():
                start_line = self.lineno
                lexeme = self.advance()  # first digit consumed

                # Leading zero case: '0' followed by digit(s) => Malformed number
                if lexeme == '0' and self.peek() is not None and self.peek().isdigit():
                    # consume the rest of the number-like sequence
                    rest = ""
                    while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                        rest += self.advance()
                    thrown = lexeme + rest
                    self.log_error(start_line, thrown, "Malformed number")
                    # Panic mode: skip until token start
                    extra = self._panic_consume_until_token_start()
                    if extra:
                        thrown += extra
                        # Update last logged thrown to include extra snippet if any
                        self.lex_errors[-1] = (start_line, thrown, "Malformed number")
                    return self.get_next_token()

                # Consume rest of digits
                while self.peek() is not None and self.peek().isdigit():
                    lexeme += self.advance()

                # If letters/underscore follow digits -> malformed number (e.g., 125d)
                if self.peek() is not None and (self.peek().isalpha() or self.peek() == '_'):
                    # consume rest of alnum/underscore
                    rest = ""
                    while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                        rest += self.advance()
                    thrown = lexeme + rest
                    self.log_error(start_line, thrown, "Malformed number")
                    # panic consume extra non-token-start chars
                    extra = self._panic_consume_until_token_start()
                    if extra:
                        thrown += extra
                        self.lex_errors[-1] = (start_line, thrown, "Malformed number")
                    return self.get_next_token()

                return (TokenType.NUM, lexeme, start_line)

            # 5. Handle Symbols (including multi-char ==)
            if char == '=':
                if self.peek(1) == '=':
                    lexeme = self.advance() + self.advance()
                    return (TokenType.SYMBOL, lexeme, self.lineno)
                else:
                    return (TokenType.SYMBOL, self.advance(), self.lineno)

            if char in SYMBOLS:
                return (TokenType.SYMBOL, self.advance(), self.lineno)

            # 6. Illegal Character (can't begin any token)
            ch = self.peek()
            if ch is not None:
                start_ln = self.lineno
                thrown = self.advance()
                self.log_error(start_ln, thrown, "Illegal character")
                # Panic mode: consume until token start (excluding char already consumed)
                extra = self._panic_consume_until_token_start()
                if extra:
                    thrown_full = thrown + extra
                    self.lex_errors[-1] = (start_ln, thrown_full, "Illegal character")
                return self.get_next_token()

        # End while loop -> EOF
        return (TokenType.EOF, "EOF", self.lineno)


def main():
    input_file = "input.txt"
    output_file = "tokens.txt"
    errors_file = "lexical_errors.txt"
    symtab_file = "symbol_table.txt"

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        return

    scanner = Scanner(source_code)
    lines_output = {}

    while True:
        token_type, token_string, lineno = scanner.get_next_token()

        if token_type == TokenType.EOF:
            break

        token_repr = f"({token_type}, {token_string})"

        if lineno not in lines_output:
            lines_output[lineno] = []
        lines_output[lineno].append(token_repr)

    # Write tokens to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for lineno in sorted(lines_output.keys()):
                line_content = " ".join(lines_output[lineno])
                f.write(f"{lineno}. {line_content}\n")
        print(f"Tokenization complete. Output saved to {output_file}")
    except IOError as e:
        print(f"Error writing to {output_file}: {e}")

    # Write lexical errors file
    scanner.write_errors_file(errors_file)
    if scanner.lex_errors:
        print(f"Lexical errors recorded in {errors_file}")
    else:
        print(f"No lexical errors found. {errors_file} created with a success message.")

    # Write symbol table file
    scanner.write_symbol_table(symtab_file)
    print(f"Symbol table saved to {symtab_file}")


if __name__ == "__main__":
    main()
