#
# PC-BASIC 3.23 - backend.py
#
# Backend modules and interface events
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import logging

import config
import state 
import timedate
import unicodepage
    
# backend implementations
video = None
audio = None 
penstick = None 

#############################################
# sound queue

state.console_state.music_queue = [[], [], [], []]

#############################################
# keyboard queue

# capslock, numlock, scrollock mode 
state.console_state.caps = False
state.console_state.num = False
state.console_state.scroll = False
# let OS handle capslock effects
ignore_caps = True

# default function keys for KEY autotext
function_key = { 
        '\x00\x3b':0, '\x00\x3c':1, '\x00\x3d':2, '\x00\x3e':3, '\x00\x3f':4,     # F1-F5
        '\x00\x40':5, '\x00\x41':6, '\x00\x42':7, '\x00\x43':8, '\x00\x44':9,     # F6-F10    
        '\x00\x98':10, '\x00\x99':11 } # Tandy F11 and F12, these scancodes should *only* be sent on Tandy
# user definable key list
state.console_state.key_replace = [ 
    'LIST ', 'RUN\r', 'LOAD"', 'SAVE"', 'CONT\r', ',"LPT1:"\r','TRON\r', 'TROFF\r', 'KEY ', 'SCREEN 0,0,0\r', '', '' ]
# keyboard queue
state.console_state.keybuf = ''
# key buffer
# INP(&H60) scancode
state.console_state.inp_key = 0
# keypressed status of caps, num, scroll, alt, ctrl, shift
state.console_state.keystatus = 0
# input has closed
input_closed = False

#############################################
# screen buffer

class ScreenRow(object):
    def __init__(self, bwidth):
        # screen buffer, initialised to spaces, dim white on black
        self.clear()
        # line continues on next row (either LF or word wrap happened)
        self.wrap = False
    
    def clear(self):
        self.buf = [(' ', state.console_state.attr)] * state.console_state.width
        # character is part of double width char; 0 = no; 1 = lead, 2 = trail
        self.double = [ 0 ] * state.console_state.width
        # last non-white character
        self.end = 0    



def redraw_row(start, crow):
    while True:
        therow = state.console_state.apage.row[crow-1]  
        video.set_attr(state.console_state.attr)
        for i in range(start, therow.end): 
            # redrawing changes colour attributes to current foreground (cf. GW)
            # don't update all dbcs chars behind at each put
            put_screen_char_attr(state.console_state.apage, crow, i+1, therow.buf[i][0], state.console_state.attr, one_only=True)
        if therow.wrap and crow >= 0 and crow < state.console_state.height-1:
            crow += 1
            start = 0
        else:
            break    


def put_screen_char_attr(cpage, crow, ccol, c, cattr, one_only=False, for_keys=False):
    cattr = cattr & 0xf if state.console_state.screen_mode else cattr
    # update the screen buffer
    cpage.row[crow-1].buf[ccol-1] = (c, cattr)
    # mark the replaced char for refreshing
    start, stop = ccol, ccol+1
    cpage.row[crow-1].double[ccol-1] = 0
    # mark out sbcs and dbcs characters
    # only do dbcs in 80-character modes
    if unicodepage.dbcs and state.console_state.width == 80:
        orig_col = ccol
        # replace chars from here until necessary to update double-width chars
        therow = cpage.row[crow-1]    
        # replacing a trail byte? take one step back
        # previous char could be a lead byte? take a step back
        if (ccol > 1 and therow.double[ccol-2] != 2 and 
                (therow.buf[ccol-1][0] in unicodepage.trail or therow.buf[ccol-2][0] in unicodepage.lead)):
            ccol -= 1
            start -= 1
        # check all dbcs characters between here until it doesn't matter anymore
        while ccol < state.console_state.width:
            c = therow.buf[ccol-1][0]
            d = therow.buf[ccol][0]  
            if (c in unicodepage.lead and d in unicodepage.trail):
                if therow.double[ccol-1] == 1 and therow.double[ccol] == 2 and ccol > orig_col:
                    break
                therow.double[ccol-1] = 1
                therow.double[ccol] = 2
                start, stop = min(start, ccol), max(stop, ccol+2)
                ccol += 2
            else:
                if therow.double[ccol-1] == 0 and ccol > orig_col:
                    break
                therow.double[ccol-1] = 0
                start, stop = min(start, ccol), max(stop, ccol+1)
                ccol += 1
            if ccol >= state.console_state.width or (one_only and ccol > orig_col):
                break  
        # check for box drawing
        if unicodepage.box_protect:
            ccol = start-2
            connecting = 0
            bset = -1
            while ccol < stop+2 and ccol < state.console_state.width:
                c = therow.buf[ccol-1][0]
                d = therow.buf[ccol][0]  
                if bset > -1 and unicodepage.connects(c, d, bset): 
                    connecting += 1
                else:
                    connecting = 0
                    bset = -1
                if bset == -1:
                    for b in (0, 1):
                        if unicodepage.connects(c, d, b):
                            bset = b
                            connecting = 1
                if connecting >= 2:
                    therow.double[ccol] = 0
                    therow.double[ccol-1] = 0
                    therow.double[ccol-2] = 0
                    start = min(start, ccol-1)
                    if ccol > 2 and therow.double[ccol-3] == 1:
                        therow.double[ccol-3] = 0
                        start = min(start, ccol-2)
                    if ccol < state.console_state.width-1 and therow.double[ccol+1] == 2:
                        therow.double[ccol+1] = 0
                        stop = max(stop, ccol+2)
                ccol += 1        
    # update the screen            
    refresh_screen_range(cpage, crow, start, stop, for_keys)


