#
# PC-BASIC 3.23 - draw_and_play.py
#
# DRAW and PLAY macro languages
# 
# (c) 2013 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#
import StringIO

import glob
import fp
import vartypes
import tokenise
import util
import var
import graphics


# generic for both macro languages

def ml_parse_value(gmls):
    c = util.skip(gmls, gml_whitespace)
    
    if c=='=':
        gmls.read(1)    
        step = var.getvar(var.get_var_name(gmls))
        util.require_read(gmls,';', err=5)
    else:
        sgn=1
        if c=='+':
            gmls.read(1)
            c = util.peek(gmls)
        elif c=='-':
            gmls.read(1)
            c = util.peek(gmls)
            sgn=-1   
        
        if c in tokenise.ascii_digits:     
            numstr=''
            while c in tokenise.ascii_digits:
                gmls.read(1)
                numstr+=c 
                c = util.skip(gmls, gml_whitespace) 
            step = tokenise.str_to_value_keep(('$', numstr))
            if sgn==-1:
                step = vartypes.vneg(step)
        else:
            raise error.RunError(5)
    return step



def ml_parse_number(gmls):
    return vartypes.pass_int_keep(ml_parse_value(gmls), err=5)[1]
    

def ml_parse_string(gmls):
    util.skip(gmls, gml_whitespace)
    sub = var.getvar(var.get_var_name(gmls))
    util.require_read(gmls,';', err=5)
    return vartypes.pass_string_keep(sub, err=5)[1]




    
# GRAPHICS MACRO LANGUAGE
    
gml_whitespace = (' ')
deg_to_rad = fp.div( fp.mbf_twopi, fp.from_int(fp.MBF_class, 360))

draw_scale=4
draw_angle=0
    
    

def draw_step(x0,y0, sx,sy, plot, goback):
    global draw_scale, draw_angle
    scale = draw_scale
    rotate = draw_angle
    
    x1 = (scale*sx)/4  
    y1 = (scale*sy)/4
    
    if rotate==0:
        pass
    elif rotate==90:
        x1,y1 = y1,-x1
    elif rotate==180:
        x1,y1 = -x1,-y1
    elif rotate==270:
        x1,y1 = -y1,x1
    else:
        fx,fy = fp.from_int(fp.MBF_class, x1), fp.from_int(fp.MBF_class, y1)
        phi = fp.mul(fp.from_int(fp.MBF_class, rotate), deg_to_rad)
        sinr, cosr = fp.mbf_sin(phi), fp.mbf_cos(phi)
        fx,fy = fp.add(fp.mul(cosr,fx), fp.mul(sinr,fy)), fp.sub(fp.mul(cosr,fy), fp.mul(sinr,fx)) 
        x1,y1 = fp.round_to_int(fx), fp.round_to_int(fy)
        
    y1 += y0
    x1 += x0
    
    if plot:
        graphics.draw_line(x0,y0,x1,y1,-1)    
    else:
        graphics.last_point=(x1,y1)
        
    if goback:
        graphics.last_point=(x0,y0)
        
    
            

def draw_parse_gml(gml):
    global draw_scale, draw_angle
    
    gmls = StringIO.StringIO(gml)
    plot=True
    goback=False
    
    while True:
        c = util.skip_read(gmls, gml_whitespace).upper()
        
        if c=='':
            break
        elif c==';':
            continue
        elif c=='B':
            # do not draw
            plot=False
        elif c=='N':
            # return to postiton after move
            goback=True            
        elif c=='X':
            # execute substring
            sub = ml_parse_string(gmls)
            draw_parse_gml(sub)            
            
        elif c=='C':
            # set foreground colour
            colour = ml_parse_number(gmls)
            glob.scrn.set_attr(colour,0)
        elif c=='S':
            # set scale
            draw_scale = ml_parse_number(gmls)
        elif c=='A':
            # set angle
            draw_angle = 90*ml_parse_number(gmls)   
        elif c=='T':
            # 'turn angle' - set (don't turn) the angle to any value
            if gmls.read(1).upper() != 'A':
                raise error.RunError(5)
            draw_angle = ml_parse_number(gmls)
                
        # one-variable movement commands:     
        elif c in ('U', 'D', 'L', 'R', 'E', 'F', 'G', 'H'):
            step = ml_parse_number(gmls)
            x0,y0 = graphics.last_point
            #x1,y1=x0,y0
            x1,y1 = 0,0
            if c in ('U', 'E', 'H'):
                y1 -= step
            elif c in ('D', 'F', 'G'):
                y1 += step
            if c in ('L', 'G', 'H'):
                x1 -= step
            elif c in ('R', 'E', 'F'):
                x1 += step
            
            draw_step(x0,y0,x1,y1, plot, goback)
            plot = True
            goback = False
                
        # two-variable movement command
        elif c =='M':
            relative =  util.skip(gmls,gml_whitespace) in ('+','-')
            x = ml_parse_number(gmls)
            
            if util.skip(gmls, gml_whitespace) !=',':
                raise error.RunError(5)
            else:
                gmls.read(1)
            
            y = ml_parse_number(gmls)
            
            
            x0,y0 = graphics.last_point
            if relative:
                draw_step(x0,y0,x,y,  plot, goback)
                
            else:
                if plot:
                    graphics.draw_line(x0,y0,x,y,-1)    
                else:
                    graphics.last_point=(x,y)
                if goback:
                    graphics.last_point=(x0,y0)
            
            plot = True
            goback = False
            
            
        elif c =='P':
            # paint - flood fill
            
            x0,y0 = graphics.last_point
            
            colour = ml_parse_number(gmls)
            if util.skip(gmls, gml_whitespace) !=',':
                raise error.RunError(5)
            bound = ml_parse_number(gmls)
            
            graphics.flood_fill(x0,y0,solid_pattern(colour), colour, bound)    
        

