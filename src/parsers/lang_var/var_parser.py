from lark import ParseTree
from parsers.lang_simple.simple_ast import *
from lang_var.var_ast import *
from parsers.common import *
from typing import Union
# import common.log as log
# import ast as python_ast

grammarFile = "./src/parsers/lang_var/var_grammar.lark"

# old
# def parse(args: ParserArgs) -> exp:
#     parseTree = parseAsTree(args, grammarFile, 'exp')
#     ast = parseTreeToExpAst(parseTree)
#     log.debug(f'AST: {ast}')
#     return ast

# reference from parser/common.py
# class ParserArgs:
#     code: str
#     parseAlg: ParseAlg
#     parseTreePng: Optional[str]
#     grammarFile: Optional[str]

def parseModule(args: ParserArgs) -> mod:
    parseTree = parseAsTree(args, grammarFile, 'lvar')
    # print("\n", parseTree)
    # print("\n => AST TOKENIZATION SUCCESS!\n")
    # return parseTree
    # utils.writeTextFile(path="./DEBUGGING.txt", content=f"\n\nParse String:{parseTree}")
    # if parseTree.data.type.lower() == "rule" and parseTree.data.value != "lvar":
    #     raise ParseError(f"The given start token was not lvar, it was: {parseTree.data.value}")
    ast = parseTreeToModuleAst(parseTree)
    # print(f'AST: {ast}')
    # log.debug
    
    # with open("./test.py", "r") as f:
    #     source = f.read()
    # print("Goal AST:\n" + python_ast.dump(python_ast.parse(source), indent=4))
    # print("Goal AST:\n" + python_ast.dump(python_ast.parse(source), indent=4))
    return ast

def parseTreeToModuleAst(t: ParseTree) -> mod:
    # Input:
    # Tree(Token('RULE', 'lvar'), [Tree(Token('RULE', 'stmt_list'), [...])]
    
    # make sure it is a tree
    t = asTree(t)
    
    children:list[Token | Tree[Token]] = t.children
    assert type(children) == list, f"Expected type list, got {type(children).__name__}"
    
    if len(children) <= 0:
        return Module([])
    elif len(children) == 1:
        body = parseTreeToStmtListAst(asTree(children[0]))
        return Module(body)
    else:
        raise ParseError("Too many bodies!")

def parseTreeToStmtListAst(t: ParseTree) -> list[stmt]:
    # Input:
    # Tree(Token('RULE', 'stmt_list'), [ Token('RULE', 'stmt'), [...],
    #                                    Token('RULE', 'stmt'), [...] 
    #                                   ])
    
    body:list[stmt] = []
    for c in t.children:
        if isinstance(c, Tree):
            body += [parseTreeToStmtAst(asTree(c))]
    return body

def parseTreeToStmtAst(t: ParseTree) -> stmt:
    """
    Example Input:
    Token('RULE', 'stmt'), [ Tree('assign_stmt', [
                                                  Token('CNAME', 'x'), 
                                                  Tree('add_exp', [...])
                                                  ])
                            ]
    
    Another Example:
    Tree(Token('RULE', 'stmt'), [
                                    Tree('assign_stmt', [
                                                            Token('CNAME', 'x'), Tree(Token('RULE', 'exp'), [
                                                                                                                Tree(Token('RULE', 'exp_1'), [
                                                                                                                                                Tree('int_exp', [Token('INT', '1')])
                                                                                                                                            ])
                                                                                                            ])
                                                        ])
                                    ]), 
    Tree(Token('RULE', 'stmt'), [
                                    Tree(Token('RULE', 'exp'), [
                                                                Tree(Token('RULE', 'exp_1'), [
                                                                                                Tree('call_exp', [
                                                                                                                    Tree(Token('RULE', 'call'), [
                                                                                                                                                    Token('CNAME', 'print'), Token('CNAME', 'x')])
                                                                                                                                                ])
                                                                                                                  ])
                                                                                              ])
                                                                ])
                                ])
    """
    if len(t.children) <= 0:
        return StmtExp(Call(Ident("DO_NOT_ENTER"), []))
    else:
        for c in t.children:
            # print(f"parseTreeToStmtAst: {c.data}")
            # data:str = "_"
            # if type(c) == Tree[Token] or type(c) == Tree:
            #     data = c.data
            # elif type(c) == Token:
            #     data = c.value
            # elif type(c) == str:
            #     data = c
            # if isinstance(c, Tree):
            #     data = c.data
            # elif isinstance(c, Token):
            #     data = c.value
            # elif isinstance(c, str):
            #     data = c

            c = cast(Tree[Token], c)
            data:str = "_"
            if type(c.data) == Token:
                cur_token:Token = c.data
                data = cur_token.value
            else:
                data = c.data    # str
            # print(f"cur_children:List[Tree[Token]] = cast(List[Tree[Token]], c.children) -> {type(c.children)}[{type(c.children[0])}]")
            # cur_children:List[Union[Token, Tree[Token]]] = c.children

            match data:
                case 'assign_stmt':
                    # if type(cur_children[0]) == Token:
                    #     cur_sub_token:Token = cur_children[0]
                    # else:
                    #     cur_child_child = cur_children[0].children
                    #     if type(cur_child_child) == Tree[Token]:
                    #         cur_sub_token:Token = cast(Token, cur_child_child[0])
                    #     else:
                    #         cur_sub_token:Token = cast(Token, cur_child_child[0])
                    # varname = Ident(cur_sub_token.value)
                    varname:Ident = Ident(extractVarName(c))
                    right_expr = parseTreeToExpAst(asTree(c.children[1]))
                    return Assign(varname, right_expr)
                case 'exp' | 'exp_1' | 'exp_2':
                    return StmtExp(parseTreeToExpAst(asTree(c.children[0])))
                case _:
                    return StmtExp(Call(Ident("DO_NOT_ENTER"), []))
                    # raise Exception(f"Unhandled statement kind: {_}, type={type(_)}")
        return StmtExp(Call(Ident("DO_NOT_ENTER"), []))

