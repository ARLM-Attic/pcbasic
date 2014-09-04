#
# PC-BASIC 3.23 - redirect.py
#
# BASIC-style I/O redirection
# 
# (c) 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import unicodepage
import console

# basic-style redirected input
def load_redirected_input(f):
    # read everything
    all_input = f.read()
    last = ''
    for c in all_input:
        # replace CRLF with CR
        if not (c == '\n' and last == '\r'):
            console.insert_key(c)
        last = c
    console.input_closed = True


def echo_ascii(s, f):
    """ Output redirection echo as raw bytes. """
    f.write(str(s))
                            
# coverter with DBCS lead-byte buffer
utf8conv = unicodepage.UTF8Converter()
    
def echo_utf8(s, f):
    """ Output redirection echo as UTF-8. """
    f.write(utf8conv.to_utf8(str(s), preserve_control=True)) 
    
    