def get_screen_char_attr(crow, ccol, want_attr):
    ca = state.console_state.apage.row[crow-1].buf[ccol-1][want_attr]
    return ca if want_attr else ord(ca)

def refresh_screen_range(cpage, crow, start, stop, for_keys=False):
    therow = cpage.row[crow-1]
    ccol = start
    while ccol < stop:
        double = therow.double[ccol-1]
        if double == 1:
            ca = therow.buf[ccol-1]
            da = therow.buf[ccol]
            video.set_attr(da[1]) 
            video.putwc_at(crow, ccol, ca[0], da[0], for_keys)
            therow.double[ccol-1] = 1
            therow.double[ccol] = 2
            ccol += 2
        else:
            if double != 0:
                logging.debug('DBCS buffer corrupted at %d, %d', crow, ccol)            
            ca = therow.buf[ccol-1]        
            video.set_attr(ca[1]) 
            video.putc_at(crow, ccol, ca[0], for_keys)
            ccol += 1


class ScreenBuffer(object):
    def __init__(self, bwidth, bheight):
        self.row = [ScreenRow(bwidth) for _ in xrange(bheight)]

def redraw_text_screen():
    # force cursor invisible during redraw
    show_cursor(False)
    # this makes it feel faster
    video.clear_rows(state.console_state.attr, 1, 25)
    # redraw every character
    for crow in range(state.console_state.height):
        therow = state.console_state.apage.row[crow]  
        for i in range(state.console_state.width): 
            put_screen_char_attr(state.console_state.apage, crow+1, i+1, therow.buf[i][0], therow.buf[i][1])
    update_cursor_visibility()

def print_screen():
    for crow in range(1, state.console_state.height+1):
        line = ''
        for c, _ in state.console_state.vpage.row[crow-1].buf:
            line += c
        state.io_state.devices['LPT1:'].write_line(line)

# redirect i/o to file or printer
input_echos = []
output_echos = []

#############################################
# initialisation

def prepare():
    """ Initialise backend module. """
    global pcjr_sound, ignore_caps, egacursor
    if config.options['capture_caps']:
        ignore_caps = False
    # pcjr/tandy sound
    pcjr_sound = config.options['pcjr_syntax']
    # inserted keystrokes
    for u in config.options['keys'].decode('string_escape').decode('utf-8'):
        c = u.encode('utf-8')
        try:
            state.console_state.keybuf += unicodepage.from_utf8(c)
        except KeyError:
            state.console_state.keybuf += c
    egacursor = config.options['video'] == 'ega'
           
def init_video():
    global video
    name = ''
    if video:
        if video.init():
            return True
        name = video.__name__
    logging.warning('Failed to initialise interface %s. Falling back to command-line interface.', name)
    video = backend_cli
    if video and video.init():
        return True
    logging.warning('Failed to initialise command-line interface. Falling back to filter interface.')
    video = novideo
    return video.init()
    
def init_sound():
    global audio
    if audio.init_sound():
        return True
    logging.warning('Failed to initialise sound. Sound will be disabled.')
    audio = nosound
    # rebuild sound queue
    for voice in range(4):    
        for note in state.console_state.music_queue[voice]:
            audio.play_sound(*note)
    return audio.init_sound()
    
def music_queue_length(voice=0):
    # top of sound_queue is currently playing
    return max(0, len(state.console_state.music_queue[voice])-1)

#############################################
# main event checker
    
def check_events():
    # manage sound queue
    audio.check_sound()
    # check console events
    video.check_events()   
    # trigger & handle BASIC events
    if state.basic_state.run_mode:
        # trigger TIMER, PLAY and COM events
        check_timer_event()
        check_play_event()
        check_com_events()
        # KEY, PEN and STRIG are triggered elsewhere
        # handle all events
        for handler in state.basic_state.all_handlers:
            handler.handle()

def idle():
    video.idle()

def wait():
    video.idle()
    check_events()    

##############################
# keyboard buffer read/write