def parseTreeToExpAst(t: ParseTree) -> exp:
    """
    Input:
     Tree('add_exp', [
                        Tree(Token('RULE', 'exp'), [
                                                        Tree(Token('RULE', 'exp_1'), [
                                                                                        Tree('int_exp', [Token('INT', '1')])
                                                                                      ])
                                                    ]), 
                        Tree(Token('RULE', 'exp_1'), [
                                                        Tree('unary_exp', [
                                                                            Tree('unary_op', [
                                                                                                Tree('int_exp', [Token('INT', '1')])
                                                                                                ])
                                                                            ])
                                                    ])
                        ])
    """
    match t.data:
        case 'var_exp':
            name:str = "_"
            if type(t.children[0]) == Token:
                name = t.children[0].value
            return Name(Ident(name))
        case 'int_exp':
            return IntConst(int(asToken(t.children[0]).value))
        case 'call_exp':
            # print(f"Found Call: {t}")
            # first child can be either Token or Tree
            first_child = t.children[0]

            # # get function name token
            # if isinstance(first_child, Token):
            #     # Simple case: function name token directly
            #     function_name = first_child.value
            #     args = []

            #     if len(t.children) > 1:
            #         # second child is arg_list tree
            #         arg_list_tree = t.children[1]
            #         args = parseArgList(arg_list_tree)

            #     return Call(Ident(function_name), args)

            cur_tree_list = cast(List[Tree[Token]], t.children)
            first_child = cur_tree_list[0]
            
            if type(first_child) == Tree[Token] and first_child.data == "call_exp":
                t = first_child
                first_child = t.children[0]

                # print(f"Updated t: {t}")
                # print(f"Updted first child: {first_child}")

            # first child is a tree, e.g., var_exp or nested call_exp
            # extract function name token recursively
            # print(f"first_child = cast(Token, first_child) -> {type(first_child)}")
            first_child = cast(Token, first_child)
            function_name:str = cast(str, first_child.value) # extractFunctionName(first_child)
            # print(f"Function Name: {function_name}")
            args = []
            if len(t.children) > 1:
                arg_list_tree = cast(Tree[Token], t.children[1])
                args = parseArgList(arg_list_tree)
            # print(f"Args: {args}")
            return Call(Ident(function_name), args)
        case 'unary_exp':  
            op:str = asTree(t.children[0]).data
            e1 = asTree(asTree(t.children[0]).children[0])
            if op == "unary_op":
                return UnOp(USub(), parseTreeToExpAst(e1)) 
            else:
                # return StmtExp(Call(Ident("input_int"), [])).exp
                raise Exception(f"Unhandled unary operator {op}")
        case 'add_exp':  
            e1 = asTree(t.children[0])
            e2 = asTree(t.children[1])
            return BinOp(parseTreeToExpAst(e1), Add(), parseTreeToExpAst(e2))
        case 'sub_exp': 
            e1 = asTree(t.children[0])
            e2 = asTree(t.children[1])
            return BinOp(parseTreeToExpAst(e1), Sub(), parseTreeToExpAst(e2))
        case 'mul_exp': 
            e1 = asTree(t.children[0])
            e2 = asTree(t.children[1])
            return BinOp(parseTreeToExpAst(e1), Mul(), parseTreeToExpAst(e2))
        case 'exp' | 'exp_1' | 'exp_2' | 'paren_exp':  
            e1 = asTree(t.children[0])
            return parseTreeToExpAst(e1)
        case _:
            return Call(Ident("DO_NOT_ENTER"), [])
            # raise Exception(f'unhandled parse tree of kind {kind} for exp: {t}')

def extractVarName(tree:Union[Token, Tree[Token]]) -> str:
    # Traverse down to find the Token CNAME
    if type(tree) == Token:
        if tree.type == "CNAME":
            return tree.value
        else:
            return "_"
            # raise ValueError("Expected CNAME token but got something else")
    elif type(tree) == Tree:
        # typically the first child in these expressions
        for child in tree.children:
            return extractVarName(child)
        return "_"
    else:
        return "_"

def parseArgList(arg_list_tree:Tree[Token]) -> List[exp]:
    args:List[exp] = []
    # print(f"Founded args to check: {arg_list_tree.children}")
    for child in arg_list_tree.children:
        if isinstance(child, Tree) and "exp" in child.data:
            expr = parseTreeToExpAst(child)
            args += [expr]
        # ignore commas (Tokens)
    return args



