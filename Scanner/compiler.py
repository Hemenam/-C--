# Predictive Recursive Descent Parser + Scanner
# Produces: parse_tree.txt and syntax_errors.txt for an input C-like program
# Token types and grammar as provided by the user.

import re
from typing import List, Optional
import sys, os

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

# ---------- Scanner ----------
class Token:
    def __init__(self, typ, lexeme, line=1, col=1):
        self.type = typ
        self.lexeme = lexeme
        self.line = line
        self.col = col
    def __repr__(self):
        return f"({self.type}, {self.lexeme})"


def scan(source: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    line = 1
    col = 1
    n = len(source)

    def peek(k=0):
        return source[i+k] if i+k < n else ''

    while i < n:
        ch = source[i]
        # whitespace
        if ch in WHITESPACE_CHARS:
            if ch == '\n':
                line += 1
                col = 1
            else:
                col += 1
            i += 1
            continue
        # comments (/* ... */)
        if ch == '/' and peek(1) == '*':
            i += 2
            col += 2
            while i < n and not (source[i] == '*' and peek(1) == '/'):
                if source[i] == '\n':
                    line += 1
                    col = 1
                else:
                    col += 1
                i += 1
            if i < n:
                i += 2
                col += 2
            continue
        # numbers
        if ch.isdigit():
            start_col = col
            j = i
            while j < n and source[j].isdigit():
                j += 1
            lex = source[i:j]
            tokens.append(Token(TOKEN_TYPES['NUM'], lex, line, start_col))
            col += (j - i)
            i = j
            continue
        # identifiers / keywords
        if ch.isalpha() or ch == '_':
            start_col = col
            j = i
            while j < n and (source[j].isalnum() or source[j] == '_'):
                j += 1
            lex = source[i:j]
            typ = TOKEN_TYPES['KEYWORD'] if lex in KEYWORDS_LIST else TOKEN_TYPES['ID']
            tokens.append(Token(typ, lex, line, start_col))
            col += (j - i)
            i = j
            continue
        # two-char symbol '=='
        if ch == '=' and peek(1) == '=':
            tokens.append(Token(TOKEN_TYPES['SYMBOL'], '==', line, col))
            i += 2
            col += 2
            continue
        # single char symbols
        if ch in ''.join(set(''.join(SYMBOLS_LIST))):
            # treat = (assignment) also as SYMBOL
            tokens.append(Token(TOKEN_TYPES['SYMBOL'], ch, line, col))
            i += 1
            col += 1
            continue
        # unknown / error char
        tokens.append(Token(TOKEN_TYPES['ERROR'], ch, line, col))
        i += 1
        col += 1
    tokens.append(Token(TOKEN_TYPES['EOF'], '$', line, col))
    return tokens

# ---------- Parse Tree Node ----------
class Node:
    def __init__(self, label: str, children: Optional[List['Node']]=None):
        self.label = label
        self.children = children or []
    def add(self, node: 'Node'):
        self.children.append(node)

    def is_leaf_token(self):
        return False

class TokenNode(Node):
    def __init__(self, token: Token):
        super().__init__(f"({token.type}, {token.lexeme})")
    def is_leaf_token(self):
        return True

# pretty print the tree like the example
def tree_to_lines(node: Node, prefix: str = '', is_last: bool = True) -> List[str]:
    lines = []
    connector = '└── ' if is_last else '├── '
    lines.append(prefix + connector + node.label if prefix else node.label)
    if node.children:
        new_prefix = prefix + ('    ' if is_last else '│   ')
        for i, child in enumerate(node.children):
            lines.extend(tree_to_lines(child, new_prefix, i == len(node.children)-1))
    return lines

# ---------- Parser (Predictive Recursive Descent) ----------
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0
        self.errors = []

    def cur(self) -> Token:
        return self.tokens[self.i]
    def advance(self):
        if self.cur().type != TOKEN_TYPES['EOF']:
            self.i += 1
    def match(self, expected_type=None, expected_lexeme=None) -> Optional[TokenNode]:
        t = self.cur()
        if expected_type and t.type != expected_type:
            self.error(f"Expected token type {expected_type} but found {t.type} ('{t.lexeme}') at line {t.line} col {t.col}")
            return None
        if expected_lexeme and t.lexeme != expected_lexeme:
            self.error(f"Expected '{expected_lexeme}' but found '{t.lexeme}' at line {t.line} col {t.col}")
            return None
        node = TokenNode(t)
        self.advance()
        return node

    def error(self, msg):
        self.errors.append(msg)
        # basic panic: skip one token
        if self.cur().type != TOKEN_TYPES['EOF']:
            self.advance()

    # Grammar functions follow. Each returns a Node.

    def parse(self) -> Node:
        root = Node('Program')
        root.add(self.declaration_list())
        return root

    def declaration_list(self) -> Node:
        node = Node('Declaration-list')
        # if next token starts a Declaration -> Type-specifier 'int' or 'void'
        while self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme in ('int', 'void'):
            node.add(self.declaration())
        # epsilon allowed (if nothing matched)
        if not node.children:
            node.children.append(Node('epsilon'))
        return node

    def declaration(self) -> Node:
        node = Node('Declaration')
        node.add(self.declaration_initial())
        node.add(self.declaration_prime())
        return node

    def declaration_initial(self) -> Node:
        node = Node('Declaration-initial')
        node.add(self.type_specifier())
        if self.cur().type == TOKEN_TYPES['ID']:
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error(f"Expected ID in Declaration-initial at {self.cur().line}:{self.cur().col}")
        return node

    def declaration_prime(self) -> Node:
        node = Node('Declaration-prime')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '(':
            node.add(self.fun_declaration_prime())
        else:
            node.add(self.var_declaration_prime())
        return node

    def var_declaration_prime(self) -> Node:
        node = Node('Var-declaration-prime')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '[':
            node.add(TokenNode(self.cur())); self.advance()
            if self.cur().type == TOKEN_TYPES['NUM']:
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected NUM in array declaration')
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ']':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ] in array declaration')
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ; after array declaration')
        elif self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            # error recovery: accept semicolon if possible
            self.error('Expected ; or [ in Var-declaration-prime')
            # try to synchronize
            while self.cur().type != TOKEN_TYPES['SYMBOL'] or self.cur().lexeme != ';':
                if self.cur().type == TOKEN_TYPES['EOF']:
                    break
                self.advance()
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
                node.add(TokenNode(self.cur())); self.advance()
        return node

    def fun_declaration_prime(self) -> Node:
        node = Node('Fun-declaration-prime')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '(':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ( in Fun-declaration-prime')
        node.add(self.params())
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ')':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ) in Fun-declaration-prime')
        node.add(self.compound_stmt())
        return node

    def type_specifier(self) -> Node:
        node = Node('Type-specifier')
        if self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme in ('int','void'):
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected int or void in Type-specifier')
        return node

    def params(self) -> Node:
        node = Node('Params')
        if self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme == 'void':
            node.add(TokenNode(self.cur())); self.advance()
            return node
        # expect: int ID Param-prime Param-list
        if self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme == 'int':
            node.add(TokenNode(self.cur())); self.advance()
            if self.cur().type == TOKEN_TYPES['ID']:
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ID in Params')
            node.add(self.param_prime())
            node.add(self.param_list())
        else:
            self.error('Expected Params: void or int ID ...')
        return node

    def param_list(self) -> Node:
        node = Node('Param-list')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ',':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.param())
            node.children.append(self.param_list())
        else:
            node.children.append(Node('epsilon'))
        return node

    def param(self) -> Node:
        node = Node('Param')
        node.add(self.declaration_initial())
        node.add(self.param_prime())
        return node

    def param_prime(self) -> Node:
        node = Node('Param-prime')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '[':
            node.add(TokenNode(self.cur())); self.advance()
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ']':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ] in Param-prime')
        else:
            node.children.append(Node('epsilon'))
        return node

    def compound_stmt(self) -> Node:
        node = Node('Compound-stmt')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '{':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected { in Compound-stmt')
        node.add(self.declaration_list())
        node.add(self.statement_list())
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '}':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected } in Compound-stmt')
        return node

    def statement_list(self) -> Node:
        node = Node('Statement-list')
        # Statement starts with: ID, '{', 'if', 'for', 'return', 'break', ';'
        while True:
            t = self.cur()
            if (t.type == TOKEN_TYPES['ID'] or (t.type == TOKEN_TYPES['SYMBOL'] and t.lexeme == '{')
                or (t.type == TOKEN_TYPES['KEYWORD'] and t.lexeme in ('if','for','return','break'))
                or (t.type == TOKEN_TYPES['SYMBOL'] and t.lexeme == ';')):
                node.add(self.statement())
            else:
                break
        if not node.children:
            node.children.append(Node('epsilon'))
        return node

    def statement(self) -> Node:
        t = self.cur()
        if t.type == TOKEN_TYPES['SYMBOL'] and t.lexeme == '{':
            return self.compound_stmt()
        if t.type == TOKEN_TYPES['KEYWORD'] and t.lexeme == 'if':
            return self.selection_stmt()
        if t.type == TOKEN_TYPES['KEYWORD'] and t.lexeme == 'for':
            return self.iteration_stmt()
        if t.type == TOKEN_TYPES['KEYWORD'] and t.lexeme == 'return':
            return self.return_stmt()
        # Expression-stmt: break ; or ; or Expression ;
        return self.expression_stmt()

    def expression_stmt(self) -> Node:
        node = Node('Expression-stmt')
        if self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme == 'break':
            node.add(TokenNode(self.cur())); self.advance()
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ; after break')
            return node
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
            node.add(TokenNode(self.cur())); self.advance()
            return node
        # else parse Expression ;
        node.add(self.expression())
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ; after expression')
        return node

    def selection_stmt(self) -> Node:
        node = Node('Selection-stmt')
        if self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme == 'if':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected if in Selection-stmt')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '(':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ( after if')
        node.add(self.expression())
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ')':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ) after if condition')
        node.add(self.statement())
        # expect else
        if self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme == 'else':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.statement())
        else:
            node.children.append(Node('epsilon'))
        return node

    def iteration_stmt(self) -> Node:
        node = Node('Iteration-stmt')
        if self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme == 'for':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected for in Iteration-stmt')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '(':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ( after for')
        node.add(self.expression())
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ; in for header')
        node.add(self.expression())
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ; in for header (2)')
        node.add(self.expression())
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ')':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected ) after for header')
        node.add(self.compound_stmt())
        return node

    def return_stmt(self) -> Node:
        node = Node('Return-stmt')
        if self.cur().type == TOKEN_TYPES['KEYWORD'] and self.cur().lexeme == 'return':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Expected return')
        # Return-stmt-prime -> Expression ; | ;
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
            node.add(TokenNode(self.cur())); self.advance()
        else:
            node.add(self.expression())
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ';':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ; after return expression')
        return node

    # Expressions (simplified but compatible with the grammar)
    def expression(self) -> Node:
        # If ID then could be ID B
        if self.cur().type == TOKEN_TYPES['ID']:
            node = Node('Expression')
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.B())
            return node
        # else parse simple expression
        node = Node('Expression')
        node.add(self.simple_expression_zegond())
        return node

    def B(self) -> Node:
        node = Node('B')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '=':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.expression())
            return node
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '[':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.expression())
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ']':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ] in B')
            node.add(self.H())
            return node
        # else Simple-expression-prime
        node.add(self.simple_expression_prime())
        return node

    def H(self) -> Node:
        node = Node('H')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '=':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.expression())
            return node
        # else G D C (we'll approximate by parsing remaining operators)
        node.add(self.G())
        node.add(self.D())
        node.add(self.C())
        return node

    def simple_expression_zegond(self) -> Node:
        node = Node('Simple-expression-zegond')
        node.add(self.additive_expression_zegond())
        node.add(self.C())
        return node

    def simple_expression_prime(self) -> Node:
        node = Node('Simple-expression-prime')
        node.add(self.additive_expression_prime())
        node.add(self.C())
        return node

    def C(self) -> Node:
        node = Node('C')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme in ('==','<'):
            node.add(Node('Relop'))
            node.children[-1].add(TokenNode(self.cur()))
            self.advance()
            node.add(self.additive_expression())
        else:
            node.children.append(Node('epsilon'))
        return node

    def additive_expression(self) -> Node:
        node = Node('Additive-expression')
        node.add(self.term())
        node.add(self.D())
        return node

    def additive_expression_prime(self) -> Node:
        node = Node('Additive-expression-prime')
        node.add(self.term_prime())
        node.add(self.D())
        return node

    def additive_expression_zegond(self) -> Node:
        node = Node('Additive-expression-zegond')
        node.add(self.term_zegond())
        node.add(self.D())
        return node

    def D(self) -> Node:
        node = Node('D')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme in ('+','-'):
            node.add(Node('Addop'))
            node.children[-1].add(TokenNode(self.cur())); self.advance()
            node.add(self.term())
            node.add(self.D())
        else:
            node.children.append(Node('epsilon'))
        return node

    def term(self) -> Node:
        node = Node('Term')
        node.add(self.signed_factor())
        node.add(self.G())
        return node

    def term_prime(self) -> Node:
        node = Node('Term-prime')
        node.add(self.factor_prime())
        node.add(self.G())
        return node

    def term_zegond(self) -> Node:
        node = Node('Term-zegond')
        node.add(self.signed_factor_zegond())
        node.add(self.G())
        return node

    def G(self) -> Node:
        node = Node('G')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme in ('*','/'):
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.signed_factor())
            node.add(self.G())
        else:
            node.children.append(Node('epsilon'))
        return node

    def signed_factor(self) -> Node:
        node = Node('Signed-factor')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme in ('+','-'):
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.factor())
        else:
            node.add(self.factor())
        return node

    def signed_factor_zegond(self) -> Node:
        node = Node('Signed-factor-zegond')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme in ('+','-'):
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.factor())
        else:
            node.add(self.factor_zegond())
        return node

    def factor(self) -> Node:
        node = Node('Factor')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '(':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.expression())
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ')':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ) in Factor')
            return node
        if self.cur().type == TOKEN_TYPES['ID']:
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.var_call_prime())
            return node
        if self.cur().type == TOKEN_TYPES['NUM']:
            node.add(TokenNode(self.cur())); self.advance()
            return node
        self.error('Unexpected token in Factor')
        return node

    def var_call_prime(self) -> Node:
        node = Node('Var-call-prime')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '(':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.args())
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ')':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ) in Var-call-prime')
            return node
        node.add(self.var_prime())
        return node

    def var_prime(self) -> Node:
        node = Node('Var-prime')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '[':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.expression())
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ']':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ] in Var-prime')
        else:
            node.children.append(Node('epsilon'))
        return node

    def factor_prime(self) -> Node:
        node = Node('Factor-prime')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '(':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.args())
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ')':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ) in Factor-prime')
        else:
            node.children.append(Node('epsilon'))
        return node

    def factor_zegond(self) -> Node:
        node = Node('Factor-zegond')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == '(':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.expression())
            if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ')':
                node.add(TokenNode(self.cur())); self.advance()
            else:
                self.error('Expected ) in Factor-zegond')
        elif self.cur().type == TOKEN_TYPES['NUM']:
            node.add(TokenNode(self.cur())); self.advance()
        else:
            self.error('Unexpected token in Factor-zegond')
        return node

    def args(self) -> Node:
        node = Node('Args')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ')':
            node.children.append(Node('epsilon'))
            return node
        node.add(self.arg_list())
        return node

    def arg_list(self) -> Node:
        node = Node('Arg-list')
        node.add(self.expression())
        node.add(self.arg_list_prime())
        return node

    def arg_list_prime(self) -> Node:
        node = Node('Arg-list-prime')
        if self.cur().type == TOKEN_TYPES['SYMBOL'] and self.cur().lexeme == ',':
            node.add(TokenNode(self.cur())); self.advance()
            node.add(self.expression())
            node.add(self.arg_list_prime())
        else:
            node.children.append(Node('epsilon'))
        return node

# ---------- Runner ----------
if __name__ == '__main__':
    input_path = 'input.txt'
    if not os.path.exists(input_path):
        print("input.txt not found. Please create 'input.txt' with the source program and run again.")
        sys.exit(1)


    with open(input_path, 'r', encoding='utf-8') as f:
        source = f.read()

    tokens = scan(source)
    # uncomment to print tokens
    # for t in tokens: print(t)

    parser = Parser(tokens)
    tree = parser.parse()

    # pretty-print tree to lines
    lines = tree_to_lines(tree)
    with open('parse_tree.txt', 'w', encoding='utf-8') as f:
        for ln in lines:
            f.write(ln + '\n')
    with open('syntax_errors.txt', 'w', encoding='utf-8') as f:
        if parser.errors:
            for e in parser.errors:
                f.write(e + '\n')
        else:
            f.write('No syntax errors.\n')

    print('Wrote parse_tree.txt and syntax_errors.txt')
