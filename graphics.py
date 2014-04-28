#
# PC-BASIC 3.23 - graphics.py
#
# Graphics methods (frontend)
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import error
import fp
import vartypes
import var
import console
import state
import draw_and_play
import util
import state

backend = None

# screen-mode dependent
# screen width and height in pixels
state.console_state.size = (0, 0)
state.console_state.pixel_aspect_ratio = fp.Single.one
state.console_state.bitsperpixel = 4

# real state variables
state.console_state.graph_view_set = False
state.console_state.view_graph_absolute = True
state.console_state.graph_window = None
state.console_state.graph_window_bounds = None
state.console_state.last_point = (0, 0)    


def require_graphics_mode(err=5):
    if not is_graphics_mode():
        raise error.RunError(err)

def is_graphics_mode():
    return backend and state.console_state.screen_mode

def init_graphics_mode(mode, new_font_height):
    if mode==0:
        return
    state.console_state.size = (state.console_state.width*8, state.console_state.height*new_font_height)
    # centre of new graphics screen
    state.console_state.last_point = (state.console_state.width*4, state.console_state.height*new_font_height/2)
    # pixels e.g. 80*8 x 25*14, screen ratio 4x3 makes for pixel width/height (4/3)*(25*14/8*80)
    state.console_state.pixel_aspect_ratio = fp.div(
        fp.Single.from_int(state.console_state.height*new_font_height), 
        fp.Single.from_int(6*state.console_state.width)) 
    if mode in (1, 10):
        state.console_state.bitsperpixel = 2
    elif mode == 2:
        state.console_state.bitsperpixel = 1
    else:
        state.console_state.bitsperpixel = 4

# reset graphics state    
def reset_graphics():
    x0, y0, x1, y1 = backend.get_graph_clip()
    if state.console_state.view_graph_absolute:
        state.console_state.last_point = x0 + (x1-x0)/2, y0 + (y1-y0)/2
    else:
        state.console_state.last_point = (x1-x0)/2, (y1-y0)/2
    draw_and_play.draw_scale = 4
    draw_and_play.draw_angle = 0

def get_colour_index(c):
    if c == -1: # foreground; graphics 'background' attrib is always 0
        c = state.console_state.attr & 0xf
    else:
        c = min(state.console_state.num_colours - 1, max(0, c))
    return c

def check_coords(x, y):
    return min(state.console_state.size[0], max(-1, x)), min(state.console_state.size[1], max(-1, y))
    
### PSET, POINT

def put_point(x, y, c):
    x, y = view_coords(x,y)
    backend.apply_graph_clip()
    backend.put_pixel(x, y, get_colour_index(c))
    backend.remove_graph_clip()
    
def get_point(x, y):
    x, y = view_coords(x, y)
    if x < 0 or x >= state.console_state.size[0]:
        return -1
    if y < 0 or y >= state.console_state.size[1]:
        return -1
    return backend.get_pixel(x,y)

### WINDOW coords

def set_graph_window(fx0, fy0, fx1, fy1, cartesian=True):
    if fy0.gt(fy1):
        fy0, fy1 = fy1, fy0
    if fx0.gt(fx1):
        fx0, fx1 = fx1, fx0
    if cartesian:
        fy0, fy1 = fy1, fy0
    left,top, right,bottom = backend.get_graph_clip()
    x0, y0 = fp.Single.zero, fp.Single.zero 
    x1, y1 = fp.Single.from_int(right-left), fp.Single.from_int(bottom-top)        
    scalex, scaley = fp.div(fp.sub(x1, x0), fp.sub(fx1,fx0)), fp.div(fp.sub(y1, y0), fp.sub(fy1,fy0)) 
    offsetx, offsety = fp.sub(x0, fp.mul(fx0,scalex)), fp.sub(y0, fp.mul(fy0,scaley))
    state.console_state.graph_window = scalex, scaley, offsetx, offsety
    state.console_state.graph_window_bounds = fx0, fy0, fx1, fy1, cartesian

def unset_graph_window():
    state.console_state.graph_window = None
    state.console_state.graph_window_bounds = None