# insert character into keyboard buffer; apply KEY repacement (for use by backends)
def insert_key(c):
    if len(c) > 0:
        try:
            keynum = state.basic_state.event_keys.index(c)
            if keynum > -1 and keynum < 20:
                if state.basic_state.key_handlers[keynum].enabled:
                    # trigger only once at most
                    state.basic_state.key_handlers[keynum].triggered = True
                    # don't enter into key buffer
                    return
        except ValueError:
            pass
    if state.console_state.caps and not ignore_caps:
        if c >= 'a' and c <= 'z':
            c = chr(ord(c)-32)
        elif c >= 'A' and c <= 'z':
            c = chr(ord(c)+32)
    if len(c) < 2:
        state.console_state.keybuf += c
    else:
        try:
            # only check F1-F10
            keynum = function_key[c]
            # can't be redefined in events - so must be event keys 1-10.
            if state.basic_state.run_mode and state.basic_state.key_handlers[keynum].enabled or keynum > 9:
                # this key is being trapped, don't replace
                state.console_state.keybuf += c
            else:
                state.console_state.keybuf += state.console_state.key_replace[keynum]
        except KeyError:
            state.console_state.keybuf += c

# peek character from keyboard buffer
def peek_char():
    ch = ''
    if len(state.console_state.keybuf)>0:
        ch = state.console_state.keybuf[0]
        if ch == '\x00' and len(state.console_state.keybuf) > 0:
            ch += state.console_state.keybuf[1]
    return ch 

# drop character from keyboard buffer
def pass_char(ch):
    state.console_state.keybuf = state.console_state.keybuf[len(ch):]        
    return ch

# blocking keystroke peek
def wait_char():
    while len(state.console_state.keybuf) == 0 and not input_closed:
        wait()
    return peek_char()

#############################################
# cursor

def show_cursor(do_show):
    """ Force cursor to be visible/invisible. """
    video.update_cursor_visibility(do_show)

def update_cursor_visibility():
    """ Set cursor visibility: visible if in interactive mode, unless forced visible in text mode. """
    visible = (not state.basic_state.execute_mode)
    if state.console_state.screen_mode == 0:
        visible = visible or state.console_state.cursor
    video.update_cursor_visibility(visible)

def set_cursor_shape(from_line, to_line):
    """ Set the cursor shape as a block from from_line to to_line (in 8-line modes). Use compatibility algo in higher resolutions. """
    if egacursor:
        # odd treatment of cursors on EGA machines, presumably for backward compatibility
        # the following algorithm is based on DOSBox source int10_char.cpp INT10_SetCursorShape(Bit8u first,Bit8u last)    
        max_line = state.console_state.font_height-1
        if from_line & 0xe0 == 0 and to_line & 0xe0 == 0:
            if (to_line < from_line):
                # invisible only if to_line is zero and to_line < from_line           
                if to_line != 0: 
                    # block shape from *to_line* to end
                    from_line = to_line
                    to_line = max_line
            elif (from_line | to_line) >= max_line or to_line != max_line-1 or from_line != max_line:
                if to_line > 3:
                    if from_line+2 < to_line:
                        if from_line > 2:
                            from_line = (max_line+1) // 2
                        to_line = max_line
                    else:
                        from_line = from_line - to_line + max_line                        
                        to_line = max_line
                        if max_line > 0xc:
                            from_line -= 1
                            to_line -= 1
    state.console_state.cursor_from = max(0, min(from_line, state.console_state.font_height-1))
    state.console_state.cursor_to = max(0, min(to_line, state.console_state.font_height-1))
    video.build_cursor(state.console_state.cursor_width, state.console_state.font_height, 
                state.console_state.cursor_from, state.console_state.cursor_to)
    video.update_cursor_attr(state.console_state.apage.row[state.console_state.row-1].buf[state.console_state.col-1][1] & 0xf)


#############################################
# I/O redirection

def toggle_echo_lpt1():
    lpt1 = state.io_state.devices['LPT1:']
    if lpt1.write in input_echos:
        input_echos.remove(lpt1.write)
        output_echos.remove(lpt1.write)
    else:    
        input_echos.append(lpt1.write)
        output_echos.append(lpt1.write)

            
#############################################
# BASIC event triggers        
        
def check_timer_event():
    mutimer = timedate.timer_milliseconds() 
    if mutimer >= state.basic_state.timer_start + state.basic_state.timer_period:
        state.basic_state.timer_start = mutimer
        state.basic_state.timer_handler.triggered = True

def check_play_event():
    play_now = [music_queue_length(voice) for voice in range(3)]
    if pcjr_sound: 
        for voice in range(3):
            if ( play_now[voice] <= state.basic_state.play_trig and play_now[voice] > 0 and 
                    play_now[voice] != state.basic_state.play_last[voice] ):
                state.basic_state.play_handler.triggered = True 
    else:    
        if state.basic_state.play_last[0] >= state.basic_state.play_trig and play_now[0] < state.basic_state.play_trig:    
            state.basic_state.play_handler.triggered = True     
    state.basic_state.play_last = play_now

def check_com_events():
    ports = (state.io_state.devices['COM1:'], state.io_state.devices['COM2:'])
    for comport in (0, 1):
        if ports[comport] and ports[comport].peek_char():
            state.basic_state.com_handlers[comport].triggered = True


prepare()
