#
# PC-BASIC 3.23 - backend_cli.py
#
# CLI interface 
#
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import sys
import time
import os

import plat
import unicodepage
import backend

# cursor is visible
cursor_visible = True

# current row and column for cursor
cursor_row = 1 
cursor_col = 1

# last row and column printed on
last_row = 1
last_col = 1
    

if plat.system == 'Windows':
    import WConio as wconio
    import msvcrt

    # Ctrl+Z to exit
    eof = '\x1A'
    
    def term_echo(on=True):
        pass
            
    def getc():
        # won't work under WINE
        if not msvcrt.kbhit():
            return ''
        return msvcrt.getch()
    
    def replace_scancodes(s):
        # windows scancodes should be the same as gw-basic ones
        return s.replace('\xe0', '\0')
        
    def clear_line():
        wconio.gotoxy(0, wconio.wherey())
        wconio.clreol()
    
    def move_left(num):
        if num < 0:
            return
        x = wconio.wherex() - num
        if x < 0:
            x = 0
        wconio.gotoxy(x, wconio.wherey())
        
    def move_right(num):
        if num < 0:
            return
        x = wconio.wherex() + num
        wconio.gotoxy(x, wconio.wherey())

    class WinTerm(object):
        def write(self, s):
            for c in s:
                wconio.putch(c)
        def flush(self):
            pass

    def putc_at(row, col, c, for_keys=False):
        global last_col
        if for_keys:
            return
        update_position(row, col)
        # Windows CMD doesn't do UTF8, output raw & set codepage with CHCP
        wconio.putch(c)
        last_col += 1

    def putwc_at(row, col, c, d, for_keys=False):
        global last_col
        if for_keys:
            return
        update_position(row, col)
        # Windows CMD doesn't do UTF8, output raw & set codepage with CHCP
        wconio.putch(c)
        wconio.putch(d)
        last_col += 2

    term = WinTerm()

else:
    import tty, termios, select
    # ANSI escape codes for output, need arrow movements and clear line and esc_to_scan under Unix.
    import ansi

    # output to stdout
    term = sys.stdout

    # Ctrl+D to exit
    eof = '\x04'

    term_echo_on = True
    term_attr = None

    def term_echo(on=True):
        global term_attr, term_echo_on
        # sets raw terminal - no echo, by the character rather than by the line
        fd = sys.stdin.fileno()
        if (not on) and term_echo_on:
            term_attr = termios.tcgetattr(fd)
            tty.setraw(fd)
        elif not term_echo_on and term_attr != None:
            termios.tcsetattr(fd, termios.TCSADRAIN, term_attr)
        previous = term_echo_on
        term_echo_on = on    
        return previous

    def getc():
        if select.select([sys.stdin], [], [], 0)[0] == []:
            return ''
        return os.read(sys.stdin.fileno(), 1)        
        
    def replace_scancodes(s):    
        # avoid confusion of NUL with scancodes    
        s = s.replace('\0', '\0\0')
        # first replace escape sequences in s with scancodes
        # this plays nice with utf8 as long as the scan codes are all in 7 bit ascii, ie no \00\f0 or above    
        for esc in ansi.esc_to_scan:
            s = s.replace(esc, ansi.esc_to_scan[esc])
        return s

    def clear_line():
        term.write(ansi.esc_clear_line)
    
    def move_left(num):
        term.write(ansi.esc_move_left*num)

    def move_right(num):
        term.write(ansi.esc_move_right*num)

    def putc_at(row, col, c, for_keys=False):
        global last_col
        if for_keys:
            return
        update_position(row, col)
        # this doesn't recognise DBCS
        term.write(unicodepage.UTF8Converter().to_utf8(c))
        term.flush()
        last_col += 1

    def putwc_at(row, col, c, d, for_keys=False):
        global last_col
        if for_keys:
            return
        update_position(row, col)
        # this does recognise DBCS
        try:
            term.write(unicodepage.UTF8Converter().to_utf8(c+d))
        except KeyError:
            term.write('  ')
        term.flush()
        last_col += 2

def prepare(args):
    pass

def init():
    term_echo(False)
    term.flush()
    return True
        
def supports_graphics_mode(mode_info):
    return False
    
def init_screen_mode(mode_info, is_text_mode=False):
    pass
    
def close():
    term_echo()
    term.flush()

def idle():
    time.sleep(0.024)
    
def move_cursor(crow, ccol):
    global cursor_row, cursor_col
    cursor_row, cursor_col = crow, ccol

def check_events():
    check_keyboard()
    update_position()

def update_position(row=None, col=None):
    global last_row, last_col
    if row == None:
        row = cursor_row
    if col == None:
        col = cursor_col
    # move cursor if necessary
    if row != last_row:
        term.write('\r\n')
        term.flush()
        last_col = 1
        last_row = row
        # show what's on the line where we are. 
        # note: recursive by one level, last_row now equals row
        # this reconstructs DBCS buffer, no need to do that
        backend.redraw_row(0, cursor_row, wrap=False)
    if col != last_col:
        move_left(last_col-col)
        move_right(col-last_col)
        term.flush()
        last_col = col

def clear_rows(cattr, start, stop):
    if start == cursor_row and stop == cursor_row:
        update_position(None, 1)
        clear_line()
        term.flush()
        update_position()

def scroll(from_line, scroll_height, attr):
    term.write('\r\n')
    term.flush()

def scroll_down(from_line, scroll_height, attr):
    pass

def check_keyboard():
    global pre_buffer
    s = ''
    # drain input buffer of all charaters available
    while True:
        c = getc()
        # break if stdin has no more characters to read
        if c == '':
            break
        s += c    
    if s == '':    
        return
    s = replace_scancodes(s)
    # replace utf-8 with codepage
    # convert into unicode codepoints
    u = s.decode('utf-8')
    # then handle these one by one as UTF-8 sequences
    c = ''
    for uc in u:                    
        c += uc.encode('utf-8')
        if c == '\x03':         # ctrl-C
            backend.insert_special_key('break')
        if c == eof:            # ctrl-D (unix) / ctrl-Z (windows)
            backend.insert_special_key('quit')
        elif c == '\x7f':       # backspace
            backend.insert_key('\b')
        elif c == '\0':    
            # scancode; go add next char
            continue
        else:
            try:
                backend.insert_key(unicodepage.from_utf8(c))
            except KeyError:    
                backend.insert_key(c)    
        c = ''

def update_palette(new_palette, colours, colours1):
    pass
    
def set_colorburst(on, palette, colours, colours1):
    pass

def update_cursor_attr(attr):
    pass
    
def update_cursor_visibility(cursor_on):
    pass
            
def set_attr(attr):
    pass

def set_page(vpage, apage):
    pass

def copy_page(src, dst):
    pass
        
def build_cursor(width, height, from_line, to_line):
    pass

def load_state():
    pass
            
def set_border(attr):
    pass
                
