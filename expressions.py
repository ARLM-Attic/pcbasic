#
# PC-BASIC 3.23 - expressions.py
#
# Expression parser 
# 
# (c) 2013 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import datetime
import os
from cStringIO import StringIO
from functools import partial

import fp
import vartypes
import rnd
import tokenise
import oslayer
import util
import error
import var
import fileio
import deviceio
import graphics
import console
# for FRE() only
import program

# binary operator priority, lowest index is tightest bound 
# operators of the same priority are evaluated left to right      
priority = [
    ['\xED'], # ^  
    ['\xEB', '\xEC'], # *, /
    ['\xF4'], # \
    ['\xF3'], # MOD
    ['\xE9', '\xEA'], # +, -
    ['\xE6', '\xE7', '\xE8', '\xE6\xE7', '\xE8\xE7', '\xE8\xE6' ], # >, =, <, >=, <=, <>  
    ['\xEE'], # AND
    ['\xEF'], # OR
    ['\xF0'], # XOR
    ['\xF1'], # EQV
    ['\xF2'] # IMP
]

# flatten list
operator_tokens = [item for sublist in priority for item in sublist]
# command line option /d
# allow double precision math for ^, ATN, COS, EXP, LOG, SIN, SQR, and TAN
option_double = False
# pre-defined PEEK outputs
peek_values = {}


def parse_expression(ins, allow_empty=False, empty_err=22):
    units = []
    operators = []
    d = util.skip_white(ins)
    while d not in util.end_expression: 
        units.append(parse_expr_unit(ins))
        d = util.skip_white(ins)
        # string lit breaks expression, number after string lit breaks expression, + or - doesnt (could be an operator...
        if d not in operator_tokens:
            break
        else:
            ins.read(1)
        if d in ('\xE6', '\xE7', '\xE8'):
            nxt = util.skip_white(ins)
            if nxt in ('\xE6', '\xE7', '\xE8'):
                ins.read(1)
                if d == nxt:
                    raise error.RunError(2)
                else:    
                    d += nxt
                    if d[0] == '\xe7': #= 
                        # =>, =<
                        d = d[1]+d[0]
                    elif d == '\xe6\xe8': # ><
                        d = '\xe8\xe6'    
        operators.append(d)
    # empty expression is a syntax error (inside brackets) or Missing Operand (in an assignment) or ok (in print)
    if len(units) == 0:
        if allow_empty:
            return None
        else:    
            raise error.RunError(empty_err)
    if len(units) <= len(operators):
        # missing operand
        raise error.RunError(22)
    return parse_operators(operators, units)

def parse_operators(operators, units):
    for current_priority in priority:
        pos = 0
        while pos < len(operators):
            if operators[pos] in current_priority:
                units[pos] = value_operator(operators[pos], units[pos], units[pos+1])
                del units[pos+1]
                del operators[pos]
            else:
                pos += 1
        if len(operators) == 0:
            break
    if len(operators) > 0:
        # unrecognised operator, syntax error
        raise error.RunError(2)
    return units[0]    
    
