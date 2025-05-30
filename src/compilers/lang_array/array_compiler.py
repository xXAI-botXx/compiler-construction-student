# Task: Take loop_compiler.py and change, so it work for array_astAtom

from lang_array.array_astAtom import *    # -> atom
import lang_array.array_ast as plainAst
# from lang_array import array_astCommon
from common.wasm import *
import lang_array.array_tychecker as array_tychecker
import lang_array.array_transform as array_transform
from lang_array.array_compilerSupport import *
from common.compilerSupport import *
# import common.utils as utils
from typing import Union, Any



# --------------
# >>> Helper <<<
# --------------
def ident_to_wasm_id(x:Ident) -> WasmId:
    return WasmId("$"+x.name)

def get_ty_from_exp(e:exp) -> ty:
    ty_ = e.ty
    if type(ty_) == NotVoid:
        return ty_.ty
    else:
        raise ValueError("Expected exp to have an return type.")

def get_ty(ty_:optional[resultTy]) -> ty:
    if type(ty_) == NotVoid:
        return ty_.ty
    else:
        raise ValueError("Expected exp to have an return type.")

def ty_to_string(ty_:ty) -> Union[Literal['i32'], Literal['i64']]:
    match ty_:
        case Int():
            return 'i64'
        case Bool():
            return 'i32'
        case Array():
            return 'i32'    # FIXME

def resolve_fun(f: str, argtys: list[ty]) -> str:
    match (f, argtys):
        case ('input_int', ()): return '$input_i64'
        case ('print', [Int()]): return '$print_i64'
        case ('print', [Bool()]): return '$print_bool'
        # case ('len', [Array()]): return '$len'
        case _:
            raise ValueError(f'Bug: invalid combination of function {f} and argument types {argtys}')

def compileInitArray(lenExp: atomExp, elemTy: ty, cfg: CompilerConfig) -> list[WasmInstr]:
    """
    Generates code to initialize an array without initializing the elements.
    
    Initialization for n elements:
        - Validate length n
        - Allocate the memory
        - Compute the header
        - ArrayInitDyn : set all elements to the same value
        - ArrayInitStatic : set each element individually
    
    class CompilerConfig:
        maxMemSize: int   # (in pages of size 64kb)
        defaultMaxMemSize = (100 * 1024) // 64  # 100MB
        maxArraySize: int # (in bytes)
        defaultMaxArraySize = 50 * 1024 * 1024 # 50MB

    """
    instrs: list[WasmInstr] = []
    # Validate Length
    if type(lenExp) == IntConst:
        len_instr = WasmInstrConst(ty='i64', val=lenExp.value)
    elif type(lenExp) == Name:
        # Name
        len_instr = WasmInstrVarLocal(op="get", id=WasmId(id="$"+lenExp.var.name))
        # raise ValueError(f"Expected len to be a int, but got {type(lenExp)} for len.")
    elif type(lenExp) == BoolConst:
        len_instr = WasmInstrConst(ty='i64', val=int(lenExp.value))
    else:
        raise Exception(f"Type of length is {type(lenExp)}")

    # len < 0 && len > 0
    left: list[WasmInstr] = [len_instr,
               WasmInstrConst(ty='i64', val=0),
               WasmInstrIntRelOp(ty='i64', op='lt_s'),
               ]
    right: list[WasmInstr] = [len_instr,
               WasmInstrConst(ty='i64', val=cfg.maxArraySize),
               WasmInstrIntRelOp(ty='i64', op='gt_s')]

    instrs += [*left,
               WasmInstrIf(resultType="i32", 
                          thenInstrs=right,
                          elseInstrs=[WasmInstrConst(ty='i32', val=0)]
                         )]
    
    thenBody: list[WasmInstr] = Errors.outputError(Errors.arraySize)  # + unreachable?
    thenBody += [WasmInstrTrap()]
    instrs += [WasmInstrIf(resultType=None, thenInstrs=thenBody, elseInstrs=[])]
    
    # Compute Header Value
    instrs += [WasmInstrVarGlobal(op='get', id=Globals.freePtr)]
    instrs += [WasmInstrVarGlobal(op='get', id=Globals.freePtr)]  # save old value $@free_ptr (address of the array)
    instrs += [len_instr]  # length is on top of stack
    instrs += [WasmInstrConvOp(op='i32.wrap_i64')]  # converts length to i32
    instrs += [WasmInstrNumBinOp(ty='i32', op='shl')]  # shift length left by 4 bit
    if type(elemTy) == Array:
        m = 3
    else:
        m = 1
    instrs += [WasmInstrConst(ty='i32', val=m)]  # value for bits 0-3
    instrs += [WasmInstrNumBinOp(ty='i32', op='xor')]  # integrate bits 0-3
    # instrs += [WasmInstrVarGlobal(op='set', id=Globals.freePtr)]  # Store header at $@free_ptr.
    instrs += [WasmInstrMem(ty='i32', op='store')]

    # Move $@free_ptr and return array address.
    instrs += [WasmInstrVarGlobal(op='get', id=Globals.freePtr)]
    instrs += [len_instr]
    instrs += [WasmInstrConvOp(op='i32.wrap_i64')]
    if type(elemTy) in [Array, Bool]:
        s = 4
    else:
        s = 8
    instrs += [WasmInstrConst(ty='i32', val=s)]
    instrs += [WasmInstrNumBinOp(ty='i32', op='mul')]  # multiply length with the size of each element
    instrs += [WasmInstrConst(ty='i32', val=4)]
    instrs += [WasmInstrNumBinOp(ty='i32', op='add')]  # add 4 for the header
    instrs += [WasmInstrVarGlobal(op='get', id=Globals.freePtr)]
    instrs += [WasmInstrNumBinOp(ty='i32', op='add')]  # add the space required by the array to $@free_ptr
    instrs += [WasmInstrVarGlobal(op='set', id=Globals.freePtr)]  # save new $@free_ptr

    return instrs

