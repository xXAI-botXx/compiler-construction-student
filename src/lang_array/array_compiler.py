# Task: Take loop_compiler.py and change, so it work for array_astAtom

from lang_array.array_astAtom import *    # -> atom
import lang_array.array_ast as plainAst
from common.wasm import *
import lang_array.array_tychecker as array_tychecker
import lang_array.array_transform as array_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *
import common.utils as utils



# --------------
# >>> Helper <<<
# --------------
FUNC_MAPPER:dict[str, Callable[[Any], str]] = {
    '$input_int': lambda type_:f'$input_{type_}',
    '$print': lambda type_:'$print_bool' if 'i32' in f'$print_{type_}' else f'$print_{type_}'
}

def ident_to_wasm_id(x:Ident) -> WasmId:
    return WasmId("$"+x.name)

def compileDataType(type_:Any) -> str:
    if (isinstance(type_, int) or type_ == int or isinstance(type_, Int)) and not isinstance(type_, bool):
        return 'i64'
    elif isinstance(type_, str) and type_.lower() in ["integer", "int", "i", "i64"]:
        return 'i64'
    else:
        return 'i32'

def get_ty(e:exp) -> ty:
    ty_ = e.ty
    if type(ty_) == NotVoid:
        return ty_.ty
    else:
        raise ValueError("Expected exp to have an return type.")

def ty_to_string(ty_:ty) -> str:
    if type(ty_) == Int:
        return "i64"
    else:
        return "i32"

def extract_ty(ty_: optional[resultTy]) -> Union[ty, None]:
    if ty_:
        if type(ty_) == NotVoid:
            return ty_.ty
        else:
            # in such cases we expect to don't use the type
            return None
    else:
        # in such cases we expect to don't use the type
        return None

def extract_deep_ty(e:exp) -> Union[ty, None]:
    match e:
        case IntConst(value=_, ty=ty_):
            return extract_ty(ty_)
        case BoolConst(value=_, ty=ty_):
            return extract_ty(ty_)
        case Name(name=_, ty=ty_):
            return extract_ty(ty_)
        case Call(name=_, args=args_, ty=ty_):
            if type(ty_) == NotVoid:
                return ty_.ty
            else:
                for cur_arg in args_:
                    ty_ = extract_deep_ty(cur_arg)
                    if ty_:
                        return ty_
                    else:
                        continue
                return None
        case UnOp(op=_, arg=arg_, ty=_):
            return extract_deep_ty(arg_)
        case BinOp(left=left_, op=_, right=right_, ty=ty_):
            if type(ty_) == NotVoid:
                return ty_.ty

            ty_ = extract_deep_ty(left_)
            if ty_:
                return ty_
            else:
                return extract_deep_ty(right_)




# ---------------
# >>> Compile <<<
# ---------------
def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    # type-checking
    vars = loop_tychecker.tycheckModule(m)
    
    # # compiling statements
    # instrs = compileStmts(m.stmts)

    # compiling statements
    stmts:list[stmt] = m.stmts
    env_ctx:array_transform.Ctx = array_transform.Ctx()
    stmt_a:list[atom.stmt] = array_transform.transStmts(stmts, env_ctx)
    instrs = compileStmts(stmt_a)
    
    # generating Wasm module
    idMain = WasmId('$main')
    locals: list[Any] = []
    for key, value in vars.items():
        locals += [[ident_to_wasm_id(key), compileDataType(value.ty)]]
    
    return WasmModule(
                imports=wasmImports(cfg.maxMemSize),
                exports=[WasmExport("main", WasmExportFunc(idMain))],
                globals=[],
                data=[],
                funcTable=WasmFuncTable([]),
                funcs=[WasmFunc(idMain, [], None, locals, instrs)]
            )

# FIXME -> should handle now atom stmt not normal stmt
def compileStmts(stmts:list[stmt]) -> list[WasmInstr]:
    instrs:list[Union[WasmInstrL, WasmInstr, WasmInstrLoop]] = []

    for cur_stmt in stmts:
        match cur_stmt:
            case StmtExp(exp=e):
                instrs += compileExp(e)
            case Assign(var=var, right=right):
                instrs += compileExp(right)
                instrs += [WasmInstrVarLocal(op='set', id=WasmId('$'+var.name))]
            case IfStmt(cond=cond, thenBody=thenBody, elseBody=elseBody):
                instrs += compileExp(cond)
                thenBody = compileStmts(thenBody)
                elseBody = compileStmts(elseBody)
                instrs += [WasmInstrIf(resultType=None, thenInstrs=thenBody, elseInstrs=elseBody)]
            case WhileStmt(cond=cond, body=body):
                entry_jump_label = WasmId('$loop_start')
                exit_jump_label = WasmId('$loop_exit')

                loop_body = compileExp(cond)
                loop_body += [WasmInstrIf(resultType=None, 
                                         thenInstrs=[], 
                                         elseInstrs=[WasmInstrBranch(exit_jump_label, conditional=False)]
                                        )]
                loop_body += compileStmts(body)
                loop_body += [WasmInstrBranch(entry_jump_label, conditional=False)]

                block_body:list[WasmInstr] = [WasmInstrLoop(label=entry_jump_label, body=loop_body)]

                instrs += [WasmInstrBlock(label=exit_jump_label, result=None, body=block_body)]

    return instrs

