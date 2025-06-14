"""
Exercise 2 (10 credits)

In this exercise, you have to implement register allocation by graph coloring. Refer to the lecture
for details of the algorithm (around slide 58).

Put your implementation in the file src/compilers/assembly/graphColoring.py . The file
src/templates/assembly/graphColoring.py provides a good starting point with lots of comm-
ents. Entry point is the function colorInterfGraph .

Completing this exercise does not make all tests run. But you can test your implementation
with the command scripts/run -k test_graphColoring .
"""
from copy import deepcopy as dc

from assembly.common import *
import assembly.tac_ast as tac
import common.log as log
from common.prioQueue import PrioQueue

def chooseColor(x: tac.ident, forbidden: dict[tac.ident, set[int]]) -> int:
    """
    Returns the lowest possible color for variable x that is not forbidden for x.
    """
    forbidden_values = dc(forbidden.get(x, set()))

    color = 0
    not_found_right_color = True
    while not_found_right_color:
      if color not in forbidden_values:
          not_found_right_color = False
          continue
      color += 1

    return color

def colorInterfGraph(g: InterfGraph, secondaryOrder: dict[tac.ident, int]={},
                     maxRegs: int=MAX_REGISTERS) -> RegisterMap:
    """
    Given an interference graph, computes a register map mapping a TAC variable
    to a TACspill variable. You have to implement the "simple graph coloring algorithm"
    from slide 58 here.

    - Parameter maxRegs is the maximum number of registers we are allowed to use.
    - Parameter secondaryOrder is used by the tests to get deterministic results even
      if two variables have the same number of forbidden colors.
    """
    log.debug(f"Coloring interference graph with maxRegs={maxRegs}")
    colors: dict[tac.ident, int] = {}
    forbidden: dict[tac.ident, set[int]] = {}
    # q = PrioQueue(secondaryOrder)
   
    # init blocks/vertices
    blocks: set[tac.Ident] = set()
    for x in list(g.vertices):
        blocks.add(x)

    n_blocks = len(list(g.vertices))
    for _ in range(n_blocks):
        queue = PrioQueue(secondaryOrder)
        for cur_block in list(blocks):
            cur_color_sum = 0
            for cur_color in g.succs(cur_block):
                cur_color_sum += colors[cur_color] if cur_color in colors. keys() else 0
            queue.push(cur_block, cur_color_sum)

        next_block = queue.pop()
        next_color = chooseColor(next_block, forbidden)
        colors[next_block] = next_color

        for cur_block in g.succs(next_block):
            if cur_block not in forbidden.keys():
                forbidden[cur_block] = set()
            forbidden[cur_block].add(next_color)

        blocks.remove(next_block)

    m = RegisterAllocMap(colors, maxRegs)
    return m