def arrayLenInstrs() -> list[WasmInstr]:
    """
    Generates code that expects the array address on top of stack and puts the length on top of stack.
    """
    instrs: list[WasmInstr] = []
    instrs += [WasmInstrMem(ty='i32', op='load')]  # load array header
    instrs += [WasmInstrConst(ty='i32', val=4)]
    instrs += [WasmInstrNumBinOp(ty='i32', op='shr_u')]  # shift right by 4 bit to get the length
    instrs += [WasmInstrConvOp(op='i64.extend_i32_u')]  # convert to i64

    return instrs

def arrayOffsetInstrs(arrayExp: atomExp, indexExp: atomExp, ty_:ty, cfg: CompilerConfig) -> list[WasmInstr]:
    """
    Returns instructions that places the memory offset for a certain array element on top of stack.
    """
    instrs: list[WasmInstr] = []

    instrs += compileAtomExp(arrayExp, cfg)

    # Add 4 to skip header
    instrs += [WasmInstrConst(ty='i32', val=4)]
    instrs += [WasmInstrNumBinOp(ty='i32', op='add')]

    instrs += compileAtomExp(indexExp, cfg)

    # Get ELemt Size -> from where?
    if type(ty_) in [Array, Bool]:
        elem_size = 4
    else:
        elem_size = 8
    # elem_size = 8

    # Multiply index by element size
    instrs += [WasmInstrConst(ty='i32', val=elem_size)]
    instrs += [WasmInstrNumBinOp(ty='i32', op='mul')]

    # Add offset to base+4
    instrs += [WasmInstrNumBinOp(ty='i32', op='add')]

    return instrs



