import sys

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

    def get_next_token(self):
        while self.pos < self.length:
            char = self.peek()

            # 1. Handle Whitespace
            if char in WHITESPACE:
                self.advance()
                continue

            # 2. Handle EOF
            if char is None:
                return (TokenType.EOF, "EOF", self.lineno)

            # 3. Handle Comments and Division (Starts with /)
            if char == '/':
                next_char = self.peek(1)
                
                # Case: Line Comment //
                if next_char == '/':
                    self.advance(); self.advance() 
                    # Consume until end of line (newline or EOF)
                    while self.peek() is not None and self.peek() not in ['\n', '\f']:
                        self.advance()
                    continue

                # Case: Block Comment /* */
                elif next_char == '*':
                    self.advance(); self.advance() 
                    comment_closed = False
                    start_line = self.lineno
                    while self.pos < self.length:
                        if self.peek() == '*' and self.peek(1) == '/':
                            self.advance(); self.advance()
                            comment_closed = True
                            break
                        # Handle newlines inside block comments to keep line count correct
                        if self.peek() == '\n':
                            self.lineno += 1
                            self.pos += 1 # advance manually to avoid double counting if advance() handles it
                        else:
                            self.advance()
                    
                    if not comment_closed:
                        # Unclosed comment is an error, usually fatal or returns EOF
                        print(f"Error at line {start_line}: Unclosed block comment.")
                        return (TokenType.EOF, "EOF", self.lineno)
                    continue 
                
                # Case: Division / (Check if '/' is in SYMBOLS, yes it is)
                else:
                    return (TokenType.SYMBOL, self.advance(), self.lineno)

            # 4. Handle Identifiers and Keywords (Starts with Letter or Underscore)
            # Table: [A-Za-z_][A-Za-z0-9_]*
            if char.isalpha() or char == '_': 
                lexeme = ""
                while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                    lexeme += self.advance()
                
                if lexeme in KEYWORDS:
                    return (TokenType.KEYWORD, lexeme, self.lineno)
                return (TokenType.ID, lexeme, self.lineno)

            # 5. Handle Numbers
            # Table: [0-9]+ (but report leading zeros as error)
            if char.isdigit():
                start_line = self.lineno
                lexeme = self.advance() # Consume first digit
                
                # Check for Leading Zero Error (e.g., 01, 007)
                # Valid '0' is allowed, but '0' followed by another digit is an error.
                if lexeme == '0' and self.peek() is not None and self.peek().isdigit():
                    self.errors_found = True
                    print(f"Error at line {start_line}: Invalid number format (leading zero): '{lexeme}{self.peek()}...'")
                    
                    # Panic Mode: Skip invalid digits/letters
                    while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                        self.advance()
                    return self.get_next_token()

                # Consume rest of digits
                while self.peek() is not None and self.peek().isdigit():
                    lexeme += self.advance()

                # Check for Invalid Suffix (e.g., 123a) - Common lexical error check
                if self.peek() is not None and (self.peek().isalpha() or self.peek() == '_'):
                    self.errors_found = True
                    print(f"Error at line {start_line}: Invalid number format (letters after digits): '{lexeme}{self.peek()}...'")
                    while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                        self.advance()
                    return self.get_next_token()

                return (TokenType.NUM, lexeme, self.lineno)

            # 6. Handle Symbols
            # First check for '==' (The only multi-char symbol in your new table)
            if char == '=':
                if self.peek(1) == '=':
                    lexeme = self.advance() + self.advance()
                    return (TokenType.SYMBOL, lexeme, self.lineno)
            
            # Check single char symbols
            if char in SYMBOLS:
                return (TokenType.SYMBOL, self.advance(), self.lineno)

            # 7. Illegal Character
            # Any character not matched above (including >, !, etc.)
            char_hex = hex(ord(char))
            print(f"Error at line {self.lineno}: Illegal character '{char}'")
            self.errors_found = True
            self.advance()
            return self.get_next_token()

        return (TokenType.EOF, "EOF", self.lineno)


def main():
    input_file = "input.txt"
    output_file = "tokens.txt"

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

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for lineno in sorted(lines_output.keys()):
                line_content = " ".join(lines_output[lineno])
                f.write(f"{lineno}. {line_content}\n")
        print(f"Tokenization complete. Output saved to {output_file}")      
    except IOError as e:
        print(f"Error writing to {output_file}: {e}")

if __name__ == "__main__":
    main()