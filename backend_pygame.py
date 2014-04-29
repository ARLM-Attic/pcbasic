#
# PC-BASIC 3.23 - backend_pygame.py
#
# Graphical console backend based on PyGame
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

try:
    import pygame
except ImportError:
    pygame = None

try:
    import numpy
except ImportError:
    numpy = None

import plat
if plat.system == 'Android':
    android = True
    # don't do sound for now on Android
    mixer = None   
    numpy = None
    # Pygame for Android-specific definitions
    if pygame:
        import pygame_android
else:
    android = False
    import pygame.mixer as mixer

import logging
import error
import cpi_font
import unicodepage 
import console

import state as state_module
from state import display_state as state

if pygame:
    # CGA palette choices
    gamecolours16 = [ pygame.Color(*rgb) for rgb in [   
        (0x00,0x00,0x00), (0x00,0x00,0xaa), (0x00,0xaa,0x00), (0x00,0xaa,0xaa),
        (0xaa,0x00,0x00), (0xaa,0x00,0xaa), (0xaa,0x55,0x00), (0xaa,0xaa,0xaa), 
        (0x55,0x55,0x55), (0x55,0x55,0xff), (0x55,0xff,0x55), (0x55,0xff,0xff),
        (0xff,0x55,0x55), (0xff,0x55,0xff), (0xff,0xff,0x55), (0xff,0xff,0xff) ] ]

    # EGA palette choices
    gamecolours64 = [ pygame.Color(*rgb) for rgb in [
        (0x00,0x00,0x00), (0x00,0x00,0xaa), (0x00,0xaa,0x00), (0x00,0xaa,0xaa),
        (0xaa,0x00,0x00), (0xaa,0x00,0xaa), (0xaa,0xaa,0x00), (0xaa,0xaa,0xaa), 
        (0x00,0x00,0x55), (0x00,0x00,0xff), (0x00,0xaa,0x55), (0x00,0xaa,0xff),
        (0xaa,0x00,0xff), (0xaa,0x00,0xff), (0xaa,0xaa,0x55), (0xaa,0xaa,0xff),
        (0x00,0x55,0x00), (0x00,0x55,0xaa), (0x00,0xff,0x00), (0x00,0xff,0xaa),
        (0xaa,0x55,0x00), (0xaa,0x55,0xaa), (0xaa,0xff,0x00), (0xaa,0xff,0xaa),
        (0x00,0x55,0x55), (0x00,0x55,0xff), (0x00,0xff,0x55), (0x00,0xff,0xff),
        (0xaa,0x55,0x55), (0xaa,0x55,0xff), (0xaa,0xff,0x55), (0xaa,0xff,0xff),
        (0x55,0x00,0x00), (0x55,0x00,0xaa), (0x55,0xaa,0x00), (0x55,0xaa,0xaa),
        (0xff,0x00,0x00), (0xff,0x00,0xaa), (0xff,0xaa,0x00), (0xff,0xaa,0xaa),
        (0x55,0x00,0x55), (0x55,0x00,0xff), (0x55,0xaa,0x55), (0x55,0xaa,0xff),
        (0xff,0x00,0x55), (0xff,0x00,0xff), (0xff,0xaa,0x55), (0xff,0xaa,0xff),
        (0x55,0x55,0x00), (0x55,0x55,0xaa), (0x55,0xff,0x00), (0x55,0xff,0xaa),
        (0xff,0x55,0x00), (0xff,0x55,0xaa), (0xff,0xff,0x00), (0xff,0xff,0xaa),
        (0x55,0x55,0x55), (0x55,0x55,0xff), (0x55,0xff,0x55), (0x55,0xff,0xff),
        (0xff,0x55,0x55), (0xff,0x55,0xff), (0xff,0xff,0x55), (0xff,0xff,0xff) ] ]

    # for use with get_at
    workaround_palette = [ 
            (0,0,0), (0,0,1), (0,0,2), (0,0,3), (0,0,4), (0,0,5), (0,0,6), (0,0,7),
            (0,0,8), (0,0,9), (0,0,10), (0,0,11), (0,0,12), (0,0,13), (0,0,14), (0,0,15) ]

    # standard palettes
    state.palette64 = [0,1,2,3,4,5,20,7,56,57,58,59,60,61,62,63]
    state.gamepalette = None

    # screen width and height in pixels
    state.size = (0,0)
    state.display_size = (640, 480)
    state.display_size_text = (640, 400)
    
    fullscreen = False
    smooth = False
    # ignore ALT+F4 (and consequently window X button)
    noquit = False

    # letter shapes
    glyphs = []
    fonts = None
    font = None
    state.font_height = 16
    
    # cursor shape
    state.cursor_from = 0
    state.cursor_to = 0    
    cursor0 = None
    # screen & updating 
    screen = None
    surface0 = []
    surface1 = []
        
    screen_changed = True
    cycle = 0
    blink_state = 0
    last_cycle = 0
    cycle_time = 120 #120
    blink_cycles = 5

    # current cursor location
    state.last_row = 1
    state.last_col = 1    
    state.cursor_visible = True
    
    under_cursor = None
    under_top_left = None

    # available joy sticks
    joysticks = []    

    # store for fast get & put arrays
    get_put_store = {}

    keycode_to_scancode = {
        pygame.K_UP:    '\x00\x48',
        pygame.K_DOWN:  '\x00\x50',
        pygame.K_RIGHT: '\x00\x4D',
        pygame.K_LEFT:  '\x00\x4B',
        pygame.K_INSERT:'\x00\x52',
        pygame.K_DELETE:'\x00\x53',
        pygame.K_HOME:  '\x00\x47',
        pygame.K_END:   '\x00\x4F',
        pygame.K_PAGEUP:'\x00\x49',
        pygame.K_PAGEDOWN:'\x00\x51',
        pygame.K_F1:    '\x00\x3B',
        pygame.K_F2:    '\x00\x3C',
        pygame.K_F3:    '\x00\x3D',
        pygame.K_F4:    '\x00\x3E',
        pygame.K_F5:    '\x00\x3F',
        pygame.K_F6:    '\x00\x40',
        pygame.K_F7:    '\x00\x41',
        pygame.K_F8:    '\x00\x42',
        pygame.K_F9:    '\x00\x43',
        pygame.K_F10:   '\x00\x44',
        pygame.K_PRINT: '\x00\x37',
    }
    #K_SYSREQ              sysrq

    ctrl_keycode_to_scancode = {
        pygame.K_RIGHT:     '\x00\x74',
        pygame.K_LEFT:      '\x00\x73',
        pygame.K_HOME:      '\x00\x77',
        pygame.K_END:       '\x00\x75',
        pygame.K_PAGEUP:    '\x00\x84',
        pygame.K_PAGEDOWN:  '\x00\x76',
        pygame.K_BACKSPACE: '\x7F',
        pygame.K_RETURN:    '\x0A',
        pygame.K_TAB:       '',
        pygame.K_1:         '',
        pygame.K_2:         '\x00\x03',
        pygame.K_3:         '',
        pygame.K_4:         '',
        pygame.K_5:         '',
        # <CTRL+6> is passed normally
        pygame.K_7:         '',
        pygame.K_8:         '',
        pygame.K_9:         '\x00\x84',
        pygame.K_0:         '',
        pygame.K_F2:        '\x00\x5F',
        pygame.K_F3:        '\x00\x60',
        pygame.K_MINUS:     '\x1F',
    }

    alt_keycode_to_scancode = {
        # unknown: ESC, BACKSPACE, TAB, RETURN
        pygame.K_1:         '\x00\x78',
        pygame.K_2:         '\x00\x79',
        pygame.K_3:         '\x00\x7A',
        pygame.K_4:         '\x00\x7B',
        pygame.K_5:         '\x00\x7C',
        pygame.K_6:         '\x00\x7D',
        pygame.K_7:         '\x00\x7E',
        pygame.K_8:         '\x00\x7F',
        pygame.K_9:         '\x00\x80',
        pygame.K_0:         '\x00\x81',
        pygame.K_MINUS:     '\x00\x82',
        pygame.K_EQUALS:    '\x00\x83',
        # row 1
        pygame.K_q:         '\x00\x10',
        pygame.K_w:         '\x00\x11',
        pygame.K_e:         '\x00\x12',
        pygame.K_r:         '\x00\x13',
        pygame.K_t:         '\x00\x14',
        pygame.K_y:         '\x00\x15',
        pygame.K_u:         '\x00\x16',
        pygame.K_i:         '\x00\x17',
        pygame.K_o:         '\x00\x18',
        pygame.K_p:         '\x00\x19',
        # row 2
        pygame.K_a:         '\x00\x1E',
        pygame.K_s:         '\x00\x1F',
        pygame.K_d:         '\x00\x20',
        pygame.K_f:         '\x00\x21',
        pygame.K_g:         '\x00\x22',
        pygame.K_h:         '\x00\x23',
        pygame.K_j:         '\x00\x24',
        pygame.K_k:         '\x00\x25',
        pygame.K_l:         '\x00\x26',
        # row 3        
        pygame.K_z:         '\x00\x2C',
        pygame.K_x:         '\x00\x2D',
        pygame.K_c:         '\x00\x2E',
        pygame.K_v:         '\x00\x2F',
        pygame.K_b:         '\x00\x30',
        pygame.K_n:         '\x00\x31',
        pygame.K_m:         '\x00\x32',
        # others    
        pygame.K_F1:        '\x00\x68',
        pygame.K_F2:        '\x00\x69',
        pygame.K_F3:        '\x00\x6A',
        pygame.K_F4:        '\x00\x6B',
        pygame.K_F5:        '\x00\x6C',
        pygame.K_F6:        '\x00\x6D',
        pygame.K_F7:        '\x00\x6E',
        pygame.K_F8:        '\x00\x6F',
        pygame.K_F9:        '\x00\x70',
        pygame.K_F10:       '\x00\x71',
    }
       
    keycode_to_inpcode = {
        # top row
        pygame.K_ESCAPE:    '\x01',
        pygame.K_1:         '\x02',
        pygame.K_2:         '\x03',
        pygame.K_3:         '\x04',
        pygame.K_4:         '\x05',
        pygame.K_5:         '\x06',
        pygame.K_6:         '\x07',
        pygame.K_7:         '\x08',
        pygame.K_8:         '\x09',
        pygame.K_9:         '\x0A',
        pygame.K_0:         '\x0B',
        pygame.K_MINUS:     '\x0C',
        pygame.K_EQUALS:    '\x0D',
        pygame.K_BACKSPACE: '\x0E',
        # row 1
        pygame.K_TAB:       '\x0F',
        pygame.K_q:         '\x10',
        pygame.K_w:         '\x11',
        pygame.K_e:         '\x12',
        pygame.K_r:         '\x13',
        pygame.K_t:         '\x14',
        pygame.K_y:         '\x15',
        pygame.K_u:         '\x16',
        pygame.K_i:         '\x17',
        pygame.K_o:         '\x18',
        pygame.K_p:         '\x19',
        pygame.K_LEFTBRACKET:'\x1A',
        pygame.K_RIGHTBRACKET:'\x1B',
        pygame.K_RETURN:    '\x1C',
        # row 2
        pygame.K_RCTRL:     '\x1D',
        pygame.K_LCTRL:     '\x1D',
        pygame.K_a:         '\x1E',
        pygame.K_s:         '\x1F',
        pygame.K_d:         '\x20',
        pygame.K_f:         '\x21',
        pygame.K_g:         '\x22',
        pygame.K_h:         '\x23',
        pygame.K_j:         '\x24',
        pygame.K_k:         '\x25',
        pygame.K_l:         '\x26',
        pygame.K_SEMICOLON: '\x27',
        pygame.K_QUOTE:     '\x28',
        pygame.K_BACKQUOTE :     '\x29',
        # row 3        
        pygame.K_LSHIFT:    '\x2A',
        pygame.K_HASH:      '\x2B',     # assumes UK keyboard?
        pygame.K_z:         '\x2C',
        pygame.K_x:         '\x2D',
        pygame.K_c:         '\x2E',
        pygame.K_v:         '\x2F',
        pygame.K_b:         '\x30',
        pygame.K_n:         '\x31',
        pygame.K_m:         '\x32',
        pygame.K_COMMA:     '\x33',
        pygame.K_PERIOD:    '\x34',
        pygame.K_SLASH:     '\x35',
        pygame.K_RSHIFT:    '\x36',
        pygame.K_PRINT:     '\x37',
        pygame.K_SYSREQ:    '\x37',
        pygame.K_RALT:      '\x38',
        pygame.K_LALT:      '\x38',
        pygame.K_SPACE:     '\x39',
        pygame.K_CAPSLOCK:  '\x3A',
        # others    
        pygame.K_F1:        '\x3B',
        pygame.K_F2:        '\x3C',
        pygame.K_F3:        '\x3D',
        pygame.K_F4:        '\x3E',
        pygame.K_F5:        '\x3F',
        pygame.K_F6:        '\x40',
        pygame.K_F7:        '\x41',
        pygame.K_F8:        '\x42',
        pygame.K_F9:        '\x43',
        pygame.K_F10:       '\x44',
        pygame.K_NUMLOCK:   '\x45',
        pygame.K_SCROLLOCK: '\x46',
        pygame.K_HOME:      '\x47',
        pygame.K_UP:        '\x48',
        pygame.K_PAGEUP:    '\x49',
        pygame.K_KP_MINUS:  '\x4A',
        pygame.K_LEFT:      '\x4B',
        pygame.K_KP5:       '\x4C',
        pygame.K_RIGHT:     '\x4D',
        pygame.K_KP_PLUS:   '\x4E',
        pygame.K_END:       '\x4F',
        pygame.K_DOWN:      '\x50',
        pygame.K_PAGEDOWN:  '\x51',
        pygame.K_INSERT:    '\x52',
        pygame.K_DELETE:    '\x53',
        pygame.K_BACKSLASH: '\x56',
    }

            
