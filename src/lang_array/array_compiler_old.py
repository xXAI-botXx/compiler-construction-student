from lang_array.array_astAtom import *    # -> atom
import lang_array.array_ast as plainAst
from common.wasm import *
import lang_array.array_tychecker as array_tychecker
import lang_array.array_transform as array_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *
import common.utils as utils


def compileModule(m: plainAst.mod, cfg: CompilerConfig) -> WasmModule:
    # type-checking
    vars = array_tychecker.tycheckModule(m)
    
    # compiling statements
    stmts:list[stmt] = m.stmts
    env_ctx:array_transform.Ctx = array_transform.Ctx()
    stmt_a:list[atom.stmt] = array_transform.transStmts(stmts, env_ctx)
    instrs = compileStmtsA(stmt_a)
    
    # generating Wasm module
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64') for x in vars]
    return WasmModule(
                imports=wasmImports(cfg.maxMemSize),
                exports=[WasmExport("main", WasmExportFunc(idMain))],
                globals=[],
                data=[],
                funcTable=WasmFuncTable([]),
                funcs=[WasmFunc(idMain, [], None, locals, instrs)]
            )

# see other compiler!!!
def compileStmtsA(stmts_a: list[atom.stmt], cfg: CompilerConfig) -> list[WasmInstr]:
    """
    type stmt = StmtExp | Assign | IfStmt | WhileStmt | SubscriptAssign
    """
    pass

def compileInitArray(lenExp: atomExp, elemTy: ty, cfg: CompilerConfig) -> list[WasmInstr]:
    """
    Generates code to initialize an array without initializing the elements.
    
    See Lecture slides -> page 19
    """
    pass

def arrayLenInstrs() -> list[WasmInstr]:
    """
    Generates code that expects the array address 
    on top of stack and puts the length on top of stack.

    See Lecture slides -> page 29
    """
    pass

def arrayOffsetInstrs(arrayExp: atomExp, indexExp: atomExp) -> list[WasmInstr]:
    """
    Returns instructions that places the memory offset 
    for a certain array element on top of stack.

    See Lecture slides -> page 30
    """
    pass


