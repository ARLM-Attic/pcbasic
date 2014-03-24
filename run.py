#
# PC-BASIC 3.23 - run.py
# Main loops for pc-basic 
# 
# (c) 2013, 3014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import sys
from cStringIO import StringIO
#import cProfile

import error
import util
import tokenise 
import program
import statements 
import fileio
import console

# suppress one prompt by setting to False (used by EDIT)
prompt = True

def loop():
    # main loop 
    while True:
        line = wait_line()
        if execute(line):
            show_prompt()

def show_prompt():
    global prompt
    if prompt:
        console.start_line()
        console.write_line("Ok\xff")
    prompt = True
                          
def wait_line():
    while True:
        try:
            # input loop, checks events
            line = console.wait_screenline(from_start=True) 
        except error.Break:
            continue
        if line:
            return line
                        
def execute(line, ignore_empty_number=False):
    program.direct_line = tokenise.tokenise_line(line)    
    c = util.peek(program.direct_line)
    if c == '\x00':
        try:
            program.store_line(program.direct_line, ignore_empty_number)
            return False
        except error.Error as e:
            e.handle() 
            # prompt
            return True    
    elif c != '':    
        # it is a command, go and execute    
        execution_loop()
        return True
               
# execute any commands
def execution_loop():
    program.direct_line.seek(0)
    program.current_codestream = program.direct_line
    console.show_cursor(False)
    while True:
        try:
            console.check_events()
            if not statements.parse_statement():
                break
        except error.Error as e:
            if not e.handle():
                break
    console.show_cursor()
                   
def exit():
    fileio.close_all()
    sys.exit(0)
    
