# -*- coding: utf-8 -*-
"""
Created on Fri Apr 11 10:45:04 2014

@author: Nate
"""

import ast, pdb

class Script():
    def __init__(self,script_string):
        self.script=script_string
    def find_dependencies(self):
        """
        finds the references to undeclared variables as a dictionary
        of variable:line# pairs and attaches them to self.references
        
        also finds the assignments to new variables as a dictionary
        of variable:[line numbers] pairs
        """
        if not hasattr(self,'syn_tree'): self.build_ast()
        sv=self.ScriptVisitor()
        sv.visit(self.syn_tree)
        self.assignments=sv.assignments
        self.references=sv.references
    class ScriptVisitor(ast.NodeVisitor):
        """
        helper-class to allow walking the syntax tree to find assignments
        and references to undeclared variables
        """
        references={}    
        assignments={}    
        def visit_Name(self, node):
            if node.id in self.assignments: return
            self.references.update({node.id:node.lineno})
        def visit_Assign(self, node):
            for targ in node.targets:
                if targ.id in self.assignments:
                    self.assignments[targ.id].append(targ.lineno)
                else: 
                    self.assignments.update({targ.id:[targ.lineno]})
                self.visit(node.value)
    def build_ast(self):
        """
        builds the abstract syntax tree of the script
        """
        self.syn_tree=ast.parse(self.script)

moda="""
[p for p in gor if p != 1]
a=c-d
b=a+k
g=matplotlib.plot()
c=b.gotohell()
c=1
h.update({a:2})
print f
f=4
"""


sc=Script(moda)