# input logical coords, output physical coords
def window_coords(fx, fy, step=False):
    if state.console_state.graph_window:
        scalex, scaley, offsetx, offsety = state.console_state.graph_window
        fx0, fy0 = get_window_coords(state.console_state.last_point) if step else (fp.Single.zero.copy(), fp.Single.zero.copy())    
        x = fp.add(offsetx, fp.mul(fx0.iadd(fx), scalex)).round_to_int()
        y = fp.add(offsety, fp.mul(fy0.iadd(fy), scaley)).round_to_int()
    else:
        x, y = state.console_state.last_point if step else (0, 0)
        x += fx.round_to_int()
        y += fy.round_to_int()
    # overflow check
    if x < -0x8000 or y < -0x8000 or x > 0x7fff or y > 0x7fff:
        raise error.RunError(6)    
    return x, y

# inverse function
# input physical coords, output logical coords
def get_window_coords(x, y):
    x, y = fp.Single.from_int(x), fp.Single.from_int(y)
    if state.console_state.graph_window:
        scalex, scaley, offsetx, offsety = state.console_state.graph_window
        return fp.div(fp.sub(x, offsetx), scalex), fp.div(fp.sub(y, offsety), scaley)
    else:
        return x, y

def window_scale(fx, fy):
    if state.console_state.graph_window:
        scalex, scaley, offsetx, offsety = state.console_state.graph_window
        return fp.mul(fx, scalex).round_to_int(), fp.mul(fy, scaley).round_to_int()
    else:
        return fx.round_to_int(), fy.round_to_int()

### LINE
            
def draw_box_filled(x0, y0, x1, y1, c):
    x0, y0 = view_coords(x0, y0)
    x1, y1 = view_coords(x1, y1)
    c = get_colour_index(c)
    if y1 < y0:
        y0, y1 = y1, y0
    if x1 < x0:
        x0, x1 = x1, x0    
    backend.apply_graph_clip()
    backend.fill_rect(x0, y0, x1, y1, c)
    backend.remove_graph_clip()
    
def draw_line(x0, y0, x1, y1, c, pattern=0xffff):
    c = get_colour_index(c)
    x0, y0 = check_coords(*view_coords(x0, y0))
    x1, y1 = check_coords(*view_coords(x1, y1))
    if y1 <= y0:
        # work from top to bottom, or from x1,y1 if at the same height. this matters for mask.
        x1, y1, x0, y0 = x0, y0, x1, y1
    # Bresenham algorithm
    dx, dy = abs(x1-x0), abs(y1-y0)
    steep = dy > dx
    if steep:
        x0, y0, x1, y1 = y0, x0, y1, x1
        dx, dy = dy, dx
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    mask = 0x8000
    error = dx / 2
    x, y = x0, y0
    backend.apply_graph_clip()
    for x in xrange(x0, x1+sx, sx):
        if pattern&mask != 0:
            if steep:
                backend.put_pixel(y, x, c)
            else:
                backend.put_pixel(x, y, c)
        mask >>= 1
        if mask == 0:
            mask = 0x8000
        error -= dy
        if error<0:
            y += sy
            error += dx    
    backend.remove_graph_clip()
    
def draw_straight(x0, y0, x1, y1, c, pattern, mask):
    if x0 == x1:
        p0, p1, q, direction = y0, y1, x0, 'y' 
    else:
        p0, p1, q, direction = x0, x1, y0, 'x'
    sp = 1 if p1 > p0 else -1
    for p in range (p0, p1+sp, sp):
        if pattern & mask != 0:
            if direction == 'x':
                backend.put_pixel(p, q, c)
            else:
                backend.put_pixel(q, p, c)
        mask >>= 1
        if mask == 0:
            mask = 0x8000
    return mask
                        
