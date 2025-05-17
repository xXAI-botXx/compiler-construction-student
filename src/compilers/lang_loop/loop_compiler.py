
from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as loop_tychecker
from common.compilerSupport import *
# import common.symtab as symtab
import common.utils as utils
from typing import Union, Any, Callable
import inspect



# --------------
# >>> Helper <<<
# --------------
FUNC_MAPPER:dict[str, Callable[[Any], str]] = {
    '$input_int': lambda type_:f'$input_{type_}',
    '$print': lambda type_:'$print_bool' if 'i32' in f'$print_{type_}' else f'$print_{type_}'
}
# (print_bool also exists! -> prints as string)

def ident_to_wasm_id(x:Ident) -> WasmId:
    return WasmId("$"+x.name)

def getVariable(name:str, var_types:dict[str, str]) -> str:
    utils.writeTextFile(path="./DEBUGGING.txt", content=f"Search '{name}' in {var_types}")
    
    for key, value in var_types.items():
        if key == name:
            return value
    return ""

def extractReturntypeFromInstrs(instrs:Union[list[Any], Any], var_types:dict[str, str], only_stack:bool=True) -> str:
    """
    Extracts the return type of Wasm Instructions.
    """
    if not isinstance(instrs, list):
        instrs = [instrs]

    # find datatype of if/while body
    data_type:str = ""
    for cur_instr in instrs:
        cur_instr:Any
        if isinstance(cur_instr, WasmInstrVarLocal) and cur_instr.op == "get":
            var_name = cur_instr.id.id.replace("$", "")
            if var_name not in var_types.keys():
                raise KeyError(f"Error during extracting returntype from instructions.\n'{var_name}' not found in vars: {var_types}.")
            data_type = var_types[var_name]
        
        if not only_stack:
            if isinstance(cur_instr, WasmInstrConst):
                data_type = cur_instr.ty
            elif isinstance(cur_instr, WasmInstrCall) and (cur_instr.id.id.startswith("input") or cur_instr.id.id.startswith("$input")):
                data_type =  cur_instr.id.id.split("_")[-1]
            elif isinstance(cur_instr, WasmInstrNumBinOp):
                data_type = cur_instr.ty
            elif isinstance(cur_instr, WasmInstrIntRelOp):
                data_type = cur_instr.ty
                data_type = "i32"

    if data_type == "int64":
        data_type = "i64"
    elif data_type == "int32":
        data_type = "i32"
    return data_type

def extractReturntypeFromPythonInstrs(instrs:Union[Any, list[Any]], var_types:dict[str, str], only_stack:bool=True) -> str:
    """
    Extracts the return type of Python Loop Language Instructions.
    """
    if not isinstance(instrs, list):
        instrs = [instrs]

    # find datatype of if/while body
    data_type:str = ""
    for cur_instr in instrs:
        cur_instr:Any
        if isinstance(cur_instr, Name):
            # cur_instr.ty
            var_name = cur_instr.name.name.replace("$", "")
            if var_name not in var_types.keys():
                raise KeyError(f"Error during extracting returntype from instructions.\n'{var_name}' not found in vars: {var_types}.")
            data_type = var_types[var_name]
        
        if not only_stack:
            if isinstance(cur_instr, IntConst):
                data_type = "i64"
            elif isinstance(cur_instr, BoolConst):
                data_type = "i32"
            elif isinstance(cur_instr, Call) and cur_instr.name.name.startswith("input"):
                data_type = compileDataType( cur_instr.name.name.split("_")[-1] )
            elif isinstance(cur_instr, BinOp):
                data_type = extractReturntypeFromPythonInstrs(cur_instr.right, var_types)
            elif isinstance(cur_instr, UnOp):
                data_type = extractReturntypeFromPythonInstrs(cur_instr.arg, var_types)

    return data_type

def compileDataType(type_:Any) -> str:
    utils.writeTextFile(path="./DEBUGGING.txt", content=f"  -> Try to compile {type_} ({type(type_)}) to wasm data type.")
    if (isinstance(type_, int) or type_ == int or isinstance(type_, Int)) and not isinstance(type_, bool):
        return 'i64'
    elif isinstance(type_, str) and type_.lower() in ["integer", "int", "i", "i64"]:
        return 'i64'
    else:
        return 'i32'

