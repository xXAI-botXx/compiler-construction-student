
from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as loop_tychecker
from common.compilerSupport import *
# import common.symtab as symtab
# import common.utils as utils
from typing import Union, Any, Callable
# import inspect



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
    # utils.writeTextFile(path="./DEBUGGING.txt", content=f"  -> Try to compile {type_} ({type(type_)}) to wasm data type.")
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

# def str_to_literal()

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
    
    # compiling statements
    instrs = compileStmts(m.stmts)
    # print(f"\n----------\nIn stmts: {m.stmts}\n\nOut instr: {instrs}")
    
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

# See: CC/languaes_formal.pdf/2.2 Evluation Rules
# Slide: Compiling Expressions

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
                # print(f"\nIf got: \n    -> Condition: {cond}\n    -> Then Body: {thenBody}\n    -> elseBody: {elseBody}")
                print(cond)
                print("Processed Cond:")
                print(compileExp(cond))
                instrs += compileExp(cond)
                thenBody = compileStmts(thenBody)
                elseBody = compileStmts(elseBody)
                instrs += [WasmInstrIf(resultType=None, thenInstrs=thenBody, elseInstrs=elseBody)]
                # print(f"\nIf made: \n    -> Condition: {compileExp(cond)}\n    -> Then Body: {thenBody}\n    -> elseBody: {elseBody}")
            case WhileStmt(cond=cond, body=body):
                entry_jump_label = WasmId('$loop_start')
                exit_jump_label = WasmId('$loop_exit')

                loop_body = compileExp(cond)
                # ty_ = extract_deep_ty(cond)
                # if ty_:
                #     ty_ = ty_to_string(ty_)
                # else:
                #     ty_ = None
               
                loop_body += [WasmInstrIf(resultType=None, 
                                         thenInstrs=[], 
                                         elseInstrs=[WasmInstrBranch(exit_jump_label, conditional=False)]
                                        )]
                loop_body += compileStmts(body)
                loop_body += [WasmInstrBranch(entry_jump_label, conditional=False)]

                block_body:list[WasmInstr] = [WasmInstrLoop(label=entry_jump_label, body=loop_body)]

                instrs += [WasmInstrBlock(label=exit_jump_label, result=None, body=block_body)]
            case _: 
                pass

    return instrs

def compileExp(e: exp, spacing=1) -> list[WasmInstr]:
    instrs:list[Union[WasmInstrL, WasmInstr, WasmInstrLoop]] = []

    match e:
        case IntConst(value=value):
            instrs += [WasmInstrConst(ty='i64', val=value)]
        case BoolConst(value=value):
            instrs += [WasmInstrConst(ty='i32', val=1 if value else 0)]    # alt: int(...)
        case Name(name=name):
            instrs += [WasmInstrVarLocal(op='get', id=WasmId('$'+name.name))]
        case Call(name=name, args=args, ty=ty_):
            # args:list[WasmInstr] = []
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
            # print(f"{' '*spacing}{BinOp(left=left, op=op, right=right, ty=ty_)}")

            # get type
            # if type(ty_) == NotVoid:
            #     ty_ = ty_.ty
            # else:
                
            ty_ = extract_deep_ty(left)
            # Wrong!: -> it is the return type, not the opertion type
            # if type(ty_) == NotVoid:
            #     ty_ = ty_.ty 
            # else:
            #     raise ValueError("Unexpected Void in BinOp")
            print(f"{' '*spacing}Found type: {ty_}")

            processed_left:list[WasmInstr] = compileExp(left, spacing=spacing+4)
            processed_right:list[WasmInstr] = compileExp(right, spacing=spacing+4)

            print(f"{' '*spacing}Processed Left: {processed_left}")
            print(f"{' '*spacing}Processed Right: {processed_right}")
            print(f"{' '*spacing}Operator: {op}")
            
            if ty_ == Int() and any([op == cur_op for cur_op in [Add(), Sub(), Mul()]]):
                print(f"{' '*spacing}Go into int, 1")
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
                print(f"{' '*spacing}Go into int, 2")
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
                print(f"{' '*spacing}Go into bool, 1")
                match op:
                    case Eq():
                        instrs += processed_left
                        instrs += processed_right
                        instrs += [WasmInstrIntRelOp(ty='i32', op='eq')]
                        # print(f"right: {processed_right}\nleft: {processed_left}\ncall: WasmInstrIntRelOp(ty='i32', op='eq')")
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
        case _: 
            raise Exception(f"Do not handle exp: {e}")

    print(f"{' '*spacing}Out -> {instrs}")
    return instrs