def parse_expr_unit(ins):
    d = util.skip_white_read(ins)
    # string literal
    if d == '"':
        output = bytearray()
        # while tokenised nmbers inside a string lieral will be printed as tokenised numbers, they don't actually execute as such:
        # a \00 character, even if inside a tokenised number, will break a string literal (and make the parser expect a 
        # line number afterwards, etc. We follow this.
        d = ins.read(1)
        while d not in util.end_line + ('"',)  : # ['"', '\x00', '']:
            output += d
            d = ins.read(1)        
        if d == '\x00':
            ins.seek(-1,1)
        return ('$', output)
    # variable name
    elif d >= 'A' and d <= 'Z':
        ins.seek(-1, 1)
        name, indices = get_var_or_array_name(ins)
        return var.get_var_or_array(name, indices)
    # number literals as ASCII are accepted in tokenised streams. only if they start with a figure (not & or .)
    # this happens e.g. after non-keywords like AS. They are not acceptable as line numbers.
    elif d >= '0' and d <= '9':
        ins.seek(-1, 1)
        outs = StringIO()
        tokenise.tokenise_number(ins, outs)
        outs.seek(0)
        return util.parse_value(outs)
    # number literals
    elif d in tokenise.tokens_number:
        ins.seek(-1, 1)
        return util.parse_value(ins)   
    # gw-basic allows adding line numbers to numbers     
    elif d in tokenise.tokens_linenum:
        ins.seek(-1, 1)
        return vartypes.pack_int(util.parse_jumpnum(ins))
    # brackets
    elif d == '(':
        val = parse_expression(ins, empty_err=2)
        util.require_read(ins, (')',))
        return val    
    # single-byte tokens        
    elif d == '\x85':       # INPUT
        return value_input(ins)
    elif d == '\xC8':       # SCREEN
        return value_screen(ins)
    elif d == '\xD0':       # USR
        return value_usr(ins)
    elif d == '\xD1':       # FN
        return value_fn(ins)
    elif d == '\xD3':       # NOT
        return value_not(ins)
    elif d == '\xD4':       # ERL
        return value_erl(ins)
    elif d == '\xD5':       # ERR
        return value_err(ins)
    elif d == '\xD6':       # STRING$
        return value_string(ins)
    elif d == '\xD8':       # INSTR
        return value_instr(ins)    
    elif d == '\xDA':       # VARPTR
        return value_varptr(ins)
    elif d == '\xDB':       # CSRLIN
        return value_csrlin(ins)
    elif d == '\xDC':       # POINT
        return value_point(ins)
    elif d == '\xDE':       # INKEY$
        return value_inkey(ins)
    elif d == '\xE9':       # unary +
        return parse_expr_unit(ins)
    elif d == '\xEA':       # unary -
        return value_neg(ins)     
    # two-byte tokens
    elif d == '\xFD':
        d = ins.read(1)
        if d== '\x81':      # CVI
            return value_cvi(ins)
        elif d=='\x82':     # CVS
            return value_cvs(ins)
        elif d=='\x83':     # CVD
            return value_cvd(ins)
        elif d=='\x84':     # MKI$
            return value_mki(ins)
        elif d=='\x85':     # MKS$
            return value_mks(ins)
        elif d=='\x86':     # MKD$
            return value_mkd(ins)
        elif d== '\x8b':    # EXTERR
            return value_exterr(ins)
    # two-byte tokens
    elif d == '\xFE':
        d = ins.read(1)        
        if d== '\x8D':      # DATE$
            return value_date(ins)
        elif d== '\x8E':    # TIME$
            return value_time(ins)
        elif d== '\x94':    # TIMER
            return value_timer(ins)
        elif d== '\x95':    # ERDEV
            return value_erdev(ins)
        elif d== '\x96':    # IOCTL
            return value_ioctl(ins)
        elif d== '\x9B':    # ENVIRON$
            return value_environ(ins)
        elif d== '\x9E':    # PMAP
            return value_pmap(ins)
    # two-byte tokens                    
    elif d == '\xFF':
        d = ins.read(1)
        if d == '\x81':     # LEFT$
            return value_left(ins)
        elif d == '\x82':   # RIGHT$
            return value_right(ins)
        elif d == '\x83':   # MID$
            return value_mid(ins)
        elif d == '\x84':   # SGN
            return value_sgn(ins)
        elif d == '\x85':   # INT
            return value_int(ins)
        elif d == '\x86':   # ABS
            return value_abs(ins)
        elif d == '\x87':   # SQR
            return value_sqrt(ins)
        elif d == '\x88':   # RND
            return value_rnd(ins)
        elif d == '\x89':   # SIN
            return value_sin(ins)
        elif d == '\x8a':   # LOG
            return value_log(ins)
        elif d == '\x8b':   # EXP
            return value_exp(ins)
        elif d == '\x8c':   # COS
            return value_cos(ins)
        elif d == '\x8D':   # TAN
            return value_tan(ins)
        elif d == '\x8E':   # ATN
            return value_atn(ins)
        elif d == '\x8F':   # FRE
            return value_fre(ins)
        elif d == '\x90':   # INP
            return value_inp(ins)
        elif d == '\x91':   # POS
            return value_pos(ins)
        elif d == '\x92':   # LEN
            return value_len(ins)
        elif d == '\x93':   # STR$
            return value_str(ins)
        elif d == '\x94':   # VAL
            return value_val(ins)
        elif d == '\x95':   # ASC
            return value_asc(ins)
        elif d == '\x96':   # CHR$
            return value_chr(ins)
        elif d == '\x97':   # PEEK
            return value_peek(ins)
        elif d == '\x98':   # SPACE$
            return value_space(ins)
        elif d == '\x99':   # OCT$
            return value_oct(ins)
        elif d == '\x9A':   # HEX$
            return value_hex(ins)
        elif d == '\x9B':   # LPOS
            return value_lpos(ins)
        elif d == '\x9C':   # CINT
            return value_cint(ins)
        elif d == '\x9D':   # CSNG
            return value_csng(ins)
        elif d == '\x9E':   # CDBL
            return value_cdbl(ins)
        elif d == '\x9F':   # FIX
            return value_fix(ins)    
        elif d == '\xA0':   # PEN
            return value_pen(ins)
        elif d == '\xA1':   # STICK
            return value_stick(ins)
        elif d == '\xA2':   # STRIG
            return value_strig(ins)
        elif d == '\xA3':   # EOF
            return value_eof(ins)
        elif d == '\xA4':   # LOC
            return value_loc(ins)
        elif d == '\xA5':   # LOF
            return value_lof(ins)
    return None