def draw_box(x0, y0, x1, y1, c, pattern=0xffff):
    x0, y0 = check_coords(*view_coords(x0, y0))
    x1, y1 = check_coords(*view_coords(x1, y1))
    c = get_colour_index(c)
    mask = 0x8000
    backend.apply_graph_clip()
    mask = draw_straight(x1, y1, x0, y1, c, pattern, mask)
    mask = draw_straight(x1, y0, x0, y0, c, pattern, mask)
    # verticals always drawn top to bottom
    if y0 < y1:
        y0, y1 = y1, y0
    mask = draw_straight(x1, y1, x1, y0, c, pattern, mask)
    mask = draw_straight(x0, y1, x0, y0, c, pattern, mask)
    backend.remove_graph_clip()

### circle, ellipse, sectors

def draw_circle_or_ellipse(x0, y0, r, start, stop, c, aspect):
    if aspect.equals(aspect.one):
        rx, dummy = window_scale(r,fp.Single.zero)
        ry = rx
    else:
        if aspect.gt(aspect.one):
            dummy, ry = window_scale(fp.Single.zero,r)
            rx = fp.div(r, aspect).round_to_int()
        else:
            rx, dummy = window_scale(r,fp.Single.zero)
            ry = fp.mul(r, aspect).round_to_int()
    start_octant, start_coord, start_line = -1, -1, False
    if start:
        start = fp.unpack(vartypes.pass_single_keep(start))
        start_octant, start_coord, start_line = get_octant(start, rx, ry)
    stop_octant, stop_coord, stop_line = -1, -1, False
    if stop:
        stop = fp.unpack(vartypes.pass_single_keep(stop))
        stop_octant, stop_coord, stop_line = get_octant(stop, rx, ry)
    if aspect.equals(aspect.one):
        draw_circle(x0, y0, rx, c, start_octant, start_coord, start_line, stop_octant, stop_coord, stop_line)
    else:
        # TODO - make this all more sensible, calculate only once
        startx, starty, stopx, stopy = -1, -1, -1, -1
        if start != None:
            startx = abs(fp.mul(fp.Single.from_int(rx), fp.cos(start)).round_to_int())
            starty = abs(fp.mul(fp.Single.from_int(ry), fp.sin(start)).round_to_int())
        if stop != None:
            stopx = abs(fp.mul(fp.Single.from_int(rx), fp.cos(stop)).round_to_int())
            stopy = abs(fp.mul(fp.Single.from_int(ry), fp.sin(stop)).round_to_int())
        draw_ellipse(x0, y0, rx, ry, c, start_octant/2, startx, starty, start_line, stop_octant/2, stopx, stopy, stop_line)

def get_octant(mbf, rx, ry):
    neg = mbf.neg 
    if neg:
        mbf.negate()
    octant = 0
    comp = fp.Single.pi4.copy()
    while mbf.gt(comp):
        comp.iadd(fp.Single.pi4)
        octant += 1
        if octant >= 8:
            raise error.RunError(5) # ill fn call
    if octant in (0, 3, 4, 7):
        # running var is y
        coord = abs(fp.mul(fp.Single.from_int(ry), fp.sin(mbf)).round_to_int())
    else:
        # running var is x    
        coord = abs(fp.mul(fp.Single.from_int(rx), fp.cos(mbf)).round_to_int())
    return octant, coord, neg          

