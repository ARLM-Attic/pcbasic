#
# PC-BASIC 3.23  - os_unix.py
#
# UNIX-specific OS utilities
# 
# (c) 2013 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import os
import fcntl
import pexpect

import console
    
shell = '/bin/sh'
shell_cmd = shell + ' -c'


def disk_free(path):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize
    
def spawn_interactive_shell(cmd):
    try:
        p = pexpect.spawn(str(cmd))
    except Exception:
        return 
    while True:
        c = console.get_char()
        if c == '\x08': # BACKSPACE
            p.send('\x7f')
        elif c != '':
            p.send(c)
        while True:
            try:
                c = p.read_nonblocking(1, timeout=0)
            except: 
                c = ''
            if c == '' or c == '\n':
                break
            elif c == '\r':
                console.write('\r\n')    
            elif c == '\x08':
                if console.col != 1:
                    console.col -= 1
            else:
                console.write(c)
        if c == '' and not p.isalive(): 
            return
            