######################################################################
# expression parsing utility functions 

def parse_bracket(ins):
    util.require_read(ins, ('(',))
    # we need a Syntax error, not a Missing operand
    val = parse_expression(ins, empty_err=2)
    util.require_read(ins, (')',))
    return val

def parse_int_list(ins, size, err=5, allow_last_empty=False):
    exprlist = parse_expr_list(ins, size, err, allow_last_empty=allow_last_empty)
    output = []
    for expr in exprlist:
        if expr == None:
            output.append(None)
        else:
            output.append(vartypes.pass_int_unpack(expr))
    return output

def parse_expr_list(ins, size, err=5, separators=(',',), allow_last_empty=False):
    pos = 0
    output = [None] * size
    while True:
        d = util.skip_white(ins)
        if d in separators: 
            ins.read(1)
            pos += 1
            if pos >= size:
                # 5 = illegal function call
                raise error.RunError(err)
        elif d in util.end_expression:
            break
        else:  
            output[pos] = parse_expression(ins)
    # can't end on a comma: Missing Operand  
    if not allow_last_empty and not output[pos]:
        raise error.RunError(22)
    return output

def parse_int_list_var(ins, size, err=5):
    output = [ vartypes.pass_int_unpack(parse_expression(ins, empty_err=2)) ]   
    while True:
        d = util.skip_white(ins)
        if d == ',': 
            ins.read(1)
            c = util.peek(ins)
            if c in util.end_statement:
                # missing operand
                raise error.RunError(22)
            # if end_expression, syntax error    
            output.append(vartypes.pass_int_unpack(parse_expression(ins, empty_err=2)))
        elif d in util.end_statement:
            # statement ends - syntax error
            raise error.RunError(2)        
        elif d in util.end_expression:
            break
        else:  
            raise error.RunError(2)
    return output

def parse_file_number(ins):
    screen = None
    if util.skip_white_read_if(ins,'#'):
        number = vartypes.pass_int_unpack(parse_expression(ins))
        util.range_check(0, 255, number)
        screen = fileio.get_file(number)
        util.require_read(ins, (',',))
    return screen        

def parse_file_number_opthash(ins):
    util.skip_white_read_if(ins, '#')
    number = vartypes.pass_int_unpack(parse_expression(ins))
    util.range_check(0, 255, number)
    return number    

def get_var_or_array_name(ins):
    name = util.get_var_name(ins)
    indices = []
    if util.skip_white_read_if(ins, ('[', '(')):
        # it's an array, read indices
        indices = parse_int_list(ins, 255, 9) # subscript out of range
        while len(indices) > 0 and indices[-1] == None:
            indices = indices[:-1]
        if None in indices:
            raise error.RunError(2)
        util.require_read(ins, (']', ')'))
    return name, indices

######################################################################
# conversion

def value_cvi(ins):            
    cstr =  vartypes.pass_string_unpack(parse_bracket(ins))
    if len(cstr) < 2:
        raise error.RunError(5)
    return vartypes.pack_int(vartypes.sint_to_value(cstr[:2]))

def value_cvs(ins):            
    cstr =  vartypes.pass_string_unpack(parse_bracket(ins))
    if len(cstr) < 4:
        raise error.RunError(5)
    return ('!', cstr[:4]) 

def value_cvd(ins):            
    cstr =  vartypes.pass_string_unpack(parse_bracket(ins))
    if len(cstr) < 8:
        raise error.RunError(5)
    return ('#', cstr[:8])

def value_mki(ins):            
    return vartypes.pack_string(vartypes.value_to_sint(vartypes.pass_int_unpack(parse_bracket(ins))))

def value_mks(ins):            
    return vartypes.pack_string(vartypes.pass_single_keep(parse_bracket(ins))[1])

def value_mkd(ins):       
    return vartypes.pack_string(vartypes.pass_double_keep(parse_bracket(ins))[1])

def value_cint(ins):            
    return vartypes.pass_int_keep(parse_bracket(ins))

def value_csng(ins):            
    return vartypes.pass_single_keep(parse_bracket(ins))

def value_cdbl(ins):            
    return vartypes.pass_double_keep(parse_bracket(ins))

def value_str(ins):            
    s = parse_bracket(ins)
    if s[0] == '$':
        raise error.RunError(13)
    return vartypes.value_to_str_keep(s, screen=True)
        
def value_val(ins):            
    return tokenise.str_to_value_keep(parse_bracket(ins))

def value_chr(ins):            
    val = vartypes.pass_int_unpack(parse_bracket(ins))
    util.range_check(0, 255, val)
    return vartypes.pack_string(bytearray(chr(val)))

