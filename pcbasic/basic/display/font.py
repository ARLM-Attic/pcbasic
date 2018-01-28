"""
PC-BASIC - font.py
Font handling

(c) 2014--2018 Rob Hagemans
This file is released under the GNU GPL version 3 or later.
"""

import os
import logging

try:
    import numpy
except ImportError:
    numpy = None


DEFAULT_FONT = {
    u'\x00': '\x00\x00\x00\x00\x00\x00\x00\x00', u'\u2302': '\x00\x00\x108l\xc6\xc6\xfe', u'\u266a': '?3?00p\xf0\xe0', u'\u2191': '\x18<~\x18\x18\x18\x18\x00', u'\u2502': '\x18\x18\x18\x18\x18\x18\x18\x18', u'\u2195': '\x18<~\x18\x18~<\x18', u'\u2558': '\x18\x18\x1f\x18\x1f\x00\x00\x00', u' ': '\x00\x00\x00\x00\x00\x00\x00\x00', u'\xa3': '8ld\xf0``f\xfc', u'$': '\x00\x18>`<\x06|\x18', u'\xa7': '>a<ff<\x86|', u'\u03a9': '\x008l\xc6\xc6l(\xee', u'(': '\x00\x0c\x18000\x18\x0c', u'\xab': '\x00\x00\x003f\xccf3', u',': '\x00\x00\x00\x00\x00\x18\x180', u'\u03b1': '\x00\x00\x00v\xdc\xc8\xdcv', u'0': '\x008l\xc6\xd6\xc6l8', u'\u03b5': '\x00\x00\x00|\xc6p\xc6|', u'4': '\x00\x1c<l\xcc\xfe\x0c\x1e', u'\xb7': '\x00\x00\x00\x00\x18\x00\x00\x00', u'8': '\x00|\xc6\xc6|\xc6\xc6|', u'\xbb': '\x00\x00\x00\xccf3f\xcc', u'\u255e': '\x18\x18\x1f\x18\x1f\x18\x18\x18', u'<': '\x00\x06\x0c\x180\x18\x0c\x06', u'\xbf': '\x000\x0000`\xc6|', u'@': '\x00|\xc6\xde\xde\xde\xc0x', u'D': '\x00\xf8lfffl\xf8', u'\xc7': '<f\xc0\xc0f<\x18p', u'\u2660': '\x108|\xfe\xfe|\x108', u'H': '\x00\xc6\xc6\xc6\xfe\xc6\xc6\xc6', u'\u20a7': '\xf8\xcc\xcc\xfa\xc6\xcf\xc6\xc7', u'L': '\x00\xf0```bf\xfe', u'P': '\x00\xfcff|``\xf0', u'\u2552': '\x00\x00\x1f\x18\x1f\x18\x18\x18', u'T': '\x00~~Z\x18\x18\x18<', u'\u2556': '\x00\x00\x00\x00\xfe666', u'\u25d9': '\xff\xc3\x99\xbd\xbd\x99\xc3\xff', u'X': '\x00\xc6\xc6l8l\xc6\xc6', u'\u255a': '6670?\x00\x00\x00', u'\\': '\x00\xc0`0\x18\x0c\x06\x02', u'\xdf': 'x\xcc\xd8\xcc\xc6\xc6\xcc\x00', u'\u2264': '\x00\x0c\x180\x18\x0c\x00~', u'`': '0\x18\x0c\x00\x00\x00\x00\x00', u'\u2219': '\x00\x00\x00\x00\x18\x18\x00\x00', u'd': '\x00\x1c\x0c|\xcc\xcc\xccv', u'\xe7': '\x00|\xc6\xc0\xc6|\x18p', u'\u2510': '\x00\x00\x00\x00\xf8\x18\x18\x18', u'h': '\x00\xe0`lvff\xe6', u'\xeb': '\x00\xc6\x00|\xc6\xfe\xc0|', u'\u2566': '\x00\x00\xff\x00\xf7666', u'l': '\x008\x18\x18\x18\x18\x18<', u'\xef': '\x00f\x008\x18\x18\x18<', u'p': '\x00\x00\x00\xdcf|`\xf0', u'\xf3': '\x0c\x18\x00|\xc6\xc6\xc6|', u't': '\x0000\xfc006\x1c', u'\xf7': '\x00\x00\x18\x00~\x00\x18\x00', u'\u2666': '\x108|\xfe|8\x10\x00', u'x': '\x00\x00\x00\xc6l8l\xc6', u'\xfb': 'x\xcc\x00\xcc\xcc\xcc\xccv', u'|': '\x00\x18\x18\x18\x18\x18\x18\x18', u'\xff': '\x00\xc6\x00\xc6\xc6~\x06\xfc', u'\u263c': '\x18\xdb<\xe7\xe7<\xdb\x18', u'\u256a': '\x18\x18\xff\x18\xff\x18\x18\x18', u'\u2562': '6666\xf6666', u'\u0192': '\x0e\x1b\x18<\x18\x18\xd8p', u'\u2591': '"\x88"\x88"\x88"\x88', u'\u221f': '\x00\x00\xc0\xc0\xc0\xfe\x00\x00', u'\u25c4': '\x02\x0e>\xfe>\x0e\x02\x00', u'\u2321': '\x18\x18\x18\x18\x18\xd8\xd8p', u'\xa0': '\x00\x00\x00\x00\x00\x00\x00\x00', u'#': '\x00ll\xfel\xfell', u"'": '\x00\x18\x180\x00\x00\x00\x00', u'\u03a6': '\x00\x10|\xd6\xd6\xd6|\x10', u'+': '\x00\x00\x18\x18~\x18\x18\x00', u'\xac': '\x00\x00\x00\xfe\x06\x06\x00\x00', u'/': '\x00\x06\x0c\x180`\xc0\x80', u'\xb0': '\x008ll8\x00\x00\x00', u'3': '\x00|\xc6\x06<\x06\xc6|', u'\u25b2': '\x00\x18<~\xff\xff\x00\x00', u'7': '\x00\xfe\xc6\x0c\x18000', u';': '\x00\x18\x18\x00\x00\x18\x180', u'\u25ba': '\x80\xe0\xf8\xfe\xf8\xe0\x80\x00', u'\xbc': 'c\xe6lz6j\xdf\x06', u'?': '\x00|\xc6\x0c\x18\x18\x00\x18', u'C': '\x00<f\xc0\xc0\xc0f<', u'\xc4': '\xc6\x108l\xc6\xfe\xc6\xc6', u'G': '\x00<f\xc0\xc0\xcef:', u'\u03c6': '\x00\x00\x00\\\xd6\xd6|\x10', u'K': '\x00\xe6flxlf\xe6', u'\u263b': '~\xff\xdb\xff\xc3\xe7\xff~', u'O': '\x00|\xc6\xc6\xc6\xc6\xc6|', u'\u2551': '66666666', u'S': '\x00<f0\x18\x0cf<', u'\u2022': '\x00\x00\x18<<\x18\x00\x00', u'\u2555': '\x00\x00\xf8\x18\xf8\x18\x18\x18', u'W': '\x00\xc6\xc6\xc6\xd6\xd6\xfel', u'\u2559': '6666?\x00\x00\x00', u'[': '\x00<00000<', u'\u255d': '66\xf6\x06\xfe\x00\x00\x00', u'\xdc': '\xc6\x00\xc6\xc6\xc6\xc6\xc6|', u'_': '\x00\x00\x00\x00\x00\x00\x00\xff', u'\u2561': '\x18\x18\xf8\x18\xf8\x18\x18\x18', u'\xe0': '`0\x00x\x0c|\xccv', u'c': '\x00\x00\x00|\xc6\xc0\xc6|', u'\u2565': '\x00\x00\x00\x00\xff666', u'\xe4': '\x00\xcc\x00x\x0c|\xccv', u'g': '\x00\x00\x00v\xcc|\x0c\xf8', u'\u2569': '66\xf7\x00\xff\x00\x00\x00', u'\xe8': '0\x18\x00|\xc6\xfe\xc0|', u'k': '\x00\xe0`flxl\xe6', u'\xec': '0\x18\x008\x18\x18\x18<', u'o': '\x00\x00\x00|\xc6\xc6\xc6|', u'\u2590': '\x0f\x0f\x0f\x0f\x0f\x0f\x0f\x0f', u's': '\x00\x00\x00~\xc0|\x06\xfc', u'\xf4': '8l\x00|\xc6\xc6\xc6|', u'w': '\x00\x00\x00\xc6\xd6\xd6\xfel', u'{': '\x00\x0e\x18\x18p\x18\x18\x0e', u'\xfc': '\x00\xcc\x00\xcc\xcc\xcc\xccv', u'\u207f': '\x00l6666\x00\x00', u'\u2500': '\x00\x00\x00\x00\xff\x00\x00\x00', u'\u2248': '\x00\x00v\xdc\x00v\xdc\x00', u'\u2193': '\x18\x18\x18\x18~<\x18\x00', u'\u250c': '\x00\x00\x00\x00\x1f\x18\x18\x18', u'\u2310': '\x00\x00\x00\xfe\xc0\xc0\x00\x00', u'\u0393': '\x00\xfeb````\xf0', u'\u2192': '\x00\x18\x0c\xfe\x0c\x18\x00\x00', u'\u2514': '\x18\x18\x18\x18\x1f\x00\x00\x00', u'\u2518': '\x18\x18\x18\x18\xf8\x00\x00\x00', u'\u221a': '\x0f\x0c\x0c\x0c\xecl<\x1c', u'\u251c': '\x18\x18\x18\x18\x1f\x18\x18\x18', u'\u221e': '\x00\x00~\xdb\xdb~\x00\x00', u'\xa1': '\x00\x18\x00\x18\x18<<\x18', u'\u2320': '\x0e\x1b\x1b\x18\x18\x18\x18\x18', u'\u03a3': '\x00\xfe\xc6`0`\xc6\xfe', u'"': '\x00ff$\x00\x00\x00\x00', u'\xa5': 'ff<~\x18~\x18\x18', u'\u2524': '\x18\x18\x18\x18\xf8\x18\x18\x18', u'&': '\x008l8v\xdc\xccv', u'*': '\x00\x00f<\xff<f\x00', u'\u252c': '\x00\x00\x00\x00\xff\x18\x18\x18', u'.': '\x00\x00\x00\x00\x00\x00\x18\x18', u'\xb1': '\x00\x18\x18~\x18\x18\x00~', u'2': '\x00|\xc6\x06\x1c0f\xfe', u'\xb5': '\x00\x00\x00fff|\xc0', u'\u2534': '\x18\x18\x18\x18\xff\x00\x00\x00', u'6': '\x008`\xc0\xfc\xc6\xc6|', u':': '\x00\x00\x18\x18\x00\x00\x18\x18', u'\xbd': 'c\xe6l~3f\xcc\x0f', u'\u253c': '\x18\x18\x18\x18\xff\x18\x18\x18', u'>': '\x00`0\x18\x0c\x180`', u'\u2261': '\x00\x00\xfe\x00\xfe\x00\xfe\x00', u'\u03c3': '\x00\x00\x00~\xd8\xd8\xd8p', u'B': '\x00\xfcff|ff\xfc', u'\xc5': '8l8|\xc6\xfe\xc6\xc6', u'\u2665': 'l\xfe\xfe\xfe|8\x10\x00', u'F': '\x00\xfebhxh`\xf0', u'\xc9': '\x0c\x18\xfe\xc0\xf8\xc0\xc0\xfe', u'\u25cb': '\x00<fBBf<\x00', u'J': '\x00\x1e\x0c\x0c\x0c\xcc\xccx', u'\u2663': '8|8\xfe\xfe\xd6\x108', u'N': '\x00\xc6\xe6\xf6\xde\xce\xc6\xc6', u'\xd1': 'v\xdc\x00\xe6\xf6\xde\xce\xc6', u'\u2550': '\x00\x00\xff\x00\xff\x00\x00\x00', u'R': '\x00\xfcff|lf\xe6', u'\u2554': '\x00\x00?07666', u'V': '\x00\xc6\xc6\xc6\xc6\xc6l8', u'\u2265': '\x000\x18\x0c\x180\x00~', u'Z': '\x00\xfe\xc6\x8c\x182f\xfe', u'\u255c': '6666\xfe\x00\x00\x00', u'^': '\x108l\x00\x00\x00\x00\x00', u'\xe1': '\x180\x00x\x0c|\xccv', u'\u2560': '66707666', u'b': '\x00\xe0`|fff\xdc', u'\xe5': '8l8x\x0c|\xccv', u'\u2564': '\x00\x00\xff\x00\xff\x18\x18\x18', u'f': '\x00<f`\xf8``\xf0', u'\xe9': '\x0c\x18\x00|\xc6\xfe\xc0|', u'\u2568': '6666\xff\x00\x00\x00', u'j': '\x00\x06\x00\x06\x06\x06f<', u'\xed': '\x0c\x18\x008\x18\x18\x18<', u'\u256c': '66\xf7\x00\xf7666', u'n': '\x00\x00\x00\xdcffff', u'\xf1': 'v\xdc\x00\xdcffff', u'r': '\x00\x00\x00\xdcv``\xf0', u'v': '\x00\x00\x00\xc6\xc6\xc6l8', u'\xf9': '`0\x00\xcc\xcc\xcc\xccv', u'z': '\x00\x00\x00~\x0c\x180~', u'\u266b': '\x7fc\x7fccg\xe6\xc0', u'\u2592': 'U\xaaU\xaaU\xaaU\xaa', u'~': 'v\xdc\x00\x00\x00\x00\x00\x00', u'\u2580': '\xff\xff\xff\xff\x00\x00\x00\x00', u'\u2584': '\x00\x00\x00\x00\xff\xff\xff\xff', u'\u2640': '<fff<\x18~\x18', u'\u2588': '\xff\xff\xff\xff\xff\xff\xff\xff', u'\u258c': '\xf0\xf0\xf0\xf0\xf0\xf0\xf0\xf0', u'\u2190': '\x000`\xfe`0\x00\x00', u'\u2642': '\x0f\x07\x0f}\xcc\xcc\xccx', u'\u2194': '\x00$f\xfff$\x00\x00', u'\u203c': 'fffff\x00f\x00', u'\u0398': '\x00|\xc6\xc6\xfe\xc6\xc6|', u'!': '\x00\x18<<\x18\x18\x00\x18', u'\u25a0': '\x00\x00<<<<\x00\x00', u'\xa2': '\x18\x18~\xc0\xc0~\x18\x18', u'%': '\x00\x00\xc6\xcc\x180f\xc6', u')': '\x000\x18\x0c\x0c\x0c\x180', u'\u21a8': '\x18<~\x18~<\x18\xff', u'\xaa': '\x00<ll6\x00~\x00', u'-': '\x00\x00\x00\x00~\x00\x00\x00', u'\u25ac': '\x00\x00\x00\x00~~~\x00', u'1': '\x00\x188\x18\x18\x18\x18~', u'\xb2': '\x00x\x0c\x180|\x00\x00', u'5': '\x00\xfe\xc0\xc0\xfc\x06\xc6|', u'\u03b4': '\x00<`8|\xc6\xc6|', u'\xb6': '\x7f\xdb\xdb{\x1b\x1b\x1b\x00', u'9': '\x00|\xc6\xc6~\x06\x0cx', u'\xba': '\x008ll8\x00|\x00', u'=': '\x00\x00\x00~\x00\x00~\x00', u'\u25bc': '\x00\xff\xff~<\x18\x00\x00', u'A': '\x008l\xc6\xfe\xc6\xc6\xc6', u'\u03c0': '\x00\x00\x00\xfellll', u'E': '\x00\xfebhxhb\xfe', u'\u03c4': '\x00\x00\x00\xfe006\x1c', u'\xc6': '\x00>l\xcc\xfe\xcc\xcc\xce', u'I': '\x00<\x18\x18\x18\x18\x18<', u'M': '\x00\xc6\xee\xfe\xfe\xd6\xc6\xc6', u'\u263a': '~\x81\xa5\x81\xbd\x99\x81~', u'Q': '\x00|\xc6\xc6\xc6\xce|\x0e', u'\u2553': '\x00\x00\x00\x00?666', u'U': '\x00\xc6\xc6\xc6\xc6\xc6\xc6|', u'\u2557': '\x00\x00\xfe\x06\xf6666', u'\xd6': '\xc6\x008l\xc6\xc6l8', u'Y': '\x00fff<\x18\x18<', u'\u25d8': '\xff\xff\xe7\xc3\xc3\xe7\xff\xff', u'\u255b': '\x18\x18\xf8\x18\xf8\x00\x00\x00', u']': '\x00<\x0c\x0c\x0c\x0c\x0c<', u'\u255f': '66667666', u'a': '\x00\x00\x00x\x0c|\xccv', u'\u2563': '66\xf6\x06\xf6666', u'\xe2': '8l\x00x\x0c|\xccv', u'e': '\x00\x00\x00|\xc6\xfe\xc0|', u'\u2567': '\x18\x18\xff\x00\xff\x00\x00\x00', u'\xe6': '\x00\x00\x00\xec6~\xd8n', u'i': '\x00\x18\x008\x18\x18\x18<', u'\u256b': '6666\xff666', u'\xea': '8l\x00|\xc6\xfe\xc0|', u'm': '\x00\x00\x00\xec\xfe\xd6\xd6\xd6', u'\xee': '8l\x008\x18\x18\x18<', u'q': '\x00\x00\x00v\xcc|\x0c\x1e', u'\u2229': '\x00|\xc6\xc6\xc6\xc6\xc6\x00', u'\xf2': '0\x18\x00|\xc6\xc6\xc6|', u'u': '\x00\x00\x00\xcc\xcc\xcc\xccv', u'\xf6': '\x00\xc6\x00|\xc6\xc6\xc6|', u'y': '\x00\x00\x00\xc6\xc6~\x06\xfc', u'\u2593': 'w\xddw\xddw\xddw\xdd', u'\xfa': '\x180\x00\xcc\xcc\xcc\xccv', u'}': '\x00p\x18\x18\x0e\x18\x18p'
}


