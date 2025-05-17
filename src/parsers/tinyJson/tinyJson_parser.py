from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleJson(toks: TokenStream) -> Json:
    # json: object | string | int;
    # => check type of next token:
    #       - rule('{}')
    #       - rule(string)
    #       - rule(int)
    # sub rules must fail if not the right rule!!!
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt])

# def ruleJson(toks: TokenStream) -> Json:
#     # json: object | string | int;
#     # => check type of next token:
#     #       - rule('{}')
#     #       - rule(string)
#     #       - rule(int)
#     # Changed the original function, so that the subfunction does not have to fail!
#     # The failing apporach is not needed when just checking the types...I hope so
#     t = toks.lookahead()
#     if t.type == "LBRACE":
#         return ruleObject(toks)
#     elif t.type == "STRING":
#         return ruleString(toks)
#     elif t.type == "INT":
#         return ruleInt(toks)
#     else:
#         raise ParseError(f"Unexpected token: {t}")

def ruleObject(toks: TokenStream) -> dict[str, Json]:
    # object: "{", entryList, "}";
    # => { rule(entries) }
    toks.ensureNext("LBRACE")
    entries = ruleEntryList(toks)
    toks.ensureNext("RBRACE")
    return entries

def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    # entryList: | entryListNotEmpty;
    # First try:
    # if toks.lookahead().type == "RBRACE":
    #     return {}    # empty list
    # return ruleEntryListNotEmpty(toks)    # rule not empty list
    # After reading the details:
    if toks.lookahead().type == "STRING":
        return ruleEntryListNotEmpty(toks)
    else:
        return {}

def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    # entryListNotEmpty: entry | entry, ",", entryListNotEmpty;
    # => rule(parameter) while there is a comma: ,rule(parameter),...
    result:dict[str, Json] = {}
    key, value = ruleEntry(toks)
    result[key] = value
    while toks.lookahead().type == "COMMA":
        toks.ensureNext("COMMA")
        key, value = ruleEntry(toks)
        if key in result:
            raise ParseError(f"Duplicate key '{key}' in object")
        result[key] = value
    return result

def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    # entry: string, ":", json;
    # => rule(string):rule(json) (to get an function call, number or string value)
    key = ruleString(toks)
    toks.ensureNext("COLON")
    value = ruleJson(toks)
    return key, value

def ruleString(toks: TokenStream) -> str:
    token = toks.ensureNext("STRING")
    return token.value[1:-1]  # remove quotes -> needed? unsure

def ruleInt(toks: TokenStream) -> int:
    token = toks.ensureNext("INT")
    return int(token.value)

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res