def value_oct(ins):            
    # allow range -32768 to 65535
    val = vartypes.pass_int_unpack(parse_bracket(ins), 0xffff)
    return vartypes.pack_string(vartypes.oct_to_str(vartypes.value_to_sint(val))[2:])

def value_hex(ins):            
    # allow range -32768 to 65535
    val = vartypes.pass_int_unpack(parse_bracket(ins), 0xffff)
    return vartypes.pack_string(vartypes.hex_to_str(vartypes.value_to_sint(val))[2:])

######################################################################
# string maniulation            
    
def value_len(ins):            
    return vartypes.pack_int(len(vartypes.pass_string_unpack(parse_bracket(ins))) )

def value_asc(ins):            
    s = vartypes.pass_string_unpack(parse_bracket(ins))
    if s:
        return vartypes.pack_int(s[0])
    else:
        raise error.RunError(5)

def value_instr(ins):
    util.require_read(ins, ('(',))
    big = ''
    small = ''
    have_big = False
    n = 1
    s = parse_expression(ins, empty_err=2)
    if s[0] != '$':
        n = vartypes.pass_int_unpack(s)
        util.range_check(1, 255, n)
    else:
        big = vartypes.pass_string_unpack(s)
        have_big = True
    util.require_read(ins, (',',))
    if not have_big:
        big = vartypes.pass_string_unpack(parse_expression(ins, allow_empty=True))
        util.require_read(ins, (',',))
    small = vartypes.pass_string_unpack(parse_expression(ins, allow_empty=True))
    util.require_read(ins, (')',))
    if big == '' or n > len(big):
        return vartypes.null['%']
    # BASIC counts string positions from 1
    return vartypes.pack_int(n + big[n-1:].find(small))   

def value_mid(ins):
    util.require_read(ins, ('(',))
    s = vartypes.pass_string_unpack(parse_expression(ins))
    util.require_read(ins, (',',))
    start = vartypes.pass_int_unpack(parse_expression(ins))
    if util.skip_white_read_if(ins, ','):
        num = vartypes.pass_int_unpack(parse_expression(ins))
    else:
        num = len(s)
    util.require_read(ins, (')',))
    util.range_check(1, 255, start)
    util.range_check(0, 255, num)
    if num == 0 or start > len(s):
        return vartypes.null['$']
    start -= 1    
    stop = start + num 
    if stop > len(s):
        stop = len(s)
    return vartypes.pack_string(s[start:stop])  
    
def value_left(ins):
    util.require_read(ins, ('(',))
    s = vartypes.pass_string_unpack(parse_expression(ins))
    util.require_read(ins, (',',))
    stop = vartypes.pass_int_unpack(parse_expression(ins))
    util.require_read(ins, (')',))
    util.range_check(0, 255, stop)
    if stop == 0:
        return vartypes.null['$']
    if stop > len(s):
        stop = len(s)
    return vartypes.pack_string(s[:stop])  
    
def value_right(ins):
    util.require_read(ins, ('(',))
    s = vartypes.pass_string_unpack(parse_expression(ins))
    util.require_read(ins, (',',))
    stop = vartypes.pass_int_unpack(parse_expression(ins))
    util.require_read(ins, (')',))
    util.range_check(0, 255, stop)
    if stop == 0:
        return vartypes.null['$']
    if stop > len(s):
        stop = len(s)
    return vartypes.pack_string(s[-stop:])  

def value_string(ins): # STRING$
    util.require_read(ins, ('(',))
    n, j = parse_expr_list(ins, 2)    
    n = vartypes.pass_int_unpack(n)
    util.range_check(0, 255, n)
    if j[0] == '$':
        j = vartypes.unpack_string(j)[0]
    else:
        j = vartypes.pass_int_unpack(j)        
    util.range_check(0, 255, j)
    util.require_read(ins, (')',))
    return vartypes.pack_string(bytearray(chr(j)*n))

def value_space(ins):            
    num = vartypes.pass_int_unpack(parse_bracket(ins))
    util.range_check(0, 255, num)
    return vartypes.pack_string(bytearray(' '*num))
    
######################################################################
# console functions

def value_screen(ins):
    # SCREEN(x,y,[z])
    util.require_read(ins, ('(',))
    row, col, z = parse_int_list(ins, 3, 5) 
    util.require_read(ins, (')',))
    if row == None or col == None:
        raise error.RunError(5)
    util.range_check(1, console.height, row)
    if console.view_set:
        util.range_check(console.view_start, console.scroll_height, row)
    util.range_check(1, console.width, col)
    (char, attr) = console.read_screen(row, col)
    if z: 
        return vartypes.pack_int(attr)
    else:
        return vartypes.pack_int(ord(char))
    
