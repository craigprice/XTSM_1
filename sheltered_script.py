# -*- coding: utf-8 -*-
"""
Created on Wed Dec 18 18:49:21 2013

@author: Nate

Module for running untrusted scripts - intended for XTSM analysis script 
execution.  Defines a "sandboxed" context for running a nearly arbitrary script
with a timeout and access to a whitelist of standard modules as well as Python
builtins.  It DOES NOT do a good job of preventing malicious code.  It DOES NOT
limit the memory available to a script.


The problem with this routine is that globals associated with the function
execute_script are automatically passed to the child process, so the run time
is surprisingly long for simple scripts - since the larger modules like numpy
are pickled in order to be passed.  this is solvable by burdening the 
scripts with their own import statements, but the import alone takes fractions
of seconds.  This overhead problem of seeding subprocesses with code and data
is likely not solvable, since serialization and communication will be unavoidable

for reference, pickling a 700*1000 pixel image at 16bit resolution is a 0.25s
operation itself.
"""

import multiprocessing
import time
#import logging
#logger = multiprocessing.log_to_stderr()
#logger.setLevel(logging.INFO)
from functools import wraps
import pdb, sys, StringIO
#import sys, inspect

TEST_GLOBAL=1

#import scipy,numpy,datetime,math,random,itertools,tables,matplotlib
ALLOWED_SCRIPT_MODULES={
#'time':     time,
#'scipy':    scipy,
#'datetime': datetime,
#'math':     math,
#'random':   random,
#'itertools':itertools,
#'tables':   tables,
#'matplotlib':matplotlib
}

class TimeoutException(Exception):
    pass

class RunableProcessing(multiprocessing.Process):
    def __init__(self, func, *args, **kwargs):
        self.queue = multiprocessing.Queue(maxsize=1)
        args = (func,) + args
        #pdb.set_trace()
        multiprocessing.Process.__init__(self, target=self.run_func, args=args, kwargs=kwargs)
    def run_func(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            self.queue.put((True, result))
        except Exception as e:
            self.queue.put((False, e))
    def done(self):
        return self.queue.full()
    def result(self):
        return self.queue.get()

def timeout(function,seconds=5):
    @wraps(function)
    def inner(*args, **kwargs):
        #seconds=5 
        force_kill=True
        now = time.time()
        #pdb.set_trace()
        proc = RunableProcessing(function, *args, **kwargs)
        #pdb.set_trace()
        #t0=time.time()
        proc.start()
        proc.join(seconds)
        #print time.time()-t0
        if proc.is_alive():
            if force_kill:
                proc.terminate()
            runtime = int(time.time() - now)
            raise TimeoutException('timed out after {0} seconds'.format(runtime))
        assert proc.done()
        success, result = proc.result()
        if success:
            return result
        else:
            raise result
    return inner
    
def execute_scripts(scripts,contexts=None):
    """
    executes an array of scripts in a separate process with a timeout mechanism
    and sheltered data contexts, which can be provided as an array of dictionaries.
    All variables defined and assigned in the scripts are appended to the corresponding context
    dictionary and returned.  An allowed list of modules are provided to the 
    script context as defined in ALLOWED_SCRIPT_MODULES above.
    USAGE:  
        >>> timed_execute_scripts({"print numpy.sum(numpy.zeros((3000,3000))*numpy.zeros((3000,3000)))","print 'hi again'\na=1"},[{'b':4},{}])
        0.0
        hi again
        [{'_starttime': 1387735975.468, 'b': 4, '_exectime': 0.1230001449584961}, {'a': 1, '_starttime': 1387735975.592, '_exectime': 0.0}]
    """
    if contexts==None:
        contexts=[]
        for ind in xrange(len(scripts)):
            contexts.append({})
    for script,context in zip(scripts,contexts):
        context.update(ALLOWED_SCRIPT_MODULES)
        old_stdout = sys.stdout
        try:
            capturer = StringIO.StringIO()
            sys.stdout = capturer
            t0=time.time()
            exec script in globals(),context
            t1=time.time()
            context.update({"_starttime":t0,"_exectime":(t1-t0),"_script_console":capturer.getvalue()})
        except Exception as e: 
            context.update({'_SCRIPT_ERROR':e})
#        del context['__builtin__']  # removes the backeffect of exec on context to add builtins
        sys.stdout = old_stdout
        for mod in ALLOWED_SCRIPT_MODULES.keys():
            del context[mod]
    return contexts
timed_execute_scripts=timeout(execute_scripts)

# register a pickle handler for code objects
import copy_reg
import marshal, types
def code_unpickler(data):
    return marshal.loads(data)
def code_pickler(code):
    return code_unpickler, (marshal.dumps(code),)
copy_reg.pickle(types.CodeType, code_pickler, code_unpickler)

