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

import assembly.tac_ast as tac
import assembly.tacSpill_ast as tacSpill
import assembly.mips_ast as mips
from typing import *
from assembly.common import *
import assembly.tacInterp as tacInterp
from assembly.mipsHelper import *
from common.compilerSupport import *

def assignToMips(i: tacSpill.Assign) -> list[mips.instr]:
    raise ValueError('todo')