def value_input(ins):    # INPUT$
    if ins.read(1) != '$':
        raise error.RunError(2)
    util.require_read(ins, ('(',))
    num = vartypes.pass_int_unpack(parse_expression(ins))
    util.range_check(1, 255, num)
    screen = console    
    if util.skip_white_read_if(ins, ','):
        screen = fileio.get_file(parse_file_number_opthash(ins))
    util.require_read(ins, (')',))
    word = bytearray()
    for char in screen.read_chars(num):
        if len(char) > 1 and char[0] == '\x00':
            # replace some scancodes than console can return
            if char[1] in ('\x4b', '\x4d', '\x48', '\x50', '\x47', '\x49', '\x4f', '\x51', '\x53'):
                word += '\x00'
            # ignore all others    
        else:
            word += char                        
    return vartypes.pack_string(bytearray(word))
    
def value_inkey(ins):
    return vartypes.pack_string(bytearray(console.get_char()))

def value_csrlin(ins):
    return vartypes.pack_int(console.row)

def value_pos(ins):            
    # parse the dummy argument, doesnt matter what it is as long as it's a legal expression
    parse_bracket(ins)
    return vartypes.pack_int(console.col)

def value_lpos(ins):            
    num = vartypes.pass_int_unpack(parse_bracket(ins))
    util.range_check(0, 3, num)
    printer = deviceio.lpt1
    if num == 2:
        printer = deviceio.lpt2
    elif num ==3:
        printer = deviceio.lpt3    
    return vartypes.pack_int(printer.col)
           
######################################################################
# file access

def value_loc(ins): # LOC
    util.skip_white(ins)
    num = vartypes.pass_int_unpack(parse_bracket(ins), maxint=0xffff)
    util.range_check(0, 255, num)
    the_file = fileio.get_file(num)
    # refuse for output devices, such as SCRN: (bad file mode). Kybd: and com1: etc should be allowed
    if the_file in deviceio.output_devices:
        # bad file mode
        raise error.RunError(54)
    return vartypes.pack_int(the_file.loc())

def value_eof(ins): # EOF
    util.skip_white(ins)
    num = vartypes.pass_int_unpack(parse_bracket(ins), maxint=0xffff)
    if num == 0:
        return vartypes.null['%']
    util.range_check(0, 255, num)
    the_file = fileio.get_file(num, 'IR')
    return vartypes.bool_to_int_keep(the_file.eof())
  
def value_lof(ins): # LOF
    util.skip_white(ins)
    num = vartypes.pass_int_unpack(parse_bracket(ins), maxint=0xffff)
    util.range_check(0, 255, num)
    the_file = fileio.get_file(num)
    return vartypes.pack_int(the_file.lof() )
    

######################################################################
# os functions
       
def value_environ(ins):
    if ins.read(1) != '$':
        raise error.RunError(2)
    expr = parse_bracket(ins)
    if expr[0] == '$':
        parm = str(vartypes.unpack_string(expr))
        if parm == '':
            raise error.RunError(5)
        val = os.getenv(parm)
        if val == None:
            val = ''
        return vartypes.pack_string(val)
    else:
        expr = vartypes.pass_int_unpack(expr)
        envlist = list(os.environ)
        if expr < 1 or expr > 255:
            raise error.RunError(5)
        if expr > len(envlist):
            return vartypes.null['$']            
        else:
            val = os.getenv(envlist[expr-1])
            return vartypes.pack_string(bytearray(envlist[expr-1] + '=' + val))
        
def value_timer(ins):
    # precision of GWBASIC TIMER is about 1/20 of a second
    return fp.pack(fp.div( fp.Single.from_int(oslayer.timer_milliseconds()/50), fp.Single.from_int(20)))
    
def value_time(ins):
    return vartypes.pack_string((datetime.datetime.today() + oslayer.time_offset).strftime('%H:%M:%S'))
    
def value_date(ins):
    return vartypes.pack_string((datetime.datetime.today() + oslayer.time_offset).strftime('%m-%d-%Y'))

#######################################################
# user-defined functions

def value_fn(ins):
    fnname = util.get_var_name(ins)
    try:
        varnames, fncode = var.functions[fnname]
    except KeyError:
        # undefined user function
        raise error.RunError(18)
    # save existing vars
    varsave = {}
    for name in varnames:
        if name[0] == '$':
            # we're just not doing strings
            raise error.RunError(13)
        if name in var.variables:
            varsave[name] = var.variables[name]
    # read variables
    if util.skip_white_read_if(ins, ('(',)):
        exprs = parse_expr_list(ins, len(varnames), err=2)
        if None in exprs:
            raise error.RunError(2)
        for i in range(len(varnames)):
            var.set_var(varnames[i], exprs[i])
        util.require_read(ins, (')',))
    # execute the code
    fns = StringIO(fncode)
    fns.seek(0)
    value = parse_expression(fns)    
    # restore existing vars
    for name in varnames:
        del var.variables[name]
    for name in varsave:    
        var.variables[name] = varsave[name]
    return value    