# MUSIC MACRO LANGUAGE


# 12-tone equal temperament
# C, C#, D, D#, E, F, F#, G, G#, A, A#, B
note_freq = [ 440.*2**((i-33.)/12.) for i in range(84) ]
play_octave=4
play_speed=7./8.
play_tempo= 2. # 2*0.25 =0.5 seconds per quarter note
play_length=0.25

notes = { 'C':0, 'C#':1, 'D-':1, 'D':2, 'D#':3, 'E-':3, 'E':4, 'F':5, 'F#':6, 'G-':6, 'G':7, 'G#':8, 'A-':8, 'A':9, 'A#':10, 'B-':10, 'B':11 }

music_foreground=True

def play_parse_mml(mml):
    global play_octave, play_speed, play_length, play_tempo, music_foreground
    gmls = StringIO.StringIO(mml)
    next_oct=0
    while True:
        c = util.skip_read(gmls, gml_whitespace).upper()
        
        if c=='':
            break
        elif c==';':
            continue
        elif c=='X':
            # execute substring
            sub = ml_parse_string(gmls)
            play_parse_mml(sub)
            
        elif c=='N':
            note = ml_parse_number(gmls)
            if note>0 and note<=84:
                glob.sound.play_sound(note_freq[note-1], play_length*play_speed*play_tempo)
        
            if note==0:
                glob.sound.play_pause(play_length*play_speed*play_tempo)

        elif c=='L':
            play_length = 1./ml_parse_number(gmls)    
        elif c=='T':
            play_tempo = 240./ml_parse_number(gmls)    
        
        
        elif c=='O':
            play_octave = ml_parse_number(gmls)
            if play_octave<0:
                play_octave=0
            if play_octave>6:
                play_octave=6        
        elif c=='>':
            play_octave += 1
            if play_octave>6:
                play_octave=6
        elif c=='<':
            play_octave -=1
            if play_octave<0:
                play_octave=0
                        
        elif c in ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'P'):
            note=c
            dur=play_length
            while True:    
                c = util.skip(gmls, gml_whitespace).upper()
                if c=='.':
                    gmls.read(1)
                    dur *= 1.5
                elif c in tokenise.ascii_digits:
                    numstr=''
                    
                    while c in tokenise.ascii_digits:
                        gmls.read(1)
                        numstr+=c 
                        c = util.skip(gmls, gml_whitespace) 
                    length = vartypes.pass_int_keep(tokenise.str_to_value_keep(('$', numstr)))[1]
                    dur = 2./float(length)
                elif c in ('#', '+'):
                    gmls.read(1)
                    note+='#'
                elif c == '-':
                    gmls.read(1)
                    note+='-'
                else:
                    break                    
            if note=='P':
                glob.sound.play_pause(dur*play_speed*play_tempo)
            
            else:        
                glob.sound.play_sound(note_freq[(play_octave+next_oct)*12+notes[note]], dur*play_speed*play_tempo)
            next_oct=0
        
        elif c=='M':
            c = util.skip_read(gmls, gml_whitespace).upper()
            if c=='N':
                play_speed=7./8.
            elif c=='L':
                play_speed==1.
            elif c=='S':
                play_speed=3./4.        
            elif c=='F':
                # foreground
                music_foreground=True
            elif c=='B':
                # background
                music_foreground=False
                            
            
            else:
                raise error.RunError(5)    
        else:
            raise error.RunError(5)    
    
    if music_foreground:
        glob.sound.wait_music()
                                 
