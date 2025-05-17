# x = input_int()
# print(x + 2)

# Module(stmts=[
#     Assign(var=Ident(name='x'), 
#            right=Call(name=Ident(name='input_int'), args=[])), 
#     StmtExp(exp=Call(name=Ident(name='print'), 
#                      args=[BinOp(
#                             left=Name(name='x'), 
#                             op=Add(), 
#                             right=IntConst(value=2)
#                             )
#                             ]
#                     )
#             )
#         ]
#     )