###############################################################
# graphics    
    
def value_point(ins):
    util.require_read(ins, ('(',))
    lst = parse_expr_list(ins, 2, err=2)
    util.require_read(ins, (')',))
    if not lst[0]:
        raise error.RunError(2)
    if not lst[1]:
        # single-argument version
        x,y = graphics.get_coord()
        fn = vartypes.pass_int_unpack(lst[0])
        if fn == 0:
            return vartypes.pack_int(x)
        elif fn == 1:
            return vartypes.pack_int(y)
        elif fn == 2:
            fx, fy = graphics.get_window_coords(x,y)
            return fx
        elif fn == 3:
            fx, fy = graphics.get_window_coords(x,y)
            return fy
    else:       
        return vartypes.pack_int(graphics.get_point(vartypes.pass_int_unpack(lst[0]), vartypes.pass_int_unpack(lst[1])))        

def value_pmap(ins):
    util.require_read(ins, ('(',))
    coord = fp.unpack(vartypes.pass_single_keep(parse_expression(ins)))
    util.require_read(ins, (',',))
    mode = vartypes.pass_int_unpack(parse_expression(ins))
    util.require_read(ins, (')',))
    if mode == 0:
        value, dummy = graphics.window_coords(coord,fp.Single.zero)       
        value = vartypes.pack_int(value)        
    elif mode == 1:
        dummy, value = graphics.window_coords(fp.Single.zero,coord)       
        value = vartypes.pack_int(value)        
    elif mode == 2:
        value, dummy = graphics.get_window_coords(coord.round_to_int(), 0)       
        value = fp.pack(value)
    elif mode == 3:
        dummy, value = graphics.get_window_coords(0, coord.round_to_int())       
        value = fp.pack(value)
    else:
        raise error.RunError(5)
    return value
    
#####################################################################
# error functions

def value_erl(ins):
    return fp.pack(fp.Single.from_int(error.get_error()[1]))

def value_err(ins):
    return vartypes.pack_int(error.get_error()[0])
    
#####################################################################
# pen, stick and strig

def value_pen(ins):
    fn = vartypes.pass_int_unpack(parse_bracket(ins))
    if fn == 0:
        return vartypes.bool_to_int_keep(console.pen_has_been_down())
    elif fn == 1:
        x, _ = console.get_last_pen_down_pos()
        return vartypes.pack_int(x)
    elif fn == 2:
        _, y = console.get_last_pen_down_pos()
        return vartypes.pack_int(y)
    elif fn == 3:
        return vartypes.bool_to_int_keep(console.pen_is_down())
    elif fn == 4:
        x, _ = console.get_pen_pos()
        return vartypes.pack_int(x)
    elif fn == 5:
        _, y = console.get_pen_pos()
        return vartypes.pack_int(y)
    elif fn == 6:
        _, row = console.get_last_pen_down_pos_char()
        return vartypes.pack_int(row)
    elif fn == 7:
        col, _ = console.get_last_pen_down_pos_char()
        return vartypes.pack_int(col)
    elif fn == 8:
        _, row = console.get_pen_pos_char()
        return vartypes.pack_int(row)
    elif fn == 9:
        col, _ = console.get_pen_pos_char()
        return vartypes.pack_int(col)
    else:
        raise error.RunError(5)

# coordinated run 1..200 (says http://www.qb64.net/wiki/index.php?title=STICK)
# STICK(0) is required to get values from the other STICK functions. Always read it first!
def value_stick(ins):
    fn = vartypes.pass_int_unpack(parse_bracket(ins))
    if fn == 0:
        x, _ = console.stick_coord(0)
        return vartypes.pack_int(x)
    elif fn == 1:
        _, y = console.stick_coord(0)
        return vartypes.pack_int(y)
    elif fn == 2:
        x, _ = console.stick_coord(1)
        return vartypes.pack_int(x)
    elif fn == 3:
        _, y = console.stick_coord(1)
        return vartypes.pack_int(y)
    else:
        raise error.RunError(5)
    