def compileExp(e: exp) -> list[WasmInstr]:
    instrs:list[Union[WasmInstrL, WasmInstr, WasmInstrLoop]] = []

    match e:
        case IntConst(value=value):
            instrs += [WasmInstrConst(ty='i64', val=value)]
        case BoolConst(value=value):
            instrs += [WasmInstrConst(ty='i32', val=1 if value else 0)]    # alt: int(...)
        case Name(name=name):
            instrs += [WasmInstrVarLocal(op='get', id=WasmId('$'+name.name))]
        case Call(name=name, args=args, ty=ty_):
            for arg in args:
                instrs += compileExp(arg)
            
            data_type = extract_deep_ty(Call(name=name, args=args, ty=ty_)) # extract_ty(ty_)

            if not data_type:
                raise TypeError(f"Could not find a datatype (searched recursivly).\n    Call -> '{name}'\n         -> args: {args}\n         -> ty: {ty_}")

            if "$"+name.name not in FUNC_MAPPER.keys():
                raise ValueError(f"The name '${name.name}' does not exist in FUNC_MAPPER!")
            instrs += [WasmInstrCall(id=WasmId(FUNC_MAPPER["$"+name.name](ty_to_string(data_type))))]
        case UnOp(op=op, arg=arg):
            match op: 
                case USub():
                    instrs += [WasmInstrConst(ty='i64', val=-1)]
                    instrs += compileExp(arg)
                    instrs += [WasmInstrNumBinOp(ty='i64', op='mul')]
                case Not():
                    # xor:
                    # 1 0 = 1
                    # 1 1 = 0
                    instrs += [WasmInstrConst(ty='i32', val=1)]
                    instrs += compileExp(arg)
                    instrs += [WasmInstrNumBinOp(ty='i32', op='xor')]
        case BinOp(left=left, op=op, right=right, ty=ty_):
            # get type
            ty_ = extract_deep_ty(left)

            processed_left:list[WasmInstr] = compileExp(left)
            processed_right:list[WasmInstr] = compileExp(right)
            
            if ty_ == Int() and any([op == cur_op for cur_op in [Add(), Sub(), Mul()]]):
                instrs += processed_left
                instrs += processed_right
                
                match op:
                    case Add(): 
                        op = 'add'
                    case Sub(): 
                        op = 'sub'
                    case Mul(): 
                        op = 'mul'
                    case _: 
                        op = 'mul'
                instrs += [WasmInstrNumBinOp(ty='i64', op=op)]
            elif ty_ == Int() and any([op == cur_op for cur_op in [Less(), LessEq(), Greater(), GreaterEq(), Eq(), NotEq()]]):
                instrs += processed_left
                instrs += processed_right
                
                match op:
                    case Less():
                        op = 'lt_s'
                    case LessEq():
                        op = 'le_s'
                    case Greater():
                        op = 'gt_s' 
                    case GreaterEq():
                        op = 'ge_s'
                    case Eq():
                        op = 'eq'
                    case NotEq():
                        op = 'ne'
                    case _: 
                        op = 'ne'

                instrs += [WasmInstrIntRelOp(ty='i64', op=op)]

            elif ty_ == Bool() and any([op == cur_op for cur_op in [And(), Or(), Eq(), NotEq()]]):
                match op:
                    case Eq():
                        instrs += processed_left
                        instrs += processed_right
                        instrs += [WasmInstrIntRelOp(ty='i32', op='eq')]
                    case NotEq():
                        instrs += processed_left
                        instrs += processed_right
                        instrs += [WasmInstrIntRelOp(ty='i32', op='ne')]
                    case And():
                        instrs += processed_left
                        instrs += [WasmInstrIf(resultType="i32", 
                                                thenInstrs=processed_right,
                                                elseInstrs=[WasmInstrConst(ty='i32', val=0)]
                                                )
                                    ]
                    case Or():
                        instrs += processed_left
                        instrs += [WasmInstrIf(resultType="i32", 
                                                thenInstrs=[WasmInstrConst(ty='i32', val=1)], 
                                                elseInstrs=processed_right
                                                )
                                    ]
                    case _: 
                        raise Exception(f"Do not handle operator: {op}")
            else:
                raise Exception(f"Did not handle operator: {op} with type {ty_}")

    return instrs