# see e.g. http://en.wikipedia.org/wiki/Midpoint_circle_algorithm
def draw_circle(x0, y0, r, c, oct0=-1, coo0=-1, line0=False, oct1=-1, coo1=-1, line1=False):
    c = get_colour_index(c)
    x0, y0 = view_coords(x0, y0)
    if oct0 == -1:
        hide_oct = range(0,0)
    elif oct0 < oct1 or oct0 == oct1 and octant_gte(oct0, coo1, coo0):
        hide_oct = range(0, oct0) + range(oct1+1, 8)
    else:
        hide_oct = range(oct1+1, oct0)
    # if oct1==oct0: 
    # ----|.....|--- : coo1 lt coo0 : print if y in [0,coo1] or in [coo0, r]  
    # ....|-----|... ; coo1 gte coo0: print if y in [coo0,coo1]
    backend.apply_graph_clip()
    x, y = r, 0
    error = 1-r 
    while x >= y:
        for octant in range(0,8):
            if octant in hide_oct:
                continue
            elif oct0 != oct1 and (octant == oct0 and octant_gte(oct0, coo0, y)):
                continue
            elif oct0 != oct1 and (octant == oct1 and octant_gte(oct1, y, coo1)):
                continue
            elif oct0 == oct1 and octant == oct0:
                if octant_gte(oct0, coo1, coo0):
                    if octant_gte(oct0, y, coo1) or octant_gte(oct0, coo0,y):
                        continue
                else:
                    if octant_gte(oct0, y, coo1) and octant_gte(oct0, coo0, y):
                        continue
            backend.put_pixel(*octant_coord(octant, x0, y0, x, y), index=c) 
        # remember endpoints for pie sectors
        if y == coo0:
            coo0x = x
        if y == coo1:
            coo1x = x    
        # bresenham error step
        y += 1
        if error < 0:
            error += 2*y+1
        else:
            x -= 1
            error += 2*(y-x+1)
    if line0:
        draw_line(x0,y0, *octant_coord(oct0, x0, y0, coo0x, coo0), c=c)
    if line1:
        draw_line(x0,y0, *octant_coord(oct1, x0, y0, coo1x, coo1), c=c)
    backend.remove_graph_clip()
    
def octant_coord(octant, x0,y0, x,y):    
    if   octant == 7:     return x0+x, y0+y
    elif octant == 0:     return x0+x, y0-y
    elif octant == 4:     return x0-x, y0+y
    elif octant == 3:     return x0-x, y0-y
    elif octant == 6:     return x0+y, y0+x
    elif octant == 1:     return x0+y, y0-x
    elif octant == 5:     return x0-y, y0+x
    elif octant == 2:     return x0-y, y0-x
    
def octant_gte(octant, y, coord):
    if octant%2 == 1: 
        return y<=coord 
    else: 
        return y>=coord
    
# notes on midpoint algo implementation:
#    
# x*x + y*y == r*r
# look at y'=y+1
# err(y) = y*y+x*x-r*r
# err(y') = y*y + 2y+1 + x'*x' - r*r == err(y) + x'*x' -x*x + 2y+1 
# if x the same:
#   err(y') == err(y) +2y+1
# if x -> x-1:
#   err(y') == err(y) +2y+1 -2x+1 == err(y) +2(y-x+1)

# why initialise error with 1-x == 1-r?
# we change x if the radius is more than 0.5pix out so err(y, r+0.5) == y*y + x*x - (r*r+r+0.25) == err(y,r) - r - 0.25 >0
# with err and r both integers, this just means err - r > 0 <==> err - r +1 >= 0
# above, error == err(y) -r + 1 and we change x if it's >=0.



# ellipse: 
# ry^2*x^2 + rx^2*y^2 == rx^2*ry^2
# look at y'=y+1 (quadrant between points of 45deg slope)
# err == ry^2*x^2 + rx^2*y^2 - rx^2*ry^2
# err(y') == rx^2*(y^2+2y+1) + ry^2(x'^2)- rx^2*ry^2 == err(y) + ry^2(x'^2-x^2) + rx^2*(2y+1)
# if x the same:
#   err(y') == err(y) + rx^2*(2y+1)
# if x' -> x-1:
#   err(y') == err(y) + rx^2*(2y+1) +rx^2(-2x+1)

# change x if radius more than 0.5pix out: err(y, rx+0.5, ry) == ry^2*y*y+rx^2*x*x - (ry*ry)*(rx*rx+rx+0.25) > 0
#  ==> err(y) - (rx+0.25)*(ry*ry) >0
#  ==> err(y) - (rx*ry*ry + 0.25*ry*ry ) > 0 