class Font(object):
    """Single-height bitfont."""

    def __init__(self, height, fontdict={}):
        """Initialise the font."""
        self.height = height
        if height == 8 and not fontdict:
            fontdict = DEFAULT_FONT
        self.fontdict = fontdict

    def build_glyph(self, c, req_width, req_height, carry_col_9, carry_row_9):
        """Build a glyph for the given unicode character."""
        # req_width can be 8, 9 (SBCS), 16, 18 (DBCS) only
        req_width_base = req_width if req_width <= 9 else req_width // 2
        try:
            face = bytearray(self.fontdict[c])
        except KeyError:
            logging.debug(u'%s [%s] not represented in font, replacing with blank glyph.', c, repr(c))
            face = bytearray(int(self.height))
        # shape of encoded mask (8 or 16 wide; usually 8, 14 or 16 tall)
        code_height = 8 if req_height == 9 else req_height
        code_width = (8*len(face))//code_height
        force_double = req_width >= code_width*2
        force_single = code_width >= (req_width-1)*2
        if force_double or force_single:
            # i.e. we need a double-width char but got single or v.v.
            logging.debug(u'Incorrect glyph width for %s [%s]: %d-pixel requested, %d-pixel found.', c, repr(c), req_width, code_width)
        if numpy:
            glyph = numpy.unpackbits(face, axis=0).reshape((code_height, code_width)).astype(bool)
            # repeat last rows (e.g. for 9-bit high chars)
            if req_height > glyph.shape[0]:
                if carry_row_9:
                    repeat_row = glyph[-1]
                else:
                    repeat_row = numpy.zeros((1, code_width), dtype = numpy.uint8)
                while req_height > glyph.shape[0]:
                    glyph = numpy.vstack((glyph, repeat_row))
            if force_double:
                glyph = glyph.repeat(2, axis=1)
            elif force_single:
                glyph = glyph[:, ::2]
            # repeat last cols (e.g. for 9-bit wide chars)
            if req_width > glyph.shape[1]:
                if carry_col_9:
                    repeat_col = numpy.atleast_2d(glyph[:,-1]).T
                else:
                    repeat_col = numpy.zeros((code_height, 1), dtype = numpy.uint8)
                while req_width > glyph.shape[1]:
                    glyph = numpy.hstack((glyph, repeat_col))
        else:
            # if our code glyph is too wide for request, we need to make space
            start_width = req_width*2 if force_single else req_width
            glyph = [ [False]*start_width for _ in range(req_height) ]
            for yy in range(code_height):
                for half in range(code_width//8):
                    line = face[yy*(code_width//8)+half]
                    for xx in range(8):
                        if (line >> (7-xx)) & 1 == 1:
                            glyph[yy][half*8 + xx] = True
                # halve the width if code width incorrect
                if force_single:
                    glyph[yy] = glyph[yy][::2]
                # MDA/VGA 9-bit characters
                # carry_col_9 will be ignored for double-width glyphs
                if carry_col_9 and req_width == 9:
                    glyph[yy][8] = glyph[yy][7]
            # tandy 9-bit high characters
            if carry_row_9 and req_height == 9:
                for xx in range(8):
                    glyph[8][xx] = glyph[7][xx]
            # double the width if code width incorrect
            if force_double:
                for yy in range(code_height):
                    for xx in range(req_width_base, -1, -1):
                        glyph[yy][2*xx+1] = glyph[yy][xx]
                        glyph[yy][2*xx] = glyph[yy][xx]
        return glyph