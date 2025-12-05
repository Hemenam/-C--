import sys

# --- Token Definitions ---
class TokenType:
    KEYWORD = "KEYWORD"
    ID = "ID"
    NUM = "NUM"
    SYMBOL = "SYMBOL"
    EOF = "EOF"
    ERROR = "ERROR"

# C-minus Keywords
KEYWORDS = {'else', 'if', 'int', 'return', 'void', 'while'}

# C-minus Symbols (based on requirements and typical syntax)
SYMBOLS = {'+', '-', '*', '/', '<', '<=', '>', '>=', '==', '!=', '=', ';', ',', '(', ')', '[', ']', '{', '}'}

class Scanner:
    def __init__(self, source_code):
        self.src = source_code
        self.pos = 0
        self.length = len(source_code)
        self.lineno = 1
        self.errors_found = False

    def peek(self, offset=0):
        """Look ahead at the next character without consuming it."""
        if self.pos + offset >= self.length:
            return None
        return self.src[self.pos + offset]

    def advance(self):
        """Consume the current character and return it."""
        if self.pos >= self.length:
            return None
        char = self.src[self.pos]
        self.pos += 1
        if char == '\n':
            self.lineno += 1
        return char

    def get_next_token(self):
        """
        The Core DFA Implementation.
        Returns a tuple: (TokenType, TokenString, LineNumber)
        """
        while self.pos < self.length:
            char = self.peek()

            # 1. Handle Whitespace
            if char is not None and char.isspace():
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
                    self.advance() # eat /
                    self.advance() # eat /
                    while self.peek() is not None and self.peek() != '\n':
                        self.advance()
                    continue # Loop back to start to get next real token

                # Case: Block Comment /* */
                elif next_char == '*':
                    self.advance() # eat /
                    self.advance() # eat *
                    
                    comment_closed = False
                    while self.pos < self.length:
                        if self.peek() == '*' and self.peek(1) == '/':
                            self.advance() # eat *
                            self.advance() # eat /
                            comment_closed = True
                            break
                        self.advance()
                    
                    if not comment_closed:
                        print(f"Error at line {self.lineno}: Unclosed comment.")
                        return (TokenType.EOF, "EOF", self.lineno) # Fatal error stops scanning
                    
                    continue # Comment finished, loop back
                
                # Case: Just a Division Symbol /
                else:
                    self.advance()
                    return (TokenType.SYMBOL, "/", self.lineno)

            # 4. Handle Identifiers and Keywords (Starts with Letter)
            if char.isalpha():
                lexeme = ""
                while self.peek() is not None and (self.peek().isalnum() or self.peek() == '_'):
                    lexeme += self.advance()
                
                if lexeme in KEYWORDS:
                    return (TokenType.KEYWORD, lexeme, self.lineno)
                return (TokenType.ID, lexeme, self.lineno)

            # 5. Handle Numbers (Starts with Digit)
            if char.isdigit():
                lexeme = ""
                while self.peek() is not None and self.peek().isdigit():
                    lexeme += self.advance()
                
                # Error Handling: Ill-formed number (e.g., 123d)
                if self.peek() is not None and self.peek().isalpha():
                    print(f"Error at line {self.lineno}: Ill-formed number '{lexeme}{self.peek()}...'")
                    self.errors_found = True
                    # Panic Mode: Skip the invalid characters until a delimiter
                    while self.peek() is not None and self.peek().isalnum():
                        self.advance()
                    # Recursively call to get the NEXT valid token after this error
                    return self.get_next_token()

                return (TokenType.NUM, lexeme, self.lineno)

            # 6. Handle Symbols
            # Check for two-character symbols (==, <=, >=, !=)
            if char in "=<!>":
                if self.peek(1) == '=':
                    lexeme = self.advance() + self.advance()
                    return (TokenType.SYMBOL, lexeme, self.lineno)
            
            # Single character symbols
            if char in SYMBOLS:
                return (TokenType.SYMBOL, self.advance(), self.lineno)

            # 7. Unknown/Illegal Character
            print(f"Error at line {self.lineno}: Illegal character '{char}'")
            self.errors_found = True
            self.advance() # Skip bad char
            # Try next token
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
    
    # Dictionary to group tokens by line number for output formatting
    # Format: { line_num: ["(Type, String)", "(Type, String)"] }
    lines_output = {}

    while True:
        token_type, token_string, lineno = scanner.get_next_token()
        
        if token_type == TokenType.EOF:
            break
        
        # Prepare the token string representation
        # Note: The assignment implies exact format like (KEYWORD, void)
        token_repr = f"({token_type}, {token_string})"
        
        if lineno not in lines_output:
            lines_output[lineno] = []
        lines_output[lineno].append(token_repr)

    # Write results to tokens.txt
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Sort by line number to ensure order
            for lineno in sorted(lines_output.keys()):
                # Join all tokens for this line with spaces
                line_content = " ".join(lines_output[lineno])
                f.write(f"{lineno}. {line_content}\n")
        print(f"Successfully tokenized {input_file}. Results saved to {output_file}.")
        if scanner.errors_found:
            print("Note: Some errors were encountered during scanning (checked stderr/console).")
            
    except IOError as e:
        print(f"Error writing to {output_file}: {e}")

if __name__ == "__main__":
    main()