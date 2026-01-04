# scanner_to_parse_and_errors.py
# Run: python scanner_to_parse_and_errors.py
# Produces: parse_tree.txt and syntax_errors.txt

TOKEN_TYPES = {
    'KEYWORD': 'KEYWORD',
    'ID': 'ID',
    'NUM': 'NUM',
    'SYMBOL': 'SYMBOL',
    'EOF': 'EOF',
    'ERROR': 'ERROR'
}

KEYWORDS_LIST = ['if', 'else', 'void', 'int', 'for', 'break', 'return']
SYMBOLS_LIST = [';', ':', ',', '[', ']', '(', ')', '{', '}', '+', '-', '*', '/', '=', '<', '==']
WHITESPACE_CHARS = [' ', '\n', '\r', '\t', '\v', '\f']

class Scanner:
    def __init__(self, source_code):
        self.source = source_code
        self.current_position = 0
        self.source_length = len(source_code)
        self.current_line = 1
        self.has_errors = False
        self.error_list = []
        self.symbols = {}
        self.previous_token = None
        self.should_remove_last = False
        self.token_to_remove = None
        self.line_to_remove = None
        
        for word in KEYWORDS_LIST:
            self.symbols[word] = {'type': TOKEN_TYPES['KEYWORD'], 'first_line': None}

    def look_ahead(self, steps=0):
        if self.current_position + steps >= self.source_length:
            return None
        return self.source[self.current_position + steps]

    def move_forward(self):
        if self.current_position >= self.source_length:
            return None
        current_char = self.source[self.current_position]
        self.current_position += 1
        if current_char == '\n':
            self.current_line += 1
        return current_char

    def skip_until_valid(self):
        skipped = ""
        while True:
            next_char = self.look_ahead()
            if next_char is None:
                break
            if next_char in WHITESPACE_CHARS:
                break
            if next_char.isalpha() or next_char.isdigit() or next_char == '_' or next_char in SYMBOLS_LIST or next_char == '/' or next_char == '*':
                break
            skipped += self.move_forward()
        return skipped

    def get_next_token(self):
        while self.current_position < self.source_length:
            current_char = self.look_ahead()

            if current_char is None:
                self.previous_token = None
                return (TOKEN_TYPES['EOF'], "EOF", self.current_line)

            if current_char == '*' and self.look_ahead(1) == '/':
                line_num = self.current_line
                self.move_forward()
                self.move_forward()
                self.has_errors = True
                self.error_list.append((line_num, "*/", "Stray closing comment"))
                self.previous_token = None
                continue

            if current_char in WHITESPACE_CHARS:
                self.move_forward()
                continue

            if current_char == '/':
                next_char = self.look_ahead(1)
                
                if next_char == '/':
                    self.move_forward(); self.move_forward()
                    while True:
                        ch = self.look_ahead()
                        if ch is None or ch == '\n' or ch == '\f':
                            break
                        self.move_forward()
                    self.previous_token = None
                    continue
                
                elif next_char == '*':
                    self.move_forward(); self.move_forward()
                    closed = False
                    start_line = self.current_line
                    while self.current_position < self.source_length:
                        if self.look_ahead() == '*' and self.look_ahead(1) == '/':
                            self.move_forward(); self.move_forward()
                            closed = True
                            break
                        self.move_forward()
                    
                    if not closed:
                        self.has_errors = True
                        self.error_list.append((start_line, "/* Unclosed ...", "Open comment at EOF"))
                        self.previous_token = None
                        return (TOKEN_TYPES['EOF'], "EOF", self.current_line)
                    
                    self.previous_token = None
                    continue
                
                else:
                    token_text = self.move_forward()
                    self.previous_token = (TOKEN_TYPES['SYMBOL'], token_text, self.current_position, self.current_line)
                    return (TOKEN_TYPES['SYMBOL'], token_text, self.current_line)

            if current_char.isalpha() or current_char == '_':
                identifier = ""
                start_line = self.current_line
                while True:
                    ch = self.look_ahead()
                    if ch is None:
                        break
                    if not (ch.isalnum() or ch == '_'):
                        break
                    identifier += self.move_forward()

                if identifier in KEYWORDS_LIST:
                    self.symbols[identifier] = {'type': TOKEN_TYPES['KEYWORD'], 'first_line': None}
                    self.previous_token = (TOKEN_TYPES['KEYWORD'], identifier, self.current_position, start_line)
                    return (TOKEN_TYPES['KEYWORD'], identifier, start_line)
                else:
                    self.symbols[identifier] = {'type': TOKEN_TYPES['ID'], 'first_line': start_line}
                    self.previous_token = (TOKEN_TYPES['ID'], identifier, self.current_position, start_line)
                    return (TOKEN_TYPES['ID'], identifier, start_line)

            if current_char.isdigit():
                number_text = ""
                start_line = self.current_line
                number_text += self.move_forward()

                if number_text == '0' and self.look_ahead() is not None and self.look_ahead().isdigit():
                    rest = ""
                    while True:
                        ch = self.look_ahead()
                        if ch is None:
                            break
                        if not (ch.isalnum() or ch == '_'):
                            break
                        rest += self.move_forward()
                    error_text = number_text + rest
                    self.has_errors = True
                    self.error_list.append((start_line, error_text, "Malformed number"))
                    extra = self.skip_until_valid()
                    if extra:
                        error_text += extra
                        self.error_list[-1] = (start_line, error_text, "Malformed number")
                    self.previous_token = None
                    return self.get_next_token()

                while True:
                    ch = self.look_ahead()
                    if ch is None or not ch.isdigit():
                        break
                    number_text += self.move_forward()

                ch = self.look_ahead()
                if ch is not None and (ch.isalpha() or ch == '_'):
                    rest = ""
                    while True:
                        ch = self.look_ahead()
                        if ch is None:
                            break
                        if not (ch.isalnum() or ch == '_'):
                            break
                        rest += self.move_forward()
                    error_text = number_text + rest
                    self.has_errors = True
                    self.error_list.append((start_line, error_text, "Malformed number"))
                    extra = self.skip_until_valid()
                    if extra:
                        error_text += extra
                        self.error_list[-1] = (start_line, error_text, "Malformed number")
                    self.previous_token = None
                    return self.get_next_token()

                self.previous_token = (TOKEN_TYPES['NUM'], number_text, self.current_position, start_line)
                return (TOKEN_TYPES['NUM'], number_text, start_line)

            if current_char == '=':
                if self.look_ahead(1) == '=':
                    token_text = self.move_forward() + self.move_forward()
                    self.previous_token = (TOKEN_TYPES['SYMBOL'], token_text, self.current_position, self.current_line)
                    return (TOKEN_TYPES['SYMBOL'], token_text, self.current_line)
                else:
                    token_text = self.move_forward()
                    self.previous_token = (TOKEN_TYPES['SYMBOL'], token_text, self.current_position, self.current_line)
                    return (TOKEN_TYPES['SYMBOL'], token_text, self.current_line)

            if current_char in SYMBOLS_LIST:
                token_text = self.move_forward()
                self.previous_token = (TOKEN_TYPES['SYMBOL'], token_text, self.current_position, self.current_line)
                return (TOKEN_TYPES['SYMBOL'], token_text, self.current_line)

            # Illegal/unhandled char branch
            if current_char is not None:
                line_num = self.current_line
                position = self.current_position

                left_part = ""
                if position - 1 >= 0:
                    i = position - 1
                    while i >= 0 and (self.source[i].isalnum() or self.source[i] == '_'):
                        i -= 1
                    left_start = i + 1
                    if left_start <= position - 1:
                        left_part = self.source[left_start:position]

                bad_char = self.move_forward()
                error_text = bad_char

                if left_part:
                    error_text = left_part + error_text

                right_part = ""
                while True:
                    ch = self.look_ahead()
                    if ch is None:
                        break
                    if not (ch.isalnum() or ch == '_'):
                        break
                    right_part += self.move_forward()
                
                if right_part:
                    error_text += right_part

                is_adjacent = False
                last_token_name = None
                last_token_line = None
                
                if self.previous_token is not None:
                    prev_type, prev_text, prev_end, prev_line = self.previous_token
                    if prev_type == TOKEN_TYPES['ID']:
                        if prev_end == position:
                            if left_part and prev_text == left_part:
                                is_adjacent = True
                                last_token_name = prev_text
                                last_token_line = prev_line

                if is_adjacent:
                    self.should_remove_last = True
                    self.token_to_remove = last_token_name
                    self.line_to_remove = last_token_line
                    if last_token_name in self.symbols and self.symbols[last_token_name]['type'] == TOKEN_TYPES['ID']:
                        del self.symbols[last_token_name]

                self.has_errors = True
                self.error_list.append((line_num, error_text, "Illegal character"))

                extra = self.skip_until_valid()
                if extra:
                    full_error = error_text + extra
                    self.error_list[-1] = (line_num, full_error, "Illegal character")

                self.previous_token = None
                return self.get_next_token()

        self.previous_token = None
        return (TOKEN_TYPES['EOF'], "EOF", self.current_line)


