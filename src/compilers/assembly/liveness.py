"""
Exercise 1 (15 credits)

In this exercise, you have to implement the liveness analysis . This analysis computes the variable
interference graph for a given control flow graph. Refer to the lecture for details of the algorithm
(around slide 46)

Put your implementation in the file src/compilers/assembly/liveness.py . Entry point of
your implementation is the following function:
def buildInterfGraph(g: ControlFlowGraph) -> InterfGraph

The file src/templates/assembly/liveness.py provides a good starting point with lots of
comments.

Completing this exercise does not make all tests run. But you can test your implementation
with the command scripts/run -k test_liveness .
"""
from copy import deepcopy as dc

from assembly.common import *
from assembly.graph import Graph
import assembly.tac_ast as tac

# See tac_ast.py for help and reference!!!

def instrDef(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers defined by some instrucution.
    """
    identifiers: set[tac.ident] = set()

    if type(instr) == tac.Call and instr.var:
        identifiers.add(instr.var)
    elif type(instr) == tac.Assign:
        identifiers.add(instr.var)

    # also adding GotoIf, Goto, Label ???
    # Maybe FIXME

    return identifiers

def instrUse(instr: tac.instr) -> set[tac.ident]:
    """
    Returns the set of identifiers used by some instrucution.
    """
    identifiers: set[tac.ident] = set()

    if type(instr) == tac.Call:
        # if instr.var:
        #     identifiers.add(instr.var)
        # if instr.name.name.startswith("print"):
        # print(f"\n\nCall: '{instr.name.name}'\n\n")
        if "print" in instr.name.name:
            for cur_arg in instr.args:
                if type(cur_arg) == tac.Name:
                    identifiers.add(cur_arg.var)
    elif type(instr) == tac.Assign:
        # process right
        right_exp: tac.exp = instr.right
        right_set: set[tac.ident] = set()
        if type(right_exp) == tac.BinOp:
            if type(right_exp.left) == tac.Name:
                right_set.add(right_exp.left.var)
            if type(right_exp.right) == tac.Name:
                right_set.add(right_exp.right.var)
        elif type(right_exp) == tac.Prim and type(right_exp.p) == tac.Name:
            right_set.add(right_exp.p.var)

        # update processed right
        identifiers.update(right_set)
    elif type(instr) == tac.GotoIf and type(instr.test) == tac.Name:
        identifiers.add(instr.test.var)
    

    # also adding Goto, Label ???
    # Maybe FIXME

    return identifiers


# Each individual instruction has an identifier. This identifier is the tuple
# (index of basic block, index of instruction inside the basic block)
type InstrId = tuple[int, int]

class InterfGraphBuilder:
    def __init__(self):
        # self.before holds, for each instruction I, to set of variables live before I.
        self.before: dict[InstrId, set[tac.ident]] = {}
        # self.after holds, for each instruction I, to set of variables live after I.
        self.after: dict[InstrId, set[tac.ident]] = {}

    def liveStart(self, bb: BasicBlock, s: set[tac.ident]) -> set[tac.ident]:
        """
        Given a set of variables s and a basic block bb, liveStart computes
        the set of variables live at the beginning of bb, assuming that s
        are the variables live at the end of the block.

        Essentially, you have to implement the subalgorithm "Computing L_start" from
        slide 46 here. You should update self.after and self.before while traversing
        the instructions of the basic block in reverse.
        """
        n_instructions: int = len(bb.instrs)
        if n_instructions == 0:
            return s

        # reverse processing of blocks
        cur_idx = n_instructions -1  # start at last index
        before_idx = cur_idx + 1

        for cur_instr in bb.instrs[::-1]:
            # if not "first" / last block
            if cur_idx != n_instructions-1:
                self.after[(bb.index, cur_idx)] = self.before[(bb.index, before_idx)]
            else:
                self.after[(bb.index, cur_idx)] = s

            # update last block
            defined: set[tac.Ident] = instrDef(cur_instr)
            used: set[tac.Ident] = instrUse(cur_instr)
            updated_before_set: set[tac.Ident] = dc(self.after[(bb.index, cur_idx)])
            updated_before_set.difference_update(defined)
            updated_before_set.update(used)
            self.before[(bb.index, cur_idx)] = updated_before_set

            # next block
            cur_idx -= 1
            before_idx = cur_idx + 1

        return self.before[(bb.index, 0)]

    def liveness(self, g: ControlFlowGraph):
        """
        This method computes liveness information and fills the sets self.before and
        self.after.

        You have to implement the algorithm for computing liveness in a CFG from
        slide 46 here.
        """
        input_: dict[int, set[tac.Ident]] = dict()

        # init dict with a empty set for every block
        for cur_block in g.vertices:
            input_[cur_block] = set()

        have_changes = True
        while have_changes:
            before_input: dict[int, set[tac.Ident]] = dc(input_)

            for cur_block in list(g.vertices)[::-1]:
                cur_block_set: set[tac.ident] = set()

                for cur_successor in g.succs(cur_block):
                    if g.getData(cur_successor).instrs:
                        cur_block_set.update(input_[cur_successor])

                input_[cur_block] = self.liveStart(g.getData(cur_block), cur_block_set)

            # check if now finish -> no changes?
            have_changes = input_ != before_input


    def __addEdgesForInstr(self, instrId: InstrId, instr: tac.instr, interfG: InterfGraph):
        """
        Given an instruction and its ID, adds the edges resulting from the instruction
        to the interference graph.

        You should implement the algorithm specified on the slide
        "Computing the interference graph" (slide 50) here.
        """
        defined: set[tac.Ident] = instrDef(instr)

        for cur_define in defined:
            cur_blocks: Union[set[tac.Ident], None] = self.after[instrId] if instrId in self.after.keys() else None
            if cur_blocks is not None:
                for cur_block in cur_blocks:
                    # if they are not the same add them
                    if cur_block.name != cur_define.name:
                        if not interfG.hasVertex(cur_define):
                            interfG.addVertex(cur_define, None)

                        if not interfG.hasVertex(cur_block):
                            interfG.addVertex(cur_block, None)
                        
                        interfG.addEdge(cur_define, cur_block)

    def build(self, g: ControlFlowGraph) -> InterfGraph:
        """
        This method builds the interference graph. It performs three steps:

        - Use liveness to fill the sets self.before and self.after.
        - Setup the interference graph as an undirected graph containing all variables
          defined or used by any instruction of any basic block. Initially, the
          graph does not have any edges.
        - Use __addEdgesForInstr to fill the edges of the interference graph.
        """
        # set self.before and self.after
        self.liveness(g)

        interf_graph: InterfGraph = Graph[tac.ident, None]('undirected')

        for cur_block in g.vertices:
            for idx, cur_instr in enumerate(list(g.getData(cur_block).instrs)):
                self.__addEdgesForInstr((cur_block, idx), cur_instr, interf_graph)

        return interf_graph

def buildInterfGraph(g: ControlFlowGraph) -> InterfGraph:
    builder = InterfGraphBuilder()
    return builder.build(g)