# set constants based on commandline arguments
def prepare(args):
    global fullscreen, smooth, noquit
    try:
        x, y = args.dimensions[0].split(',')
        state.display_size = (int(x), int(y))
    except (ValueError, TypeError):
        pass    
    try:
        x, y = args.dimensions_text[0].split(',')
        state.display_size_text = (int(x), int(y))
    except (ValueError, TypeError):
        pass    
    if args.fullscreen:
        fullscreen = True
    if args.smooth:
        smooth = True    
    if args.noquit:
        noquit = True

def init():
    global fonts, joysticks, physical_size, console_state, state
    # set state objects to whatever is now in state (may have been unpickled)
    console_state = state_module.console_state
    state = state_module.display_state
    if not pygame:
        logging.warning('Could not find PyGame module. Failed to initialise PyGame console.')
        return False     
    pre_init_mixer()   
    pygame.init()
    # exclude some backend drivers as they give unusable results
    if pygame.display.get_driver() == 'caca':
        pygame.display.quit()
        logging.warning('Refusing to open libcaca console. Failed to initialise PyGame console.')
        return False
    fonts = cpi_font.load_codepage(console_state.codepage)
    if fonts == None:
        pygame.display.quit()
        logging.warning('Could not load codepage font. Failed to initialise PyGame console.')
        return False
    unicodepage.load_codepage(console_state.codepage)
    # get physical screen dimensions (needs to be called before set_mode)
    display_info = pygame.display.Info()
    physical_size = display_info.current_w, display_info.current_h
    # first set the screen non-resizeable, to trick things like maximus into not full-screening
    # I hate it when applications do this ;)
    pygame.display.set_icon(build_icon())
    if not fullscreen:
        pygame.display.set_mode(state.display_size_text, 0, 8)
    resize_display(*state.display_size_text, initial=True)
    pygame.display.set_caption('PC-BASIC 3.23')
    pygame.key.set_repeat(500, 24)
    if android:
        pygame_android.init()
    init_mixer()
    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
    for j in joysticks:
        j.init()
    return True