# break yinc loop if one step no longer suffices


    
# ellipse using midpoint algorithm
# for algorithm see http://members.chello.at/~easyfilter/bresenham.html
def draw_ellipse(cx, cy, rx, ry, c, qua0=-1, x0=-1, y0=-1, line0=False, qua1=-1, x1=-1, y1=-1, line1=False):
    c = get_colour_index(c)
    cx, cy = view_coords(cx, cy)
    # find invisible quadrants
    if qua0 == -1:
        hide_qua = range(0,0)
    elif qua0 < qua1 or qua0 == qua1 and quadrant_gte(qua0, x1, y1, x0, y0):
        hide_qua = range(0, qua0) + range(qua1+1, 4)
    else:
        hide_qua = range(qua1+1,qua0)
    # error increment
    dx = 16 * (1-2*rx) * ry * ry    
    dy = 16 * rx * rx 
    ddy = 32 * rx * rx
    ddx = 32 * ry * ry
    # error for first step
    err = dx + dy   
    backend.apply_graph_clip()        
    x, y = rx, 0
    while True: 
        for quadrant in range(0,4):
            # skip invisible arc sectors
            if quadrant in hide_qua:
                continue
            elif qua0 != qua1 and (quadrant == qua0 and quadrant_gte(qua0, x0, y0, x, y)):
                continue
            elif qua0 != qua1 and (quadrant == qua1 and quadrant_gte(qua1, x, y, x1, y1)):
                continue
            elif qua0 == qua1 and quadrant == qua0:
                if quadrant_gte(qua0, x1,y1, x0,y0):
                    if quadrant_gte(qua0, x, y, x1, y1) or quadrant_gte(qua0, x0, y0, x, y):
                        continue
                else:
                    if quadrant_gte(qua0, x, y, x1, y1) and quadrant_gte(qua0, x0, y0, x, y):
                        continue
            backend.put_pixel(*quadrant_coord(quadrant, cx,cy,x,y), index=c) 
        # bresenham error step
        e2 = 2 * err
        if (e2 <= dy):
            y += 1
            dy += ddy
            err += dy
        if (e2 >= dx or e2 > dy):
            x -= 1
            dx += ddx
            err += dx
        # NOTE - err changes sign at the change from y increase to x increase
        if (x < 0):
            break
    # too early stop of flat vertical ellipses
    # finish tip of ellipse
    while (y < ry): 
        backend.put_pixel(cx, cy+y, c) 
        backend.put_pixel(cx, cy-y, c) 
        y += 1 
    if line0:
        draw_line(cx,cy, *quadrant_coord(qua0, cx, cy, x0, y0), c=c)
    if line1:
        draw_line(cx,cy, *quadrant_coord(qua1, cx, cy, x1, y1), c=c)
    backend.remove_graph_clip()     
    
def quadrant_coord(quadrant, x0,y0, x,y):    
    if   quadrant == 3:     return x0+x, y0+y
    elif quadrant == 0:     return x0+x, y0-y
    elif quadrant == 2:     return x0-x, y0+y
    elif quadrant == 1:     return x0-x, y0-y
    
def quadrant_gte(quadrant, x,y, x0,y0):
    if quadrant%2 == 0:
        if y!=y0: return y>y0
        else: return x<=x0
    else:
        if y!=y0: return y<y0 
        else: return x>=x0 
        
        
#####        
# 4-way scanline flood fill
# http://en.wikipedia.org/wiki/Flood_fill


def check_scanline (line_seed, x_start, x_stop, y, c, border, ydir):
    if x_stop < x_start:
        return line_seed
    x_start_next = x_start
    x_stop_next = x_start_next-1
    for x in range(x_start, x_stop+1):
        # here we check for border *as well as* fill colour, to avoid infinite loops over bits already painted (eg. 00 shape)
        if backend.get_pixel(x,y) not in (border,c):
            x_stop_next = x
        else:
            if x_stop_next >= x_start_next:
                line_seed.append([x_start_next, x_stop_next, y, ydir])
            x_start_next = x + 1
    if x_stop_next >= x_start_next:
        line_seed.append([x_start_next, x_stop_next, y, ydir])
    return line_seed    

def fill_scanline(x_start, x_stop, y, pattern):
    mask = 7 - x_start%8
    for x in range(x_start, x_stop+1):
        c = 0
        for b in range(state.console_state.bitsperpixel-1,-1,-1):
            c <<= 1
            c += (pattern[b] & (1<<mask)) >> mask
        mask -= 1
        if mask < 0:
            mask = 7
        backend.put_pixel(x,y,c)
      