# ---------------
# >>> Compile <<<
# ---------------
def compileModule(m: plainAst.mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    # type-checking
    vars = array_tychecker.tycheckModule(m)

    # Transform to atom
    stmts:list[plainAst.stmt] = m.stmts
    env_ctx:array_transform.Ctx = array_transform.Ctx()
    stmts_a:list[stmt] = array_transform.transStmts(stmts, env_ctx)

    # compiling statements
    instrs = compileStmts(stmts_a, cfg)
    
    # generating Wasm module
    idMain = WasmId('$main')
    locals: list[Any] = []
    for key, value in vars.items():
        locals += [[ident_to_wasm_id(key), ty_to_string(value.ty)]]
    for id_, type_ in Locals.decls(): 
        locals += [[id_, type_]]
    
    
    return WasmModule(
                imports=wasmImports(cfg.maxMemSize),
                exports=[WasmExport("main", WasmExportFunc(idMain))],
                globals=Globals.decls(),
                data=Errors.data(),
                funcTable=WasmFuncTable([]),
                funcs=[WasmFunc(idMain, [], None, locals, instrs)]
            )

def compileStmts(stmts:list[stmt], cfg: CompilerConfig) -> list[WasmInstr]:
    instrs:list[Union[WasmInstrL, WasmInstr, WasmInstrLoop]] = []

    for cur_stmt in stmts:
        match cur_stmt:
            case StmtExp(exp=e):
                instrs += compileExp(e, cfg)
            case Assign(var=var, right=right):
                instrs += compileExp(right, cfg)
                instrs += [WasmInstrVarLocal(op='set', id=WasmId('$'+var.name))]
            case IfStmt(cond=cond, thenBody=thenBody, elseBody=elseBody):
                instrs += compileExp(cond, cfg)
                thenBody = compileStmts(thenBody, cfg)
                elseBody = compileStmts(elseBody, cfg)
                instrs += [WasmInstrIf(resultType=None, thenInstrs=thenBody, elseInstrs=elseBody)]
            case WhileStmt(cond=cond, body=body):
                entry_jump_label = WasmId('$loop_start')
                exit_jump_label = WasmId('$loop_exit')

                loop_body = compileExp(cond, cfg)
                loop_body += [WasmInstrIf(resultType=None, 
                                         thenInstrs=[], 
                                         elseInstrs=[WasmInstrBranch(exit_jump_label, conditional=False)]
                                        )]
                loop_body += compileStmts(body, cfg)
                loop_body += [WasmInstrBranch(entry_jump_label, conditional=False)]

                block_body:list[WasmInstr] = [WasmInstrLoop(label=entry_jump_label, body=loop_body)]

                instrs += [WasmInstrBlock(label=exit_jump_label, result=None, body=block_body)]
            case SubscriptAssign(left=left, index=index, right=right):
                instrs += compileExp(right, cfg)
                ty_ = get_ty(right.ty)
                instrs += arrayOffsetInstrs(arrayExp=left, indexExp=index, ty_=ty_, cfg=cfg)
                if type(ty_) in [Array, Bool]:
                    instrs += [WasmInstrMem(ty='i32', op='store')]
                else:
                    instrs += [WasmInstrMem(ty='i64', op='store')]
    return instrs

def compileExp(e: exp, cfg: CompilerConfig) -> list[WasmInstr]:
    instrs:list[Union[WasmInstrL, WasmInstr, WasmInstrLoop]] = []

    match e:
        case AtomExp(e=e_2, ty=ty_):
            instrs += compileAtomExp(e_2, cfg)
        case Call(var=var_, args=args, ty=ty_):
            for arg in args:
                instrs += compileExp(arg, cfg)
            
            if var_.name == "len":
                instrs += arrayLenInstrs()
            else:
                fun = resolve_fun(var_.name, [get_ty(a.ty) for a in args])
                instrs += [WasmInstrCall(id=WasmId(fun))]
        case UnOp(op=op, arg=arg):
            match op: 
                case USub():
                    instrs += [WasmInstrConst(ty='i64', val=-1)]
                    instrs += compileExp(arg, cfg)
                    instrs += [WasmInstrNumBinOp(ty='i64', op='mul')]
                case Not():
                    # xor:
                    # 1 0 = 1
                    # 1 1 = 0
                    instrs += [WasmInstrConst(ty='i32', val=1)]
                    instrs += compileExp(arg, cfg)
                    instrs += [WasmInstrNumBinOp(ty='i32', op='xor')]
        case BinOp(left=left, op=op, right=right, ty=ty_):
            # get type
            ty_ = get_ty(left.ty)

            processed_left:list[WasmInstr] = compileExp(left, cfg)
            processed_right:list[WasmInstr] = compileExp(right, cfg)
            
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
        case ArrayInitDyn(len=len_, elemInit=elemInit, ty=ty_):
            # instrs += [WasmInstrConst(ty="i32", val=0)]
            # instrs += [WasmInstrVarLocal(op="set", id=WasmId('$@tmp_i32'))]

            str_ty = ty_to_string(get_ty(ty_))

            instrs += [WasmInstrConst(ty="i32", val=100)]
            instrs += compileInitArray(lenExp=len_, elemTy=get_ty(ty_), cfg=cfg)
            instrs += [WasmInstrVarLocal(op="tee", id=WasmId(f"$@tmp_{str_ty}"))]
            instrs += [WasmInstrVarLocal(op="get", id=WasmId(f"$@tmp_{str_ty}"))]
            instrs += [WasmInstrConst(ty=str_ty, val=4)]
            instrs += [WasmInstrNumBinOp(ty=str_ty, op="add")]
            instrs += [WasmInstrVarLocal(op="set", id=WasmId(f"$@tmp_{str_ty}"))]
            
            condition: list[WasmInstr] = [WasmInstrVarLocal(op="get", id=WasmId(f"$@tmp_{str_ty}"))]
            condition += [WasmInstrVarGlobal(op="get", id=WasmId("$@free_ptr"))]
            condition += [WasmInstrIntRelOp(ty=str_ty, op="lt_u")]

            body: list[WasmInstr] = [WasmInstrVarLocal(op="set", id=WasmId(f"$@tmp_{str_ty}"))]
            body += compileAtomExp(elemInit, cfg)
            ty_ = elemInit.ty
            if ty_ != None:
                body += [WasmInstrMem(ty=ty_to_string(ty_), op="store")]
            else:
                raise ValueError("Expected a type but got None!")
            # str_ty = ty_to_string(ty_)
            body += [WasmInstrVarLocal(op="get", id=WasmId(f"$@tmp_{str_ty}"))]
            if str_ty == "i32":
                body += [WasmInstrConst(ty=str_ty, val=4)]
            else:
                body += [WasmInstrConst(ty=str_ty, val=8)]
            body += [WasmInstrNumBinOp(ty=str_ty, op="add")]
            body += [WasmInstrVarLocal(op="set", id=WasmId(f"$@tmp_{str_ty}"))]

            # Create While loop
            entry_jump_label = WasmId('$loop_start')
            exit_jump_label = WasmId('$loop_exit')

            loop_body:list[WasmInstr] = condition
            loop_body += [WasmInstrIf(resultType=None, 
                                        thenInstrs=[], 
                                        elseInstrs=[WasmInstrBranch(exit_jump_label, conditional=False)]
                                    )]
            loop_body += body
            loop_body += [WasmInstrBranch(entry_jump_label, conditional=False)]

            block_body:list[WasmInstr] = [WasmInstrLoop(label=entry_jump_label, body=loop_body)]

            instrs += [WasmInstrBlock(label=exit_jump_label, result=None, body=block_body)]
        case ArrayInitStatic(elemInit=elemInit, ty=ty_):
            # instrs += [WasmInstrConst(ty="i32", val=0)]
            # instrs += [WasmInstrVarLocal(op="set", id=WasmId('$@tmp_i32'))]

            len_ = len(elemInit)
            str_ty = ty_to_string(get_ty(ty_))
            instrs += compileInitArray(lenExp=IntConst(len_), elemTy=get_ty(ty_), cfg=cfg)
            instrs += [WasmInstrVarLocal(op="tee", id=WasmId(f"$@tmp_{str_ty}"))]
            instrs += [WasmInstrVarLocal(op="get", id=WasmId(f"$@tmp_{str_ty}"))]
            instrs += [WasmInstrConst(ty=str_ty, val=4)]
            instrs += [WasmInstrNumBinOp(ty=str_ty, op="add")]

            for idx, cur_elemInit in enumerate(elemInit):
                ty_ = cur_elemInit.ty
                if ty_ is None:
                    raise ValueError("Expected a type but got None!")

                    # cur_elemInit.value
                match cur_elemInit:
                    case IntConst(value=value_, ty=_):
                        value_instr = WasmInstrConst(ty=str_ty, val=value_)
                    case BoolConst(value=value_, ty=_):
                        value_instr = WasmInstrConst(ty=str_ty, val=value_)
                    case Name(var=var, ty=_):
                        value_instr = WasmInstrVarLocal(op="get", id=WasmId(id="$"+var.name))
                        # raise ValueError("Unhandled Class -> Name.")

                if idx == 0:
                    # add elements
                    instrs += [value_instr]
                    instrs += [WasmInstrMem(ty=str_ty, op='store')]
                else:
                    instrs += [WasmInstrVarLocal(op="tee", id=WasmId(f"$@tmp_{str_ty}"))]
                    instrs += [WasmInstrVarLocal(op="get", id=WasmId(f"$@tmp_{str_ty}"))]

                    # add offset
                    instrs += [WasmInstrConst(ty=str_ty, val=12)]
                    instrs += [WasmInstrNumBinOp(ty=str_ty, op="add")]
                    instrs += [value_instr]
                    instrs += [WasmInstrMem(ty=str_ty, op='store')]
        case Subscript(array=array_, index=index_, ty=ty_):
            instrs += arrayOffsetInstrs(arrayExp=array_, indexExp=index_, ty_=get_ty(ty_), cfg=cfg)
            if type(get_ty(ty_)) in [Array, Bool]:
                instrs += [WasmInstrMem(ty='i32', op='load')]
            else:
                instrs += [WasmInstrMem(ty='i64', op='load')]

    return instrs

def compileAtomExp(e: atomExp, cfg: CompilerConfig) -> list[WasmInstr]:
    instrs:list[Union[WasmInstrL, WasmInstr, WasmInstrLoop]] = []

    match e:
        case IntConst(value=value):
            instrs += [WasmInstrConst(ty='i64', val=value)]
        case BoolConst(value=value):
            instrs += [WasmInstrConst(ty='i32', val=1 if value else 0)]    # alt: int(...)
        case Name(var=var_, ty=_):
            instrs += [WasmInstrVarLocal(op='get', id=WasmId('$'+var_.name))]

    return instrs





