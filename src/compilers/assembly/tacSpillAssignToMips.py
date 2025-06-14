"""
Exercise 3 (10 credits)

The final step is instruction selection . The repository contains a partial implementation of this
step (see src/assembly/tacSpillToMips.py ), but the mapping from TACspill assign instruc-
tions to MIPS assembly is still missing.

Put your implementation in src/compilers/assembly/tacSpillAssignToMips.py . The entry
point is the following function:

def assignToMips(i: tacSpill.Assign) -> list[mips.instr]

Template src/templates/assembly/tacSpillAssignToMips.py provides a good starting point.

After completing this exercise (as well as the two preceding exercises), all tests should be run-
ning!

To compile a file test.py to MIPS assembly by hand use the following command (the output
assembly will be in test.as ):

$ scripts/run --lang loop assembly --max-registers 0 test.py test.as

The command for running MIPS assembly is:

$ spim test.as
"""

# import assembly.tac_ast as tac
import assembly.tacSpill_ast as tacSpill
import assembly.mips_ast as mips
from typing import *
from assembly.common import *
# import assembly.tacInterp as tacInterp
from assembly.mipsHelper import *
from common.compilerSupport import *

def assignToMips(i: tacSpill.Assign) -> list[mips.instr]:
    
    if type(i.right) == tacSpill.Prim:
        # whether to move var to register or load constant
        if type(i.right.p) == tacSpill.Name:
            return [mips.Move(reg(i.var), reg(i.right.p.var))]
        elif type(i.right.p) == tacSpill.Const:
            return [mips.LoadI(reg(i.var), imm(i.right.p.value))]
        else:
            raise ValueError()
    elif type(i.right) == tacSpill.BinOp:
        # get op name
        if i.right.op.name.lower() == 'eq':
            op_name = (mips.Eq(), None)
        elif i.right.op.name.lower() == 'ne':
            op_name = (mips.NotEq(), None)
        elif i.right.op.name.lower() == 'gt_s':
            op_name = (mips.Greater(), None)
        elif i.right.op.name.lower() == 'ge_s':
            op_name = (mips.GreaterEq(), None)
        elif i.right.op.name.lower() == 'lt_s':
            op_name = (mips.Less(), mips.LessI())
        elif i.right.op.name.lower() == 'le_s':
            op_name = (mips.LessEq(), None)
        elif i.right.op.name.lower() == 'add':
            op_name = (mips.Add(), mips.AddI())
        elif i.right.op.name.lower() == 'sub':
            op_name = (mips.Sub(), None)
        elif i.right.op.name.lower() == 'mul':
            op_name = (mips.Mul(), None)
        else:
            op_name = (mips.Mul(), None)

        # FIXME every case covered? see mips_ast.py

        # check if right is const or var and left is const or var => 4 passes
        if type(i.right.left) == tacSpill.Name and type(i.right.right) == tacSpill.Name:
            return [mips.Op(op_name[0], 
                            reg(i.var), 
                            reg(i.right.left.var), 
                            reg(i.right.right.var))]
        elif type(i.right.left) == tacSpill.Name and type(i.right.right) == tacSpill.Const:
            # differ between immediate and not immediate
            if type(op_name[1]) in [mips.AddI, mips.LessI]: 
                if op_name[1] is None:
                    raise ValueError()
                return [mips.OpI(op_name[1], 
                                 reg(i.var), 
                                 reg(i.right.left.var), 
                                 imm(i.right.right.value))]
            else:
                return [mips.LoadI(reg(tacSpill.Ident("$t2")), 
                                   imm(i.right.right.value)),
                        mips.Op(op_name[0], 
                                reg(i.var), 
                                reg(i.right.left.var), 
                                reg(tacSpill.Ident("$t2"))
                                )]
        elif type(i.right.left) == tacSpill.Const and type(i.right.right) == tacSpill.Name:
            # differ between immediate and not immediate
            if type(op_name[1]) in [mips.AddI, mips.LessI]: 
                if op_name[1] is None:
                    raise ValueError()
                return [mips.OpI(op_name[1], 
                                 reg(i.var), 
                                 reg(i.right.right.var), 
                                 imm(i.right.left.value))]
            else:
                return [mips.LoadI(reg(tacSpill.Ident("$t2")), 
                                   imm(i.right.left.value)),
                        mips.Op(op_name[0], 
                                reg(i.var), 
                                reg(tacSpill.Ident("$t2")),
                                reg(i.right.right.var)
                                )]
        elif type(i.right.left) == tacSpill.Const and type(i.right.right) == tacSpill.Const:
            if type(op_name[0]) == mips.Add:
                optimized_const_value = i.right.left.value + i.right.right.value
            elif type(op_name[0]) == mips.Sub:
                optimized_const_value = i.right.left.value - i.right.right.value
            elif type(op_name[0]) == mips.Mul:
                optimized_const_value = i.right.left.value * i.right.right.value
            else:
                raise ValueError("Unexpected Const Operator")
            return [mips.LoadI(reg(i.var), 
                               imm(optimized_const_value))]
        else:
            raise ValueError("Does not handle all types.")
            # return []
    else:
        raise ValueError()