def value_strig(ins):
    fn = vartypes.pass_int_unpack(parse_bracket(ins))
    # 0,1 -> [0][0] 2,3 -> [0][1]  4,5-> [1][0]  6,7 -> [1][1]
    util.range_check(0, 7, fn)
    joy = fn//4
    trig = (fn//2)%2
    if fn%2 == 0:
        return vartypes.bool_to_int_keep(console.stick_has_been_trig(joy,trig))
    else:
        return vartypes.bool_to_int_keep(console.stick_trig(joy,trig))
    
#########################################################
# memory and machine

def value_fre(ins):
    val = parse_bracket(ins)
    if val[0] == '$':
        # grabge collection if a string-valued argument is specified.
        var.collect_garbage()
    return fp.pack(fp.Single.from_int(var.mem_free() ))

# read memory location 
# currently, var memory and preset values only    
def value_peek(ins):
    # TODO: take into account DEF SEG
    global peek_values
    addr = vartypes.pass_int_unpack(parse_bracket(ins), maxint=0xffff)
    if addr < 0: 
        addr += 0x10000
    if addr in peek_values:
        return vartypes.pack_int(peek_values[addr])
    elif addr >= var.var_mem_start:
        val = var.get_var_memory(addr)
        if val < 0:
            val = 0      
        return vartypes.pack_int(val)
    else:    
        return vartypes.null['%']

# VARPTR, VARPTR$    
def value_varptr(ins):    
    if util.peek(ins) == '$':
        ins.read(1) 
        util.require_read(ins, ('(',))
        name, indices = get_var_or_array_name(ins)
        util.require_read(ins, (')',))
        var_ptr = var.get_var_ptr(name, indices)
        if var_ptr < 0:
            raise error.RunError(5) # ill fn cll
        return vartypes.pack_string(bytearray(chr(var.byte_size[name[-1]])) + vartypes.value_to_uint(var_ptr))
    else:
        # TODO: strings, fields, file control blocks not yet implemented 
        util.require_read(ins, ('(',))
        name, indices = get_var_or_array_name(ins)
        util.require_read(ins, (')',))
        var_ptr = var.get_var_ptr(name, indices)
        if var_ptr < 0:
            raise error.RunError(5) # ill fn cll
        return vartypes.pack_int(var_ptr)
        
def value_usr(ins):
    if util.peek(ins) in ('\x11','\x12','\x13','\x14','\x15','\x16','\x17','\x18','\x19','\x1a'): # digits 0--9
        ins.read(1)
    parse_bracket(ins)
    return vartypes.null['%']
    
def value_inp(ins):
    console.idle()
    console.check_events()
    port = vartypes.pass_int_unpack(parse_bracket(ins), maxint=0xffff)
    if port == 0x60:
        return vartypes.pack_int(console.inp_key) 
    return vartypes.null['%']

#  erdev, erdev$        
def value_erdev(ins):
    if util.peek(ins,1)=='$':
        ins.read(1) 
        return vartypes.null['$']
    else:    
        return vartypes.null['%']
        
# exterr        
def value_exterr(ins):
    x = vartypes.pass_int_unpack(parse_bracket(ins))
    util.range_check(0, 3, x)
    return vartypes.null['%']
    
# ioctl$    
def value_ioctl(ins):
    if ins.read(1) != '$':
        raise error.RunError(2)
    util.require_read(ins, ('(',))
    num = parse_file_number_opthash(ins)
    util.require_read(ins, (')',))
    fileio.get_file(num)
    raise error.RunError(5)   
    
###########################################################
# option_double regulated single & double precision math

def value_unary(ins, fn):
    return fp.pack(fn(fp.unpack(vartypes.pass_float_keep(parse_bracket(ins), option_double))))

value_sqrt = partial(value_unary, fn=fp.sqrt)
value_exp = partial(value_unary, fn=fp.exp)
value_sin = partial(value_unary, fn=fp.sin)
value_cos = partial(value_unary, fn=fp.cos)
value_tan = partial(value_unary, fn=fp.tan)
value_atn = partial(value_unary, fn=fp.atn)
value_log = partial(value_unary, fn=fp.log)
 
# others

def value_rnd(ins):
    if util.skip_white(ins) == '(':
        return rnd.get_random(parse_bracket(ins))
    else:
        return rnd.get_random()

def value_abs(ins):
    inp = parse_bracket(ins)
    if inp[0] in ('%', '!', '#'):
        return vartypes.number_abs(inp)
    else:     
        # type mismatch
        raise error.RunError(13)

def value_int(ins):
    inp = parse_bracket(ins)
    if inp[0] == '%':
        return inp
    elif inp[0] in ('!', '#'):
        return fp.pack(fp.unpack(inp).ifloor()) 
    else:     
        # type mismatch
        raise error.RunError(13)

def value_sgn(ins):
    inp = parse_bracket(ins)
    if inp[0] == '%':
        inp_int = vartypes.unpack_int(inp) 
        if inp_int > 0:
            return vartypes.pack_int(1)
        elif inp_int < 0:
            return vartypes.pack_int(-1)
        else:
            return vartypes.null['%']
    elif inp[0] in ('!', '#'):
        return vartypes.pack_int(fp.unpack(inp).sign() )
    else:     
        # type mismatch
        raise error.RunError(13)

def value_fix(inp):
    inp = parse_bracket(inp)
    if inp[0] == '%':
        return inp
    elif inp[0] == '!':
        # needs to be a float to avoid overflow
        return fp.pack(fp.Single.from_int(fp.unpack(inp).trunc_to_int())) 
    elif inp[0] == '#':
        return fp.pack(fp.Double.from_int(fp.unpack(inp).trunc_to_int())) 
    else:     
        # type mismatch
        raise error.RunError(13)
    
def value_neg(ins):
    inp = parse_expr_unit(ins)
    if inp[0] in ('%', '!', '#'):
        return vartypes.number_neg(inp)    
    else:     
        # type mismatch
        raise error.RunError(13)

def value_not(ins):
    # two's complement not, -x-1
    return vartypes.pack_int(~vartypes.pass_int_unpack(parse_expr_unit(ins)))
    
# binary operators
        
def value_operator(op, left, right):
    if op == '\xED':                # ^
        return vcaret(left, right)
    elif op == '\xEB':              # *
        return vtimes(left, right)
    elif op == '\xEC':              # /
        return vdiv(left, right)
    elif op == '\xF4':              # \
        return vartypes.pack_int(vartypes.pass_int_unpack(left) / vartypes.pass_int_unpack(right))    
    elif op == '\xF3':              # %
        return vartypes.pack_int(vartypes.pass_int_unpack(left) % vartypes.pass_int_unpack(right))    
    elif op == '\xE9':              # +
        return vplus(left, right)
    elif op == '\xEA':              # -
        return vartypes.number_add(left, vartypes.number_neg(right))
    elif op ==  '\xE6':             # >
        return vartypes.bool_to_int_keep(vartypes.gt(left,right)) 
    elif op ==  '\xE7':             # =
        return vartypes.bool_to_int_keep(vartypes.equals(left, right))
    elif op ==  '\xE8':             # <  
        return vartypes.bool_to_int_keep(not(vartypes.gt(left,right) or vartypes.equals(left, right)))
    elif op ==  '\xE6\xE7':         # >=
        return vartypes.bool_to_int_keep(vartypes.gt(left,right) or vartypes.equals(left, right))
    elif op ==  '\xE8\xE7':         # <=
        return vartypes.bool_to_int_keep(not vartypes.gt(left,right))
    elif op ==  '\xE8\xE6':         # <>
        return vartypes.bool_to_int_keep(not vartypes.equals(left, right))
    elif op ==  '\xEE':             # AND
        return vartypes.twoscomp_to_int( vartypes.pass_twoscomp(left) & vartypes.pass_twoscomp(right) )
    elif op ==  '\xEF':             # OR
        return vartypes.twoscomp_to_int( vartypes.pass_twoscomp(left) | vartypes.pass_twoscomp(right) )
    elif op ==  '\xF0':             # XOR
        return vartypes.twoscomp_to_int( vartypes.pass_twoscomp(left) ^ vartypes.pass_twoscomp(right) )
    elif op == '\xF1':              # EQV
        return vartypes.twoscomp_to_int( ~(vartypes.pass_twoscomp(left) ^ vartypes.pass_twoscomp(right)) )
    elif op ==  '\xF2':             # IMP
        return vartypes.twoscomp_to_int( (~vartypes.pass_twoscomp(left)) | vartypes.pass_twoscomp(right) )
    else:
        raise error.RunError(2)

def vcaret(left, right):
    if (left[0] == '#' or right[0] == '#') and option_double:
        return fp.pack( fp.power(fp.unpack(vartypes.pass_double_keep(left)), fp.unpack(vartypes.pass_double_keep(right))) )
    else:
        if right[0] == '%':
            return fp.pack( fp.unpack(vartypes.pass_single_keep(left)).ipow_int(vartypes.unpack_int(right)) )
        else:
            return fp.pack( fp.power(fp.unpack(vartypes.pass_single_keep(left)), fp.unpack(vartypes.pass_single_keep(right))) )

def vtimes(left, right):
    if left[0] == '#' or right[0] == '#':
        return fp.pack( fp.unpack(vartypes.pass_double_keep(left)).imul(fp.unpack(vartypes.pass_double_keep(right))) )
    else:
        return fp.pack( fp.unpack(vartypes.pass_single_keep(left)).imul(fp.unpack(vartypes.pass_single_keep(right))) )

def vdiv(left, right):
    if left[0] == '#' or right[0] == '#':
        return fp.pack( fp.div(fp.unpack(vartypes.pass_double_keep(left)), fp.unpack(vartypes.pass_double_keep(right))) )
    else:
        return fp.pack( fp.div(fp.unpack(vartypes.pass_single_keep(left)), fp.unpack(vartypes.pass_single_keep(right))) )

def vplus(left, right):
    if left[0] == '$':
        return vartypes.pack_string(vartypes.pass_string_unpack(left) + vartypes.pass_string_unpack(right))
    else:
        return vartypes.number_add(left, right)