# flood fill stops on border colour in all directions; it also stops on scanlines in fill_colour
def flood_fill (x, y, pattern, c, border): 
    c, border = get_colour_index(c), get_colour_index(border)
    if get_point(x, y) == border:
        return
    bound_x0, bound_y0, bound_x1, bound_y1 = backend.get_graph_clip()  
    x, y = view_coords(x, y)
    line_seed = [(x, x, y, 0)]
    while len(line_seed) > 0:
        x_start, x_stop, y, ydir = line_seed.pop()
        # check left extension
        x_left = x_start
        while x_left-1 >= bound_x0 and backend.get_pixel(x_left-1,y) != border:
            x_left -= 1
        # check right extension
        x_right = x_stop
        while x_right+1 <= bound_x1 and backend.get_pixel(x_right+1,y) != border:
            x_right += 1
        if ydir == 0:
            if y + 1 <= bound_y1:
                line_seed = check_scanline(line_seed, x_left, x_right, y+1, c, border, 1)
            if y - 1 >= bound_y0:
                line_seed = check_scanline(line_seed, x_left, x_right, y-1, c, border, -1)
        else:
            # check in proper direction
            if y+ydir <= bound_y1 and y+ydir >= bound_y0:
                line_seed = check_scanline(line_seed, x_left, x_right, y+ydir, c, border, ydir)
            # check extensions in counter direction
            if y-ydir <= bound_y1 and y-ydir >= bound_y0:
                line_seed = check_scanline(line_seed, x_left, x_start-1, y-ydir, c, border, -ydir)
                line_seed = check_scanline(line_seed, x_stop+1, x_right, y-ydir, c, border, -ydir)
        # draw the pixels    
        fill_scanline(x_left, x_right, y, pattern)
        # show progress
        console.check_events()

### PUT and GET

def operation_set(pix0, pix1):
    return pix1

def operation_not(pix0, pix1):
#    return ~pix1
    return pix1 ^ ((1<<state.console_state.bitsperpixel)-1)

def operation_and(pix0, pix1):
    return pix0 & pix1

def operation_or(pix0, pix1):
    return pix0 | pix1

def operation_xor(pix0, pix1):
    return pix0 ^ pix1

operations = {
    '\xC6': operation_set, #PSET
    '\xC7': operation_not, #PRESET
    '\xEE': operation_and,
    '\xEF': operation_or,
    '\xF0': operation_xor,
    }
     
   