def resize_display(width, height, initial=False): 
    global display, screen_changed
    global fullscreen
    display_info = pygame.display.Info()
    flags = pygame.RESIZABLE
    if fullscreen or (width, height) == physical_size:
        fullscreen = True
        flags |= pygame.FULLSCREEN | pygame.NOFRAME
        width, height = state.display_size if (not initial and console_state.screen_mode != 0) else state.display_size_text
        # scale suggested dimensions to largest integer times pixel size that fits
        scale = min( physical_size[0]//width, physical_size[1]//height )
        width, height = width * scale, height * scale
    if (width, height) == (display_info.current_w, display_info.current_h) and not initial:
        return
    if smooth:
        display = pygame.display.set_mode((width, height), flags)
    else:
        display = pygame.display.set_mode((width, height), flags, 8)    
    if not initial and not smooth:
        display.set_palette(state.gamepalette)
        # load display if requested    
    screen_changed = True    
    
def close():
    if android:
        pygame_android.close()
    pygame.joystick.quit()
    pygame.display.quit()    

def get_palette_entry(index):
    return state.palette64[index]

def set_palette(new_palette=None):
    if console_state.num_palette == 64:
        state.palette64 = new_palette if new_palette else [0,1,2,3,4,5,20,7,56,57,58,59,60,61,62,63]
        state.gamepalette = [ gamecolours64[i] for i in state.palette64 ]
    elif console_state.num_colours>=16:
        state.palette64 = new_palette if new_palette else [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
        state.gamepalette = [ gamecolours16[i] for i in state.palette64 ]
    elif console_state.num_colours==4:
        state.palette64 = new_palette if new_palette else [0, 11, 13, 15]
        state.gamepalette = [ gamecolours16[i] for i in state.palette64 ]
    else:
        state.palette64 = new_palette if new_palette else [0, 15]
        state.gamepalette = [ gamecolours16[i] for i in state.palette64 ]
    if not smooth:
        display.set_palette(state.gamepalette)

def set_palette_entry(index, colour):
    state.palette64[index] = colour
    if console_state.num_palette==64:
        state.gamepalette[index] = gamecolours64[colour]
    else:
        state.gamepalette[index] = gamecolours16[colour]
    if not smooth:
        display.set_palette_at(index, state.gamepalette[index])
    
def clear_rows(cattr, start, stop):
    global screen_changed
    bg = (cattr>>4) & 0x7
    scroll_area = pygame.Rect(0, (start-1)*state.font_height, state.size[0], (stop-start+1)*state.font_height) 
    surface0[console_state.apagenum].fill(bg, scroll_area)
    surface1[console_state.apagenum].fill(bg, scroll_area)
    screen_changed = True
    
# not in interface
def set_font(new_font_height):
    global font, under_cursor
    state.font_height = new_font_height
    try:
        font = fonts[state.font_height]
    except KeyError:
        font = None
    under_cursor = pygame.Surface((8, state.font_height), depth=8)    

def init_screen_mode(mode, new_font_height):
    global glyphs, cursor0
    set_font(new_font_height)    
    glyphs = [ build_glyph(c, font, state.font_height) for c in range(256) ]
    # initialise glyph colour
    set_attr(console_state.attr)
    # set standard cursor
    cursor0 = pygame.Surface((8, state.font_height), depth=8)
    build_default_cursor(mode, True)
    if mode == 0:
        resize_display(*state.display_size_text)
    else:
        resize_display(*state.display_size)
    return True        
    
def setup_screen(to_height, to_width):
    global screen, screen_changed, surface0, surface1
    state.size = to_width*8, to_height*state.font_height
    screen = pygame.Surface(state.size, depth=8)
    # whole screen (blink on & off)
    surface0 = [ pygame.Surface(state.size, depth=8) for _ in range(console_state.num_pages)]
    surface1 = [ pygame.Surface(state.size, depth=8) for _ in range(console_state.num_pages)]
    for i in range(console_state.num_pages):
        surface0[i].set_palette(workaround_palette)
        surface1[i].set_palette(workaround_palette)
    screen.set_palette(workaround_palette)
    under_cursor.set_palette(workaround_palette)
    screen_changed = True
    
def copy_page(src,dst):
    global screen_changed
    surface0[dst].blit(surface0[src], (0,0))
    surface1[dst].blit(surface1[src], (0,0))
    screen_changed = True
    
def show_cursor(do_show, prev):
    global screen_changed
    if do_show != prev:
        screen_changed = True

def set_cursor_colour(color):
    cursor0.set_palette_at(254, screen.get_palette_at(color))

def build_default_cursor(mode, overwrite):
    global screen_changed
    if overwrite and not mode:
        state.cursor_from, state.cursor_to = state.font_height-2, state.font_height-2
    elif overwrite and mode:
        state.cursor_from, state.cursor_to = 0, state.font_height-1
    else:
        state.cursor_from, state.cursor_to = state.font_height/2, state.font_height-1
    build_cursor()
    screen_changed = True

def build_shape_cursor(from_line, to_line):
    global screen_changed
    if not console_state.screen_mode:
        state.cursor_from = max(0, min(from_line, state.font_height-1))
        state.cursor_to = max(0, min(to_line, state.font_height-1))
        build_cursor()
        screen_changed = True

def scroll(from_line):
    global screen_changed
    temp_scroll_area = pygame.Rect(
                    0, (from_line-1)*state.font_height,
                    console_state.width*8, (console_state.scroll_height-from_line+1)*state.font_height)
    # scroll
    surface0[console_state.apagenum].set_clip(temp_scroll_area)
    surface1[console_state.apagenum].set_clip(temp_scroll_area)
    surface0[console_state.apagenum].scroll(0, -state.font_height)
    surface1[console_state.apagenum].scroll(0, -state.font_height)
    # empty new line
    blank = pygame.Surface( (console_state.width*8, state.font_height) , depth=8)
    bg = (console_state.attr>>4) & 0x7
    blank.set_palette(workaround_palette)
    blank.fill(bg)
    surface0[console_state.apagenum].blit(blank, (0, (console_state.scroll_height-1)*state.font_height))
    surface1[console_state.apagenum].blit(blank, (0, (console_state.scroll_height-1)*state.font_height))
    surface0[console_state.apagenum].set_clip(None)
    surface1[console_state.apagenum].set_clip(None)
    screen_changed = True
   
def scroll_down(from_line):
    global screen_changed
    temp_scroll_area = pygame.Rect(0, (from_line-1)*state.font_height, console_state.width*8, 
                                            (console_state.scroll_height-from_line+1)*state.font_height)
    surface0[console_state.apagenum].set_clip(temp_scroll_area)
    surface1[console_state.apagenum].set_clip(temp_scroll_area)
    surface0[console_state.apagenum].scroll(0, state.font_height)
    surface1[console_state.apagenum].scroll(0, state.font_height)
    # empty new line
    blank = pygame.Surface( (console_state.width*8, state.font_height), depth=8 )
    bg = (console_state.attr>>4) & 0x7
    blank.set_palette(workaround_palette)
    blank.fill(bg)
    surface0[console_state.apagenum].blit(blank, (0, (from_line-1)*state.font_height))
    surface1[console_state.apagenum].blit(blank, (0, (from_line-1)*state.font_height))
    surface0[console_state.apagenum].set_clip(None)
    surface1[console_state.apagenum].set_clip(None)
    screen_changed = True

last_attr = None
last_attr_context = None
def set_attr(cattr):
    global last_attr, last_attr_context
    if cattr == last_attr and (console_state.screen_mode, console_state.apagenum) == last_attr_context:
        return    
    color = (0, 0, cattr & 0xf)
    bg = (0, 0, (cattr>>4) & 0x7)    
    for glyph in glyphs:
        glyph.set_palette_at(255, bg)
        glyph.set_palette_at(254, color)
    last_attr = cattr    
    last_attr_context = console_state.screen_mode, console_state.apagenum
        
def putc_at(row, col, c):
    global screen_changed
    glyph = glyphs[ord(c)]
    blank = glyphs[32] # using SPACE for blank 
    top_left = ((col-1)*8, (row-1)*state.font_height)
    if not console_state.screen_mode:
        surface1[console_state.apagenum].blit(glyph, top_left )
    if last_attr >> 7: #blink:
        surface0[console_state.apagenum].blit(blank, top_left )
    else:
        surface0[console_state.apagenum].blit(glyph, top_left )
    screen_changed = True

def build_glyph(c, font_face, glyph_height):
    color = 254 
    bg = 255 
    glyph = pygame.Surface((8, glyph_height), depth=8)
    glyph.fill(bg)
    face = font_face[c]
    for yy in range(glyph_height):
        c = ord(face[yy])
        for xx in range(8):
            pos = (xx, yy)
            bit = (c >> (7-xx)) & 1
            if bit == 1:
                glyph.set_at(pos, color)
    return glyph            
    
def build_cursor():
    color, bg = 254, 255
    cursor0.set_colorkey(bg)
    cursor0.fill(bg)
    for yy in range(state.font_height):
        for xx in range(8):
            if yy < state.cursor_from or yy > state.cursor_to:
                pass
            else:
                cursor0.set_at((xx, yy), color)

# build the Ok icon
def build_icon():
    icon = pygame.Surface((17, 17), depth=8)
    icon.fill(255)
    icon.fill(254, (1, 8, 8, 8))
    O = build_glyph(ord('O'), fonts[8], 8)
    k = build_glyph(ord('k'), fonts[8], 8)
    icon.blit(O, (1, 0, 8, 8))
    icon.blit(k, (9, 0, 8, 8))
    icon.set_palette_at(255, (0, 0, 0))
    icon.set_palette_at(254, (0xff, 0xff, 0xff))
    pygame.transform.scale2x(icon)
    pygame.transform.scale2x(icon)
    return icon


def refresh_screen():
    if console_state.screen_mode or blink_state == 0:
        screen.blit(surface0[console_state.vpagenum], (0, 0))
    elif blink_state == 1: 
        screen.blit(surface1[console_state.vpagenum], (0, 0))
    
def remove_cursor():
    if not console_state.cursor or console_state.vpage != console_state.apage:
        return
    if under_top_left != None:
        screen.blit(under_cursor, under_top_left)

def refresh_cursor():
    global under_top_left
    if not console_state.cursor or console_state.vpage != console_state.apage:
        return
    # copy screen under cursor
    under_top_left = ( (console_state.col-1)*8, (console_state.row-1)*state.font_height)
    under_char_area = pygame.Rect(
            (console_state.col-1)*8, 
            (console_state.row-1)*state.font_height, 
            console_state.col*8, 
            console_state.row*state.font_height)
    under_cursor.blit(screen, (0,0), area=under_char_area)
    if not console_state.screen_mode:
        # cursor is visible - to be done every cycle between 5 and 10, 15 and 20
        if (cycle/blink_cycles==1 or cycle/blink_cycles==3): 
            screen.blit(cursor0, ( (console_state.col-1)*8, (console_state.row-1)*state.font_height) )
    elif numpy:
        index = console_state.attr & 0xf
        # reference the destination area
        dest_array = pygame.surfarray.pixels2d(screen.subsurface(pygame.Rect(
                            (console_state.col-1)*8, (console_state.row-1)*state.font_height + state.cursor_from, 8, 
                            state.cursor_to - state.cursor_from + 1))) 
        dest_array ^= index
    else:
        index = console_state.attr & 0xf
        # no surfarray if no numpy    
        for x in range((console_state.col-1) * 8, console_state.col * 8):
            for y in range((console_state.row-1)*state.font_height + state.cursor_from, 
                            (console_state.row-1)*state.font_height + state.cursor_to + 1):
                pixel = get_pixel(x,y)
                screen.set_at((x,y), pixel^index)
    state.last_row = console_state.row
    state.last_col = console_state.col
        
def pause_key():
    # pause key press waits for any key down. continues to process screen events (blink) but not user events.
    while not check_events(pause=True):
        # continue playing background music
        console.sound.check_sound()
        idle()
        
def idle():
    pygame.time.wait(cycle_time/blink_cycles/8)  

def check_events(pause=False):
    global screen_changed, fullscreen
    # handle Android pause/resume
    if android and pygame_android.check_events():
        # force immediate redraw of screen
        refresh_screen()
        do_flip()
        # force redraw on next tick  
        # we seem to have to redraw twice to see anything
        screen_changed = True
    # check and handle pygame events    
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if not pause:
                handle_key(event)
            else:
                return True    
        if event.type == pygame.KEYUP:
            if not pause:
                handle_key_up(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Android: toggle keyboard on touch
            if android:
                pygame_android.toggle_keyboard()
            handle_mouse(event)
        elif event.type == pygame.JOYBUTTONDOWN:
            handle_stick(event)    
        elif event.type == pygame.VIDEORESIZE:
            fullscreen = False
            resize_display(event.w, event.h)
        elif event.type == pygame.QUIT:
            if noquit:
                pygame.display.set_caption('PC-BASIC 3.23 - to exit type <CTRL+BREAK> <ESC> SYSTEM')
            else:
                raise error.Exit()      
    check_screen()
    return False

def check_screen():
    global cycle, last_cycle
    global screen_changed
    global blink_state
    if not console_state.screen_mode:
        if cycle == 0:
            blink_state = 0
            screen_changed = True
        elif cycle == blink_cycles*2: 
            blink_state = 1
            screen_changed = True
    tock = pygame.time.get_ticks() 
    if (tock - last_cycle) >= (cycle_time/blink_cycles):
        last_cycle = tock
        cycle += 1
        if cycle == blink_cycles*4: 
            cycle = 0
        cursor_changed = ( (not console_state.screen_mode and cycle%blink_cycles == 0) 
                           or (console_state.row != state.last_row) or (console_state.col != state.last_col) )
        if screen_changed:
            refresh_screen()
            do_flip()
        elif cursor_changed and console_state.cursor:
            remove_cursor()
            do_flip()
        screen_changed = False

def do_flip():
    refresh_cursor()
    if smooth:
        screen.set_palette(state.gamepalette)
        pygame.transform.smoothscale(screen.convert(display), display.get_size(), display)
        screen.set_palette(workaround_palette)    
    else:
        pygame.transform.scale(screen, display.get_size(), display)  
    pygame.display.flip()

def handle_key(e):
    c = ''
    mods = pygame.key.get_mods()
    if android:
        mods |= pygame_android.apply_mods(e) 
    if e.key in (pygame.K_PAUSE, pygame.K_BREAK):
        if mods & pygame.KMOD_CTRL:
            # ctrl-break
            raise error.Break()
        else:
            # pause until keypress
            pause_key()    
    elif e.key == pygame.K_DELETE and mods & pygame.KMOD_CTRL and mods & pygame.KMOD_ALT:
        # if not caught by OS, reset the emulator
        raise error.Reset()
    elif e.key == pygame.K_NUMLOCK and mods & pygame.KMOD_CTRL:
        pause_key()    
    elif e.key == pygame.K_SCROLLOCK and mods & pygame.KMOD_CTRL:
        # ctrl+SCROLLLOCK breaks too
        raise error.Break()
    elif e.key == pygame.K_CAPSLOCK:
        # let CAPS LOCK be handled by the window manager
        pass
    elif e.key == pygame.K_PRINT:
        # these can't be caught by INKEY$ etc:
        if mods & pygame.KMOD_CTRL:
            console.toggle_echo_lpt1()
        elif mods & pygame.KMOD_SHIFT:
            console.print_screen()
    elif e.key == pygame.K_TAB and mods & pygame.KMOD_SHIFT:
        # shift+tab -> \x00\x0F (scancode for TAB) but TAB -> \x09
        c = '\x00\x0F'
    else:
        try:
            if (mods & pygame.KMOD_CTRL):
                c = ctrl_keycode_to_scancode[e.key]
            elif (mods & pygame.KMOD_ALT):
                c = alt_keycode_to_scancode[e.key]
            else:
                c = keycode_to_scancode[e.key]
        except KeyError:
            if android:
                u = pygame_android.get_unicode(e, mods)
            else:
                u = e.unicode    
            c = unicodepage.from_unicode(u)
    console.insert_key(c) 
    # current key pressed; modifiers ignored 
    try:
        console_state.inp_key = ord(keycode_to_inpcode[e.key])
    except KeyError:
        pass    
                    
def handle_key_up(e):
    # last key released gets remembered
    try:
        console_state.inp_key = 0x80 + ord(keycode_to_inpcode[e.key])
    except KeyError:
        pass    
           
def handle_mouse(e):
    if e.button == 1: # LEFT BUTTON
        console.penstick.trigger_pen(e.pos)
                
def handle_stick(e):
    if e.joy < 2 and e.button < 2:
        console.penstick.trigger_stick(e.joy, e.button)
            
##############################################
# penstick interface
# light pen (emulated by mouse) & joystick

# should be True on mouse click events
pen_down = 0
pen_down_pos = (0,0)

stick_fired = [[False, False], [False, False]]

def trigger_pen(pos):
    global pen_down, pen_down_pos
    state.basic_state.pen_handler.triggered = True
    pen_down = -1 # TRUE
    display_info = pygame.display.Info()
    xscale, yscale = display_info.current_w / (1.*state.size[0]), display_info.current_h / (1.*state.size[1])
    pen_down_pos = int(pos[0]//xscale), int(pos[1]//yscale)
                
def trigger_stick(joy, button):
    stick_fired[joy][button] = True
    state.basic_state.strig_handlers[joy*2 + button].triggered = True

def get_pen(fn):
    global pen_down
    display_info = pygame.display.Info()
    xscale, yscale = display_info.current_w / (1.*state.size[0]), display_info.current_h / (1.*state.size[1])
    pos = pygame.mouse.get_pos()
    posx, posy = int(pos[0]//xscale), int(pos[1]//yscale)
    if fn == 0:
        pen_down_old, pen_down = pen_down, 0
        return pen_down_old
    elif fn == 1:
        return min(state.size[0]-1, max(0, pen_down_pos[0]))
    elif fn == 2:
        return min(state.size[1]-1, max(0, pen_down_pos[1]))
    elif fn == 3:
        return -pygame.mouse.get_pressed()[0]
    elif fn == 4:
        return min(state.size[0]-1, max(0, posx))
    elif fn == 5:
        return min(state.size[1]-1, max(0, posy))
    elif fn == 6:
        return min(console_state.height, max(1, 1 + pen_down_pos[1]//state.font_height))
    elif fn == 7:
        return min(console_state.width, max(1, 1 + pen_down_pos[0]//8))
    elif fn == 8:
        return min(console_state.height, max(1, 1 + posy//state.font_height))
    elif fn == 9:
        return min(console_state.width, max(1, 1 + posx//xscale))

def get_stick(fn):
    stick_num, axis = fn//2, fn%2
    if len(joysticks) == 0:
        return 0
    if len(joysticks) < stick_num + 1:
        return 128
    else:
        return int(joysticks[stick_num].get_axis(axis)*127)+128

def get_strig(fn):       
    joy, trig = fn//4, (fn//2)%2
    if joy >= len(joysticks) or trig >= joysticks[joy].get_numbuttons():
        return False
    if fn%2 == 0:
        # has been trig
        stick_was_trig = stick_fired[joy][trig]
        stick_fired[joy][trig] = False
        return stick_was_trig
    else:
        # trig
        return joysticks[joy].get_button(trig)
      
###############################################
# graphics backend interface
# low-level methods (pygame implementation)

graph_view = None


def put_pixel(x, y, index, pagenum=None):
    global screen_changed
    if pagenum == None:
        pagenum = console_state.apagenum
    surface0[pagenum].set_at((x,y), index)
    # empty the console buffer of affected characters
    cx, cy = min(console_state.width-1, max(0, x//8)), min(console_state.height-1, max(0, y//state.font_height)) 
    console_state.pages[pagenum].row[cy].buf[cx] = (' ', console_state.attr)
    screen_changed = True

def get_pixel(x, y, pagenum=None):    
    if pagenum == None:
        pagenum = console_state.apagenum
    return surface0[pagenum].get_at((x,y)).b

def get_graph_clip():
    view = graph_view if graph_view else surface0[console_state.apagenum].get_rect()
    return view.left, view.top, view.right-1, view.bottom-1

def set_graph_clip(x0, y0, x1, y1):
    global graph_view
    graph_view = pygame.Rect(x0, y0, x1-x0+1, y1-y0+1)    
    
def unset_graph_clip():
    global graph_view
    graph_view = None    
    return surface0[console_state.apagenum].get_rect().center

def clear_graph_clip(bg):
    global screen_changed
    surface0[console_state.apagenum].set_clip(graph_view)
    surface0[console_state.apagenum].fill(bg)
    surface0[console_state.apagenum].set_clip(None)
    screen_changed = True

def remove_graph_clip():
    surface0[console_state.apagenum].set_clip(None)

def apply_graph_clip():
    surface0[console_state.apagenum].set_clip(graph_view)

def fill_rect(x0, y0, x1, y1, index):
    global screen_changed
    rect = pygame.Rect(x0, y0, x1-x0+1, y1-y0+1)
    surface0[console_state.apagenum].fill(index, rect)
    cx0, cy0 = min(console_state.width-1, max(0, x0//8)), min(console_state.height-1, max(0, y0//state.font_height)) 
    cx1, cy1 = min(console_state.width-1, max(0, x1//8)), min(console_state.height-1, max(0, y1//state.font_height))
    for r in range(cy0, cy1+1):
        console_state.apage.row[r].buf[cx0:cx1+1] = [(' ', console_state.attr)] * (cx1 - cx0 + 1)
    screen_changed = True

def numpy_set(left, right):
    left[:] = right

def numpy_not(left, right):
    left[:] = right
    left ^= (1<<state.console_state.bitsperpixel)-1

def numpy_iand(left, right):
    left &= right

def numpy_ior(left, right):
    left |= right

def numpy_ixor(left, right):
    left ^= right
        
fast_operations = {
    '\xC6': numpy_set, #PSET
    '\xC7': numpy_not, #PRESET
    '\xEE': numpy_iand,
    '\xEF': numpy_ior,
    '\xF0': numpy_ixor,
    }

def fast_get(x0, y0, x1, y1, varname):
    if not numpy:
        return
    # arrays[varname] must exist at this point (or GET would have raised error 5)
    version = state.basic_state.arrays[varname][2]
    # copy a numpy array of the target area
    clip = pygame.surfarray.array2d(surface0[console_state.apagenum].subsurface(pygame.Rect(x0, y0, x1-x0+1, y1-y0+1)))
    get_put_store[varname] = ( x1-x0+1, y1-y0+1, clip, version )

def fast_put(x0, y0, varname, operation_char):
    global screen_changed
    try:
        width, height, clip, version = get_put_store[varname]
    except KeyError:
        # not yet stored, do it the slow way
        return False
    if x0 < 0 or x0 + width > state.size[0] or y0 < 0 or y0 + height > state.size[1]:
        # let the normal version handle errors
        return False    
    # varname must exist at this point (or PUT would have raised error 5)       
    # if the versions are not the same, use the slow method (array has changed since clip was stored)
    if version != state.basic_state.arrays[varname][2]:
        return False
    # reference the destination area
    dest_array = pygame.surfarray.pixels2d(surface0[console_state.apagenum].subsurface(pygame.Rect(x0, y0, width, height))) 
    # apply the operation
    operation = fast_operations[operation_char]
    operation(dest_array, clip)
    cx0, cy0 = min(console_state.width-1, max(0, x0//8)), min(console_state.height-1, max(0, y0//state.font_height)) 
    cx1, cy1 = min(console_state.width-1, max(0, (x0+width)//8)), min(console_state.height-1, max(0, (y0+height)//state.font_height))
    for r in range(cy0, cy1+1):
        console_state.apage.row[r].buf[cx0:cx1+1] = [(' ', console_state.attr)] * (cx1 - cx0 + 1)
    screen_changed = True
    return True

####################################
# sound interface

from math import ceil
import event_loop

music_foreground = True

def music_queue_length():
    # top of sound_queue is currently playing
    return max(0, len(sound_queue)-1)
        
def init_sound():
    return numpy != None
    
def beep():
    play_sound(800, 0.25)

def stop_all_sound():
    global sound_queue
    mixer.quit()
    sound_queue = []
    
# process sound queue in event loop
def check_sound():
    global loop_sound, loop_sound_playing
    if not sound_queue:
        check_quit_sound()
    else:    
        check_init_mixer()
        # stop looping sound, allow queue to pass
        if loop_sound_playing:
            loop_sound_playing.stop()
            loop_sound_playing = None
        if mixer.Channel(0).get_queue() == None:
            if loop_sound:
                # loop the current playing sound; ok to interrupt it with play cos it's the same sound as is playing
                mixer.Channel(0).play(loop_sound, loops=-1)
                sound_queue.pop(0)
                loop_sound_playing = loop_sound                
                loop_sound = None
            else:
                current_list = sound_queue[0]
                if not current_list:
                    sound_queue.pop(0)
                    try:
                        current_list = sound_queue[0]
                    except IndexError:
                        check_quit_sound()
                        return
                pair_to_play = current_list.pop(0)         
                mixer.Channel(0).queue(pair_to_play[0])
                if pair_to_play[1]:
                    loop_sound = pair_to_play[0] 
                    # any next sound in the sound queue will stop this looping sound
                else:   
                    loop_sound = None
        
def wait_music(wait_length=0, wait_last=True):
    while not loop_sound_playing and (
            len(sound_queue) + wait_last - 1 > wait_length 
            or (wait_last and music_queue_length() == 0 and mixer.get_busy())):
        event_loop.idle()
        event_loop.check_events()

def play_sound(frequency, total_duration, fill=1, loop=False):
    check_init_mixer()
    # one wavelength at 37 Hz is 1192 samples at 44100 Hz
    chunk_length = 1192 * 2
    # actual duration and gap length
    duration, gap = fill * total_duration, (1-fill) * total_duration
    if frequency == 0 or frequency == 32767:
        chunk = numpy.zeros(chunk_length, numpy.int16)
    else:
        num_samples = sample_rate / (2.*frequency)
        num_half = ceil(sample_rate/ (2.*frequency))
        # build wavelength of a square wave at max amplitude
        wave0 = numpy.ones(num_half, numpy.int16) * ((1<<(mixer_bits-1)) - 1)
        wave1 = -wave0
        wave0_1 = wave0[:-1]
        wave1_1 = wave1[:-1]
        # build chunk of waves
        chunk = numpy.array([], numpy.int16) 
        half_waves, samples = 0, 0
        while len(chunk) < chunk_length:
            if samples > int(num_samples*half_waves):
                chunk = numpy.concatenate((chunk, wave0_1))
                samples += num_half-1
            else:    
                chunk = numpy.concatenate((chunk, wave0))
                samples += num_half
            half_waves += 1
            if samples > int(num_samples*half_waves):
                chunk = numpy.concatenate((chunk, wave1_1))
                samples += num_half-1
            else:    
                chunk = numpy.concatenate((chunk, wave1))
                samples += num_half                
            chunk = numpy.concatenate((chunk, wave1))
            half_waves += 1
        chunk_length = len(chunk)    
    if not loop:    
        # make the last chunk longer than a normal chunk rather than shorter, to avoid jumping sound    
        floor_num_chunks = max(0, -1 + int((duration * sample_rate) / chunk_length))
        sound_list = [] if floor_num_chunks == 0 else [ (pygame.sndarray.make_sound(chunk), False) ]*floor_num_chunks
        rest_length = int(duration * sample_rate) - chunk_length * floor_num_chunks
    else:
        # attach one chunk to loop
        sound_list = []
        rest_length = chunk_length
    # create the sound queue entry
    sound_list.append((pygame.sndarray.make_sound(chunk[:rest_length]), loop))
    # append quiet gap if requested
    if gap:
        gap_length = gap * sample_rate
        chunk = numpy.zeros(gap_length, numpy.int16)
        sound_list.append((pygame.sndarray.make_sound(chunk), False))
    # at most 16 notes in the sound queue (not 32 as the guide says!)
    wait_music(15)
    sound_queue.append(sound_list)

# implementation

sound_queue = []

mixer_bits = 16
sample_rate = 44100

# quit sound server after quiet period of quiet_quit ticks, to avoid high-ish cpu load from the sound server.
quiet_ticks = 0        
quiet_quit = 200

# loop the sound  in the mixer queue
loop_sound = None
# currrent sound that is looping
loop_sound_playing = None

    
def pre_init_mixer():
    if mixer:
        mixer.pre_init(sample_rate, -mixer_bits, channels=1, buffer=1024) #4096

def init_mixer():    
    if mixer:
        mixer.quit()
    
def check_init_mixer():
    if mixer.get_init() == None:
        mixer.init()
        
def check_quit_sound():
    global quiet_ticks
    if mixer.get_init() == None:
        return
    if music_queue_length() > 0 or mixer.get_busy():
        quiet_ticks = 0
    else:
        quiet_ticks += 1    
        if quiet_ticks > quiet_quit:
            # this is to avoid high pulseaudio cpu load
            if not state_module.basic_state.run_mode:
                mixer.quit()
                quiet_ticks = 0


####################################
# state saving and loading

class PygameDisplayState(state_module.DisplayState):
    def pickle(self):
        self.display_strings = ([], [])
        for s in surface0:    
            self.display_strings[0].append(pygame.image.tostring(s, 'P'))
        for s in surface1:    
            self.display_strings[1].append(pygame.image.tostring(s, 'P'))
        
    def unpickle(self):
        global display_strings, load_flag
        load_flag = True
        display_strings = self.display_strings
        del self.display_strings


# picklable store for surfaces
display_strings = ([], [])
state_module.display = PygameDisplayState()
load_flag = False

def load_state():        
    global screen_changed
    if load_flag:
        try:
            for i in range(len(surface0)):    
                surface0[i] = pygame.image.fromstring(display_strings[0][i], state.size, 'P')
                surface0[i].set_palette(workaround_palette)
            for i in range(len(surface1)):    
                surface1[i] = pygame.image.fromstring(display_strings[1][i], state.size, 'P')
                surface1[i].set_palette(workaround_palette)
            screen_changed = True    
        except IndexError:
            # couldn't load the state correctly; most likely a text screen saved from -t. just redraw what's unpickled.
            console.redraw_text_screen()
        