def extractStmt(statements:list[Any], var_types:dict[str, str]) -> dict[str, str]:
    utils.writeTextFile(path="./DEBUGGING.txt", content=f"Try to extract stmt: {statements} (current var_types: {var_types})")
    # if not isinstance(statements, list):
    #     statements = [statements]

    for cur_stmt in statements:
        if isinstance(cur_stmt, Assign):
            if isinstance(cur_stmt.right, IntConst) or isinstance(cur_stmt.right, BoolConst):
                var_types[cur_stmt.var.name] = compileDataType(cur_stmt.right.value)

            if isinstance(cur_stmt.right, Name) and isinstance(cur_stmt.right.ty, NotVoid):
                var_types[cur_stmt.var.name] = compileDataType(cur_stmt.right.ty.ty)

            if isinstance(cur_stmt.right, Call) and cur_stmt.right.name.name in ["input_str", "input_int"]:
                var_types[cur_stmt.var.name] = 'i64'

            if isinstance(cur_stmt.right, UnOp) and isinstance(cur_stmt.right.ty, NotVoid):
                var_types[cur_stmt.var.name] = compileDataType(cur_stmt.right.ty.ty)

            if isinstance(cur_stmt.right, BinOp) and isinstance(cur_stmt.right.ty, NotVoid):
                var_types[cur_stmt.var.name] = compileDataType(cur_stmt.right.ty.ty)
        elif isinstance(cur_stmt, StmtExp):
            extractStmt([cur_stmt.exp], var_types)
        elif isinstance(cur_stmt, IfStmt):
            # var_types = extractStmt(cur_stmt.thenBody, var_types)
            # var_types = extractStmt(cur_stmt.elseBody, var_types)
            extractStmt(cur_stmt.thenBody, var_types)
            extractStmt(cur_stmt.elseBody, var_types)
        elif isinstance(cur_stmt, WhileStmt):
            # var_types = extractStmt(cur_stmt.body, var_types)
            extractStmt(cur_stmt.body, var_types)
        elif isinstance(cur_stmt, Name) and isinstance(cur_stmt.ty, NotVoid):
            var_types[cur_stmt.name.name] = compileDataType(cur_stmt.ty.ty)
        elif isinstance(cur_stmt, Call) and cur_stmt.name.name in ["input_str", "input_int"]:
            extractStmt(cur_stmt.args, var_types)
        elif isinstance(cur_stmt, Call) and cur_stmt.name.name in ["print"]:
            pass
        elif isinstance(cur_stmt, UnOp) and isinstance(cur_stmt.ty, NotVoid):
            extractStmt([cur_stmt.arg], var_types)
        elif isinstance(cur_stmt, BinOp) and isinstance(cur_stmt.ty, NotVoid):
            extractStmt([cur_stmt.left], var_types)
            extractStmt([cur_stmt.right], var_types)
        else:
            raise ValueError(f"Did not handled '{cur_stmt}' (type={type(cur_stmt)}).")

    return var_types






# ---------------
# >>> Compile <<<
# ---------------
def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    utils.writeTextFile(path="./DEBUGGING.txt", content=f"\n{'-'*32}")
    # type-checking
    vars = loop_tychecker.tycheckModule(m)
    
    # compiling statements
    var_types:dict[str, str] = dict()
    var_types = extractStmt(m.stmts, var_types)
    
    utils.writeTextFile(path="./DEBUGGING.txt", content=f"\nScript run from: {[cur_stack.filename for cur_stack in inspect.stack()]}\nVars: {var_types}")
    instrs = compileStmts(m.stmts, var_types)

    utils.writeTextFile(path="./DEBUGGING.txt", content=f"\n\n\nWasm Result Code:\n\n{'\n'.join([str(cur_instr) for cur_instr in instrs])}")
    
    # generating Wasm module
    idMain = WasmId('$main')
    locals: list[Any] = []
    for key, value in vars.items():
        locals += [[ident_to_wasm_id(key), compileDataType(value.ty)]]    # value
    # ty: T
    # definitelyAssigned: bool
    # scope: Scope
    
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

