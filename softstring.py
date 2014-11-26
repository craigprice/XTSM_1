# -*- coding: utf-8 -*-
"""
Created on Sat Apr 26 13:53:54 2014

@author: Nate
"""

def variants(string):
    """
    returns a list of variants of the given string, capitalizing and decapitalizing all
    and first letter
    """
    return [string.upper(),string.lower(),string[0].upper()+string.lower()[1:]]
    
def flattern(A):
    """
    flattens a multidimensional list of strings
    """
    rt = []
    for i in A:
        if isinstance(i,list): rt.extend(flattern(i))
        else: rt.append(i)
    return rt