def set_area(x0,y0, array, operation_char):
    if backend.fast_put(x0, y0, array, operation_char):
        return
    byte_array, version = var.get_bytearray(array)
    dx = vartypes.uint_to_value(byte_array[0:2])
    dy = vartypes.uint_to_value(byte_array[2:4])
    # in mode 1, number of x bits is given rather than pixels
    if state.console_state.screen_mode == 1:
        dx /= 2
    x1, y1 = x0+dx-1, y0+dy-1
    x0, y0 = view_coords(x0, y0)
    x1, y1 = view_coords(x1, y1)
    # illegal fn call if outside screen boundary
    util.range_check(0, state.console_state.size[0]-1, x0, x1)
    util.range_check(0, state.console_state.size[1]-1, y0, y1)
    operation = operations[operation_char]
    backend.apply_graph_clip()
    byte = 4
    if state.console_state.screen_mode == 1:
        shift = 6
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                if shift < 0:
                    byte += 1
                    shift = 6
                if x < 0 or x >= state.console_state.size[0] or y < 0 or y >= state.console_state.size[1]:
                    pixel = 0
                else:
                    pixel = backend.get_pixel(x,y)
                    try:    
                        index = (byte_array[byte] >> shift) & 3   
                    except IndexError:
                        pass                
                    backend.put_pixel(x, y, operation(pixel, index))    
                shift -= 2
            # byte align next row
            byte += 1
            shift = 6   
    else:                
        mask = 0x80
        row_bytes = (dx+7) // 8
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                if mask == 0: 
                    mask = 0x80
                if x < 0 or x >= state.console_state.size[0] or y < 0 or y >= state.console_state.size[1]:
                    pixel = 0
                else:
                    pixel = backend.get_pixel(x,y)
                index = 0
                for b in range(state.console_state.bitsperpixel):
                    try:
                        if byte_array[4 + ((y-y0)*state.console_state.bitsperpixel + b)*row_bytes + (x-x0)//8] & mask != 0:
                            index |= 1 << b  
                    except IndexError:
                        pass
                mask >>= 1
                if x >= 0 and x < state.console_state.size[0] and y >= 0 and y < state.console_state.size[1]:
                    backend.put_pixel(x, y, operation(pixel, index)) 
            # byte align next row
            mask = 0x80
    backend.remove_graph_clip()        
        
def get_area(x0,y0,x1,y1, array):
    dx = (x1-x0+1)
    dy = (y1-y0+1)
    x0, y0 = view_coords(x0,y0)
    x1, y1 = view_coords(x1,y1)
    # illegal fn call if outside screen boundary
    util.range_check(0, state.console_state.size[0]-1, x0, x1)
    util.range_check(0, state.console_state.size[1]-1, y0, y1)
    byte_array, version = var.get_bytearray(array)
    # clear existing array
    byte_array[:] = '\x00'*len(byte_array)
    if state.console_state.screen_mode==1:
        byte_array[0:4] = vartypes.value_to_uint(dx*2) + vartypes.value_to_uint(dy)
    else:
        byte_array[0:4] = vartypes.value_to_uint(dx) + vartypes.value_to_uint(dy) 
    byte = 4
    if state.console_state.screen_mode == 1:
        shift = 6
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                if shift < 0:
                    byte += 1
                    shift = 6
                pixel = backend.get_pixel(x,y) # 2-bit value
                try:
                    byte_array[byte] |= pixel << shift
                except IndexError:
                    raise error.RunError(5)      
                shift -= 2
            # byte align next row
            byte += 1
            shift = 6   
    else:    
        mask = 0x80
        row_bytes = (dx+7) // 8
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                if mask == 0: 
                    mask = 0x80
                pixel = backend.get_pixel(x, y)
                for b in range(state.console_state.bitsperpixel):
                    if pixel & (1<<b) != 0:
                        try:
                            byte_array[4 + ((y-y0)*state.console_state.bitsperpixel + b)*row_bytes + (x-x0)//8] |= mask 
                        except IndexError:
                            raise error.RunError(5)   
                mask >>= 1
            # byte align next row
            mask = 0x80
    # store a copy in the fast-put store
    backend.fast_get(x0, y0, x1, y1, array)
    
## VIEW    
    
def set_graph_view(x0,y0,x1,y1, absolute=True):
    # VIEW orders the coordinates
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    state.console_state.view_graph_absolute = absolute
    state.console_state.graph_view_set = True
    backend.set_graph_clip(x0, y0, x1, y1)
    if state.console_state.view_graph_absolute:
        state.console_state.last_point = x0 + (x1-x0)/2, y0 + (y1-y0)/2
    else:
        state.console_state.last_point = (x1-x0)/2, (y1-y0)/2
    if state.console_state.graph_window_bounds != None:
        set_graph_window(*state.console_state.graph_window_bounds)

def unset_graph_view():
    state.console_state.view_graph_absolute = False
    state.console_state.graph_view_set = False
    state.console_state.last_point = backend.unset_graph_clip()
    if state.console_state.graph_window_bounds != None:
        set_graph_window(*state.console_state.graph_window_bounds)

def view_coords(x,y):
    if (not state.console_state.graph_view_set) or state.console_state.view_graph_absolute:
        return x, y
    else:
        lefttop = backend.get_graph_clip()
        return x + lefttop[0], y + lefttop[1]

def clear_graphics_view():
    backend.clear_graph_clip((state.console_state.attr>>4) & 0x7)

###############################################################

# memory model

colour_plane = 3
colour_plane_write_mask = 0xff
video_segment = { 0: 0xb800, 1: 0xb800, 2: 0xb800, 7: 0xa000, 8: 0xa000, 9: 0xa000 }

def get_pixel_byte(page, x, y, plane):
    if y < state.console_state.size[1] and page < state.console_state.num_pages:
        return sum(( ((backend.get_pixel(x+shift, y, page) >> plane) & 1) << (7-shift) for shift in range(8) ))
    return -1    
    
def set_pixel_byte(page, x, y, plane_mask, byte):
    if y < state.console_state.size[1] and page < state.console_state.num_pages:
        for shift in range(8):
            bit = (byte>>(7-shift)) & 1
            backend.put_pixel(x + shift, y, bit * plane_mask, page)  
    
def get_memory(addr):
    if addr < video_segment[state.console_state.screen_mode]*0x10:
        return -1
    else:
        if state.console_state.screen_mode == 0:
            return console.get_memory(addr)
        addr -= video_segment[state.console_state.screen_mode]*0x10
        if state.console_state.screen_mode == 1:
            # interlaced scan lines of 80bytes, 4pixels per byte
            x, y = ((addr%0x2000)%80)*4, (addr>=0x2000) + 2*((addr%0x2000)//80)
            if y < state.console_state.size[1]:
                return ( (backend.get_pixel(x  , y)<<6) + (backend.get_pixel(x+1, y)<<4) 
                        + (backend.get_pixel(x+2, y)<<2) + (backend.get_pixel(x+3, y)))
        elif state.console_state.screen_mode == 2:
            # interlaced scan lines of 80bytes, 8 pixes per byte
            x, y = ((addr%0x2000)%80)*8, (addr>=0x2000) + 2*((addr%0x2000)//80)
            return get_pixel_byte(0, x, y, 0)
        elif state.console_state.screen_mode == 7:
            page, addr = addr//8192, addr%8192
            x, y = (addr%40)*8, addr//40
            return get_pixel_byte(page, x, y, colour_plane % 4)
        elif state.console_state.screen_mode == 8:
            page, addr = addr//16384, addr%16384
            x, y = (addr%80)*8, addr//80
            return get_pixel_byte(page, x, y, colour_plane % 4)
        elif state.console_state.screen_mode == 9:
            page, addr = addr//32768, addr%32768
            x, y = (addr%80)*8, addr//80
            return get_pixel_byte(page, x, y, colour_plane % 4)
        return -1   

def set_memory(addr, val):
    if addr >= video_segment[state.console_state.screen_mode]*0x10:
        if state.console_state.screen_mode == 0:
            return console.set_memory(addr, val)
        addr -= video_segment[state.console_state.screen_mode]*0x10
        if state.console_state.screen_mode == 1:
            # interlaced scan lines of 80bytes, 4pixels per byte
            x, y = ((addr%0x2000)%80)*4, (addr>=0x2000) + 2*((addr%0x2000)//80)
            if y < state.console_state.size[1]:
                for shift in range(4):
                    twobit = (val>>(6-shift*2)) & 3
                    backend.put_pixel(x + shift, y, twobit) 
        elif state.console_state.screen_mode == 2:
            # interlaced scan lines of 80bytes, 8 pixes per byte
            x, y = ((addr%0x2000)%80)*8, (addr>=0x2000) + 2*((addr%0x2000)//80)
            set_pixel_byte(0, x, y, 1, val)
        elif state.console_state.screen_mode == 7:
            page, addr = addr//8192, addr%8192
            x, y = (addr%40)*8, addr//40
            set_pixel_byte(page, x, y, colour_plane_write_mask & 0xf, val)
        elif state.console_state.screen_mode == 8:
            page, addr = addr//16384, addr%16384
            x, y = (addr%80)*8, addr//80
            set_pixel_byte(page, x, y, colour_plane_write_mask & 0xf, val)
        elif state.console_state.screen_mode == 9:
            page, addr = addr//32768, addr%32768
            x, y = (addr%80)*8, addr//80
            set_pixel_byte(page, x, y, colour_plane_write_mask & 0xf, val)            

def get_memory_block(addr, length):
    return bytearray( [ max(0, get_memory(a)) for a in range(addr, addr+length) ] )
    
def set_memory_block(addr, bytes):
    for a in range(len(bytes)):
        set_memory(addr + a, bytes[a])
    
    