def compileStmts(stmts:list[Any], var_types:dict[Any, Any]={}) -> list[Any]:
    instrs:list[Union[WasmInstrL, WasmInstr, WasmInstrLoop]] = []

    # if not isinstance(stmts, list):
    #     stmts = [stmts]

    for cur_stmt in stmts:
        utils.writeTextFile(path="./DEBUGGING.txt", content=f"Statement: {cur_stmt}")
        match cur_stmt:
            case StmtExp(exp=exp):
                instrs += compileExps([exp], var_types)
            case Assign(var=var, right=right):
                # utils.writeTextFile(path="./DEBUGGING.txt", content=f"Assign var: {var}, {right}")
                instrs += compileExps([right], var_types)
                instrs += [WasmInstrVarLocal(op='set', id=WasmId('$'+var.name))]
            case IfStmt(cond=cond, thenBody=thenBody, elseBody=elseBody):
                instrs += compileExps([cond], var_types)
                thenBody = compileStmts(thenBody, var_types)
                elseBody = compileStmts(elseBody, var_types)

                # data_type = extractReturntypeFromInstrs(thenBody+elseBody, var_types)

                instrs += [WasmInstrIf(resultType=None, thenInstrs=thenBody, elseInstrs=elseBody)]
            case WhileStmt(cond=cond, body=body):
                # cond = compileExps([cond])
                # thenBody = compileStmts(body, var_types)
                # data_type = extractReturntypeFromInstrs(thenBody, var_types)

                entry_jump_label = WasmId('$loop_start')
                exit_jump_label = WasmId('$loop_exit')

                loop_body = compileExps([cond], var_types)
                loop_body += [WasmInstrIf(resultType=None, 
                                         thenInstrs=[], 
                                         elseInstrs=[WasmInstrBranch(exit_jump_label, conditional=False)]
                                        )]
                loop_body += compileStmts(body, var_types)
                loop_body += [WasmInstrBranch(entry_jump_label, conditional=False)]

                block_body:list[WasmInstr] = [WasmInstrLoop(label=entry_jump_label, body=loop_body)]

                instrs += [WasmInstrBlock(label=exit_jump_label, result=None, body=block_body)]
            case _: 
                pass

        utils.writeTextFile(path="./DEBUGGING.txt", content=f" -> Return statements: {instrs}")

    return instrs

