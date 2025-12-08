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

        # Track last returned token: (toktype, lexeme, end_pos, lineno)
        # end_pos is the scanner position (self.pos) immediately after the token
        self.last_token = None

        # Flag used to tell main() to remove the previously emitted token from lines_output
        self._remove_last_token = False
        self._removed_last_token_lexeme = None
        self._removed_last_token_lineno = None

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

    def remove_id_from_symbol_table_if_present(self, lexeme, lineno):
        """Remove previously-added identifier lexeme from symbol table if it matches an ID and first_seen==lineno.
           This prevents illegal constructs like 'invalid@char' from leaving 'invalid' in the symbol table.
        """
        if lexeme in self.symbol_table:
            entry = self.symbol_table[lexeme]
            if entry['class'] == TokenType.ID:
                # Remove the ID entry unconditionally (safer), or you can check first_seen==lineno if desired.
                del self.symbol_table[lexeme]

    def clear_remove_flag(self):
        self._remove_last_token = False
        self._removed_last_token_lexeme = None
        self._removed_last_token_lineno = None

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
                # clear last_token and return EOF
                self.last_token = None
                return (TokenType.EOF, "EOF", self.lineno)

            # Special check: '*/' outside a comment should be treated as stray closing comment
            if char == '*' and self.peek(1) == '/':
                start_ln = self.lineno
                self.advance(); self.advance()
                self.log_error(start_ln, "*/", "Stray closing comment")
                # reset last_token (no real token produced)
                self.last_token = None
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
                    # comment is ignored for tokenization
                    self.last_token = None
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
                        # Log open comment at EOF with a concise generic thrown string
                        thrown = "/* Unclosed ..."
                        self.log_error(start_line, thrown, "Open comment at EOF")
                        # EOF reached after open comment
                        self.last_token = None
                        return (TokenType.EOF, "EOF", self.lineno)
                    self.last_token = None
                    continue

                # Case: Division / (if '/' is a symbol)
                else:
                    lex = self.advance()
                    self.last_token = (TokenType.SYMBOL, lex, self.pos, self.lineno)
                    return (TokenType.SYMBOL, lex, self.lineno)

            # 3. Handle Identifiers and Keywords (Starts with Letter or Underscore)
            if char.isalpha() or char == '_':
                lexeme = ""
                start_ln = self.lineno
                while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                    lexeme += self.advance()

                if lexeme in KEYWORDS:
                    # Add keyword to symbol table (it's already init'd, but ensure presence)
                    self.add_symbol(lexeme, TokenType.KEYWORD, None)
                    self.last_token = (TokenType.KEYWORD, lexeme, self.pos, start_ln)
                    return (TokenType.KEYWORD, lexeme, start_ln)
                else:
                    # Identifier: add to symbol table with first seen line if new
                    self.add_symbol(lexeme, TokenType.ID, start_ln)
                    self.last_token = (TokenType.ID, lexeme, self.pos, start_ln)
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
                    self.last_token = None
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
                    self.last_token = None
                    return self.get_next_token()

                self.last_token = (TokenType.NUM, lexeme, self.pos, start_line)
                return (TokenType.NUM, lexeme, start_line)

            # 5. Handle Symbols (including multi-char ==)
            if char == '=':
                if self.peek(1) == '=':
                    lexeme = self.advance() + self.advance()
                    self.last_token = (TokenType.SYMBOL, lexeme, self.pos, self.lineno)
                    return (TokenType.SYMBOL, lexeme, self.lineno)
                else:
                    lex = self.advance()
                    self.last_token = (TokenType.SYMBOL, lex, self.pos, self.lineno)
                    return (TokenType.SYMBOL, lex, self.lineno)

            if char in SYMBOLS:
                lex = self.advance()
                self.last_token = (TokenType.SYMBOL, lex, self.pos, self.lineno)
                return (TokenType.SYMBOL, lex, self.lineno)

            # 6. Illegal Character (can't begin any token)
            ch = self.peek()
            if ch is not None:
                start_ln = self.lineno

                # We will build a thrown string that includes any contiguous identifier-like parts
                # immediately before and after the illegal char (no whitespace).
                start_pos = self.pos  # position of the illegal character in src

                # Look back for an alnum/_ contiguous left part
                left = ""
                if start_pos - 1 >= 0:
                    i = start_pos - 1
                    # include letters/digits/underscore contiguous to the left
                    while i >= 0 and (self.src[i].isalnum() or self.src[i] == '_'):
                        i -= 1
                    # i stopped at non-id char (or -1). left substring is (i+1 .. start_pos-1)
                    if (i + 1) <= (start_pos - 1):
                        left = self.src[i+1:start_pos]

                # Now consume the illegal char itself
                illegal_char = self.advance()  # consumes the illegal char
                thrown = illegal_char

                # If there's a left part (e.g., 'invalid' from 'invalid@...'), prepend it
                if left:
                    thrown = left + thrown

                # Look forward for an alnum/_ contiguous right part and consume it
                right = ""
                while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                    right += self.advance()
                if right:
                    thrown += right

                # If the illegal char occurs immediately after a previously returned identifier token
                # and that identifier matches the left part, then the identifier must be removed
                # from the tokens output and from the symbol table.
                adjacent = False
                last_lexeme = None
                last_ln = None
                if self.last_token is not None:
                    last_ttype, last_toklex, last_endpos, last_ln = self.last_token
                    # last_endpos is the scanner position immediately after that token was formed.
                    # The illegal char's original start_pos should match last_endpos for adjacency.
                    if last_ttype == TokenType.ID and last_endpos == start_pos and left and last_toklex == left:
                        adjacent = True
                        last_lexeme = last_toklex

                # If adjacent, set removal flags to tell main() to remove the earlier token from output.
                if adjacent:
                    self._remove_last_token = True
                    self._removed_last_token_lexeme = last_lexeme
                    self._removed_last_token_lineno = last_ln
                    # Also remove the ID from the symbol table to prevent it lingering there.
                    self.remove_id_from_symbol_table_if_present(last_lexeme, last_ln)

                # Log the illegal-character error with the full thrown string
                self.log_error(start_ln, thrown, "Illegal character")

                # Panic mode: consume until token start (excluding chars already consumed)
                extra = self._panic_consume_until_token_start()
                if extra:
                    # If panic consumed extra junk, append it to thrown in the recorded error
                    thrown_full = thrown + extra
                    self.lex_errors[-1] = (start_ln, thrown_full, "Illegal character")

                # After recording the illegal-character error, reset last_token and continue scanning
                self.last_token = None
                return self.get_next_token()

        # End while loop -> EOF
        self.last_token = None
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

        # If scanner indicates a previously emitted ID must be removed from output, do it now.
        if scanner._remove_last_token:
            lex = scanner._removed_last_token_lexeme
            ln = scanner._removed_last_token_lineno
            # Remove the most-recent occurrence of that token lexeme on that line (if present)
            if ln in lines_output:
                token_repr_to_remove = f"({TokenType.ID}, {lex})"
                # remove the first matching occurrence from the end (most recently added)
                for i in range(len(lines_output[ln]) - 1, -1, -1):
                    if lines_output[ln][i] == token_repr_to_remove:
                        del lines_output[ln][i]
                        # If that leaves the line with no tokens, remove the key
                        if not lines_output[ln]:
                            del lines_output[ln]
                        break
            # Clear the flag
            scanner.clear_remove_flag()

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
