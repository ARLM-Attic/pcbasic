#
# PC-BASIC 3.23 - novideo.py
#
# Filter interface 
# implements basic "video" I/O for redirected input streams
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import sys
import time
#import os
#import logging
from functools import partial

import unicodepage
import console
import plat
import state
#import oslayer
import redirect

# don't allow switch to graphics mode
supports_graphics = False

# palette is ignored
max_palette = 64

# unused, but needs to be defined
colorburst = False

# replace lf with cr
lf_to_cr = False

##############################################        
        
def prepare(args):
    pass        
        
def init():
    global lf_to_cr
    # use redirection echos; avoid double echos on resuming 
    if not state.loaded or state.console_state.backend_name != __name__:
        redirect.set_output(sys.stdout, utf8=True)
    # on unix ttys, replace input \n with \r 
    # setting termios won't do the trick as it will not trigger read_line, gets too complicated    
    if plat.system != 'Windows' and sys.stdin.isatty():
        lf_to_cr = True
    return True    

def check_keys():
    s = sys.stdin.readline().decode('utf-8')
    if s == '':
        state.console_state.input_closed = True
    for u in s:
        c = u.encode('utf-8')
        # replace LF -> CR if needed
        if c == '\n' and lf_to_cr:
            c = '\r'
        try:
            console.insert_key(unicodepage.from_utf8(c))
        except KeyError:        
            console.insert_key(c)
        
def idle():
    time.sleep(0.024)
    
def check_events():
    check_keys()

##############################################

def putc_at(row, col, c):
    pass
        
def putwc_at(row, col, c, d):
    pass
            
def close():
    pass
    
def clear_rows(attr, start, stop):
    pass

def init_screen_mode():
    pass

def copy_page(src, dst):
    pass

def scroll(from_line):
    pass
    
def scroll_down(from_line):
    pass

def update_cursor_attr(attr):
    pass
        
def update_palette():
    pass

def update_cursor_visibility(cursor_on):
    pass

def set_attr(cattr):
    pass
    
def build_cursor(width, height, from_line, to_line):
    pass

def load_state():
    pass