def compileExps(exps: Union[list[Any], Any], var_types:dict[Any, Any]={}) -> list[Any]:
    instrs:list[Union[WasmInstrL, WasmInstr, WasmInstrLoop]] = []

    # if not isinstance(exps, list):
    #     exps = [exps]

    for cur_exp in exps:
        utils.writeTextFile(path="./DEBUGGING.txt", content=f"Expression: {cur_exp}")
        match cur_exp:
            case IntConst(value=value):
                instrs += [WasmInstrConst(ty='i64', val=value)]
            case BoolConst(value=value):
                instrs += [WasmInstrConst(ty='i32', val=1 if value else 0)]    # alt: int(...)
            case Name(name=name):
                instrs += [WasmInstrVarLocal(op='get', id=WasmId('$'+name.name))]
            case Call(name=name, args=args, ty=ty):
                args:list[Any] = compileExps(args, var_types)
                instrs += args

                utils.writeTextFile(path="./DEBUGGING.txt", content=f"Call '{name}' '{ty}' args: {args}")
                try:
                    parameter = args[0] # if isinstance(args, list) and len(args) >= 1 else args
                except Exception:
                    parameter = args
                # if isinstance(ty, NotVoid):
                #     data_type = compileDataType(ty.ty)
                # else:
                data_type:Any = ""
                try:
                    match parameter:
                        case WasmInstrCall(id=WasmId(id=id_str)) if "input" in id_str:
                            data_type = "i64"
                        case WasmInstrCall(id=WasmId(id=id_str)) if "print" in id_str:
                            data_type = id_str.split("_")[-1]
                        case WasmInstrIntRelOp(ty=ty):
                            data_type = ty
                        case WasmInstrNumBinOp(ty=ty):
                            data_type = ty
                        case WasmGlobal(ty=ty):
                            data_type = ty
                        case WasmInstrConst(ty=ty):
                            data_type = ty
                        case _:
                            raise Exception("Custom Exception")
                    # if isinstance(parameter, WasmInstrCall) and "input" in parameter.id.id:
                    #     data_type = "i64"
                    # elif isinstance(parameter, WasmInstrCall) and "print" in parameter.id.id:
                    #     data_type = parameter.ty
                    # elif isinstance(parameter, WasmInstrIntRelOp):
                    #      data_type = parameter.ty
                    # elif isinstance(parameter, WasmInstrNumBinOp):
                    #      data_type = parameter.ty
                    # elif isinstance(parameter, WasmGlobal):
                    #      data_type = parameter.ty
                    # elif isinstance(parameter, WasmInstrConst):
                    #      data_type = parameter.ty
                    # else:
                    #     raise Exception("Custom Exception")
                        # data_type = cast(str, parameter.ty)
                except Exception:
                    if name.name == "input_int":
                        data_type = 'i64'
                    else:
                        if isinstance(parameter, WasmInstrVarLocal):
                            data_type = getVariable(parameter.id.id.replace("$", ""), var_types)
                        else:
                            data_type = 'i32'

                    # Call(name=Ident(name='input_int'), args=[], ty=NotVoid(ty=Int()))
                if "$"+name.name not in FUNC_MAPPER.keys():
                    raise ValueError(f"The name '${name.name}' does not exist in FUNC_MAPPER!")
                instrs += [WasmInstrCall(id=WasmId(FUNC_MAPPER["$"+name.name](data_type)))]
            case UnOp(op=op, arg=arg):
                match op: 
                    case USub():
                        instrs += [WasmInstrConst(ty='i64', val=-1)]
                        instrs += compileExps([arg], var_types)
                        instrs += [WasmInstrNumBinOp(ty='i64', op='mul')]
                    case Not():
                        # xor:
                        # 1 0 = 1
                        # 1 1 = 0
                        instrs += [WasmInstrConst(ty='i32', val=1)]
                        instrs += compileExps([arg], var_types)
                        instrs += [WasmInstrNumBinOp(ty='i32', op='xor')]
            case BinOp(left=left, op=op, right=right):
                left:Union[list[Any], Any] = compileExps([left], var_types)
                right:Union[list[Any], Any] = compileExps([right], var_types)
                left_datatype:str = extractReturntypeFromInstrs(left, var_types, only_stack=False)
                right_datatype:str = extractReturntypeFromInstrs(right, var_types, only_stack=False)
                # left_datatype = extractReturntypeFromPythonInstrs(left if isinstance(left, list) else [left], var_types, only_stack=False)
                # right_datatype = extractReturntypeFromPythonInstrs(right if isinstance(right, list) else [left], var_types, only_stack=False)

                if left_datatype == "i64" and right_datatype == "i64" and any([op == cur_op for cur_op in [Add(), Sub(), Mul()]]):
                    instrs += left    # compileExps([left], var_types)
                    instrs += right   # compileExps([right], var_types)
                    
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
                elif left_datatype == "i64" and right_datatype == "i64" and any([op == cur_op for cur_op in [Less(), LessEq(), Greater(), GreaterEq(), Eq(), NotEq()]]):
                    instrs += left    # compileExps([left], var_types)
                    instrs += right   # compileExps([right], var_types)
                    
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

                elif left_datatype == "i32" and right_datatype == "i32" and any([op == cur_op for cur_op in [And(), Or(), Eq(), NotEq()]]):
                    match op:
                        case Eq():
                            instrs += left    # compileExps([left], var_types)
                            instrs += right   # compileExps([right], var_types)
                            instrs += [WasmInstrIntRelOp(ty='i32', op='eq')]
                        case NotEq():
                            instrs += left    # compileExps([left], var_types)
                            instrs += right   # compileExps([right], var_types)
                            instrs += [WasmInstrIntRelOp(ty='i32', op='ne')]
                        case And():
                            instrs += left    # compileExp([left])
                            instrs += [WasmInstrIf(resultType="i32", 
                                                   thenInstrs=right,    # compileExp(right), 
                                                   elseInstrs=[WasmInstrConst(ty='i32', val=0)]
                                                   )
                                      ]
                        case Or():
                            instrs += left    # compileExp([left])
                            instrs += [WasmInstrIf(resultType="i32", 
                                                   thenInstrs=[WasmInstrConst(ty='i32', val=1)], 
                                                   elseInstrs=right    # compileExp(right)
                                                   )
                                      ]
                        case _: 
                            pass
                # else:
                #     raise ValueError(f"Can't solve binary operation '{BinOp(left=left, op=op, right=right)}'"+\
                #                      f"\n   + op: {op}\n   + left-ty: {left_datatype}\n   + right-ty: {right_datatype}"+\
                #                      f"\nCheck 1:\n    -> left == i64 => {left_datatype == 'i64'}\n    -> right == i64 => {right_datatype == 'i64'}\n    -> any([op == cur_op for cur_op in [Add(), Sub(), Mul()]]) => {any([op == cur_op for cur_op in [Add(), Sub(), Mul()]])}"+\
                #                      f"\nCheck 2:\n    -> left == i64 => {left_datatype == 'i64'}\n    -> right == i64 => {right_datatype == 'i64'}\n    -> any([op == cur_op for cur_op in [Less(), LessEq(), Greater(), GreaterEq(), Eq(), NotEq()]]) => {any([op == cur_op for cur_op in [Less(), LessEq(), Greater(), GreaterEq(), Eq(), NotEq()]])}"+\
                #                      f"\nCheck 3:\n    -> left == i32 => {left_datatype == 'i32'}\n    -> right == i32 => {right_datatype == 'i32'}\n    -> any([op == cur_op for cur_op in [And(), Or(), Eq(), NotEq()]]) => {any([op == cur_op for cur_op in [And(), Or(), Eq(), NotEq()]])}")
            case _: 
                pass


    utils.writeTextFile(path="./DEBUGGING.txt", content=f" -> Return Exp Instr.: {instrs}")
    return instrs