def main():
    input_filename = "input.txt"
    parse_tree_filename = "parse_tree.txt"
    syntax_errors_filename = "syntax_errors.txt"

    try:
        with open(input_filename, 'r') as f:
            code = f.read()
    except Exception as e:
        print("Error: Cannot open input.txt ->", e)
        return

    scanner = Scanner(code)
    token_lines = {}

    # Run scanner and collect tokens grouped by line
    while True:
        token_type, token_value, line_number = scanner.get_next_token()

        if scanner.should_remove_last:
            bad_token = scanner.token_to_remove
            bad_line = scanner.line_to_remove
            
            if bad_line in token_lines:
                token_string = "(" + TOKEN_TYPES['ID'] + ", " + bad_token + ")"
                for i in range(len(token_lines[bad_line])):
                    if token_lines[bad_line][i] == token_string:
                        del token_lines[bad_line][i]
                        if len(token_lines[bad_line]) == 0:
                            del token_lines[bad_line]
                        break
            
            scanner.should_remove_last = False
            scanner.token_to_remove = None
            scanner.line_to_remove = None

        if token_type == TOKEN_TYPES['EOF']:
            break

        token_output = "(" + token_type + ", " + token_value + ")"
        token_lines.setdefault(line_number, []).append(token_output)

    # --- WRITE parse_tree.txt ---
    # NOTE: currently this outputs a token-stream grouped by line as a simple placeholder
    # for a parse tree. If you want a real parse tree from your grammar, I'll implement a parser.
    with open(parse_tree_filename, 'w') as f:
        if not token_lines:
            f.write("Empty input or no tokens found.\n")
        else:
            f.write("Parse Tree (token-stream placeholder)\n")
            f.write("------------------------------------\n")
            for ln in sorted(token_lines.keys()):
                line_content = " ".join(token_lines[ln])
                f.write(f"{ln}. {line_content}\n")

    # --- WRITE syntax_errors.txt ---
    # Combine lexical errors (from scanner) and keep place for future syntax errors.
    with open(syntax_errors_filename, 'w') as f:
        if len(scanner.error_list) == 0:
            f.write("No lexical errors found.\n")
        else:
            for err in scanner.error_list:
                f.write(str(err[0]) + ". (" + err[1] + ", " + err[2] + ")\n")

    print("Done. Wrote:", parse_tree_filename, "and", syntax_errors_filename)


if __name__ == "__main__":
    main()
