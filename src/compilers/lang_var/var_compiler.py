
from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *
import common.utils as utils

FUNC_MAPPER = {
    '$input_int': '$input_i64',
    '$print': '$print_i64'
}

def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    # type-checking
    vars = var_tychecker.tycheckModule(m)
    
    # compiling statements
    instrs = compileStmts(m.stmts)
    
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

# See: CC/languaes_formal.pdf/2.2 Evluation Rules
# Slide: Compiling Expressions

def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    instrs = []
    for cur_stmt in stmts:
        match cur_stmt:
            case StmtExp(exp=exp):
                instrs += compileExps([exp])
            case Assign(var=var, right=right):
                instrs += compileExps([right])
                instrs += [WasmInstrVarLocal(op='set', id=WasmId('$'+var.name))]

    return instrs


def compileExps(exps: list[exp]) -> list[WasmInstr]:
    instrs = []
    for cur_exp in exps:
        match cur_exp:
            case IntConst(value=value):
                instrs += [WasmInstrConst(ty='i64', val=value)]
            case Name(name=name):
                instrs += [WasmInstrVarLocal(op='get', id=WasmId('$'+name.name))]
            case Call(name=name, args=args):
                instrs += compileExps(args)
                instrs += [WasmInstrCall(id=WasmId(FUNC_MAPPER["$"+name.name]))]
            case UnOp(op=op, arg=arg):
                instrs += [WasmInstrConst(ty='i64', val=-1)]
                instrs += compileExps([arg])
                instrs += [WasmInstrNumBinOp(ty='i64', op='mul')]
            case BinOp(left=left, op=op, right=right):
                instrs += compileExps([left])
                instrs += compileExps([right])
                match op:
                    case Add(): 
                        op = 'add'
                    case Sub(): 
                        op = 'sub'
                    case Mul(): 
                        op = 'mul'
                instrs += [WasmInstrNumBinOp(ty='i64', op=op)]

    return instrs



def identToWasmId(x:Ident) -> WasmId:
    return WasmId("$"+x.name)





