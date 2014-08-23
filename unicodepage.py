
# Codepage 437 to Unicode table 
# with Special Graphic Characters
# http://en.wikipedia.org/wiki/Code_page_437
# http://msdn.microsoft.com/en-us/library/cc195060.aspx
# http://msdn.microsoft.com/en-us/goglobal/cc305160

import logging
import os
import plat

# where to find unicode tables
encoding_dir = os.path.join(plat.basepath, 'encoding')

# default CP437 unicode table
cp437 = (
    u'\u0000\u263A\u263B\u2665\u2666\u2663\u2660\u2022\u25D8\u25CB\u25D9\u2642\u2640\u266A\u266B\u263C' +
    u'\u25BA\u25C4\u2195\u203C\u00B6\u00A7\u25AC\u21A8\u2191\u2193\u2192\u2190\u221F\u2194\u25B2\u25BC' +
    u'\u0020\u0021\u0022\u0023\u0024\u0025\u0026\u0027\u0028\u0029\u002A\u002B\u002C\u002D\u002E\u002F' +
    u'\u0030\u0031\u0032\u0033\u0034\u0035\u0036\u0037\u0038\u0039\u003A\u003B\u003C\u003D\u003E\u003F' +
    u'\u0040\u0041\u0042\u0043\u0044\u0045\u0046\u0047\u0048\u0049\u004A\u004B\u004C\u004D\u004E\u004F' +
    u'\u0050\u0051\u0052\u0053\u0054\u0055\u0056\u0057\u0058\u0059\u005A\u005B\u005C\u005D\u005E\u005F' +
    u'\u0060\u0061\u0062\u0063\u0064\u0065\u0066\u0067\u0068\u0069\u006A\u006B\u006C\u006D\u006E\u006F' +
    u'\u0070\u0071\u0072\u0073\u0074\u0075\u0076\u0077\u0078\u0079\u007A\u007B\u007C\u007D\u007E\u2302' +
    u'\u00c7\u00fc\u00e9\u00e2\u00e4\u00e0\u00e5\u00e7\u00ea\u00eb\u00e8\u00ef\u00ee\u00ec\u00c4\u00c5' +
    u'\u00c9\u00e6\u00c6\u00f4\u00f6\u00f2\u00fb\u00f9\u00ff\u00d6\u00dc\u00a2\u00a3\u00a5\u20a7\u0192' +
    u'\u00e1\u00ed\u00f3\u00fa\u00f1\u00d1\u00aa\u00ba\u00bf\u2310\u00ac\u00bd\u00bc\u00a1\u00ab\u00bb' +
    u'\u2591\u2592\u2593\u2502\u2524\u2561\u2562\u2556\u2555\u2563\u2551\u2557\u255d\u255c\u255b\u2510' +
    u'\u2514\u2534\u252c\u251c\u2500\u253c\u255e\u255f\u255a\u2554\u2569\u2566\u2560\u2550\u256c\u2567' +
    u'\u2568\u2564\u2565\u2559\u2558\u2552\u2553\u256b\u256a\u2518\u250c\u2588\u2584\u258c\u2590\u2580' +
    u'\u03b1\u00df\u0393\u03c0\u03a3\u03c3\u00b5\u03c4\u03a6\u0398\u03a9\u03b4\u221e\u03c6\u03b5\u2229' +
    u'\u2261\u00b1\u2265\u2264\u2320\u2321\u00f7\u2248\u00b0\u2219\u00b7\u221a\u207f\u00b2\u25a0\u00a0'
    )

# on the terminal, these values are not shown as special graphic chars but as their normal effect
control = (
    '\x07', # BEL
    #'\x08',# BACKSPACE
    '\x09', # TAB 
    '\x0a', # LF
    '\x0b', # HOME
    '\x0c', # clear screen
    '\x0d', # CR
    '\x1c', # RIGHT
    '\x1d', # LEFT
    '\x1e', # UP
    '\x1f', # DOWN
    ) 

# is the current codepage a double-byte codepage?
dbcs = False

def from_unicode(s):
    output = ''
    for c in s:
        if ord(c) == 0:
            # double NUL characters as single NUL signals scan code
            output += '\x00\x00'
        else:
            try: 
                output += chr(unicode_to_cp[c])
            except KeyError:
                if ord(c) <= 0xff:
                    output += chr(ord(c))
    return output

def load_codepage(codepage_name):
    # always load a single-byte page
    codepage_name = load_sbcs_codepage(codepage_name)
    # if .lead file exists, this is a DBCS codepage. Load the big table    
    if os.path.exists(os.path.join(encoding_dir, codepage_name + '.lead')):
        codepage_name = load_dbcs_codepage(codepage_name)
    return codepage_name
    
def load_sbcs_codepage(codepage_name):
    global cp_to_unicode, unicode_to_cp, cp_to_utf8, utf8_to_cp, lead, trail, dbcs
    cp_to_unicode = dict(enumerate(cp437))
    name = os.path.join(encoding_dir, codepage_name + '.utf8')
    try:
        f = open(name, 'rb')
        # convert utf8 string to dict
        dict_string = f.read().decode('utf-8')[:128]
        for i in range(128, 256):
            cp_to_unicode[i] = dict_string[i-128]
    except IOError:
        logging.warning('Could not load unicode mapping table for codepage %s. Falling back to codepage 437.', codepage_name)
        codepage_name = '437'
    # update dict with basic ASCII and special graphic characters
    unicode_to_cp = dict((reversed(item) for item in cp_to_unicode.items()))
    cp_to_utf8 = dict([ (chr(s[0]), s[1].encode('utf-8')) for s in cp_to_unicode.items()])
    utf8_to_cp = dict((reversed(item) for item in cp_to_utf8.items()))
    # this is not a DBCS codepage so no lead and trail bytes
    lead = []
    trail = []
    dbcs = False
    return codepage_name  

def load_dbcs_codepage(codepage_name):
    global dbcs_utf8_to_cp, dbcs_cp_to_utf8, lead, trail, dbcs, dbcs_num_chars
    # load double-byte unicode table
    name = os.path.join(encoding_dir, codepage_name + '.dbcs')
    try:
        f = open(name, 'rb')
        dbcs_unicode_table = f.read().decode('utf-8')
    except IOError:
        logging.warning('Could not load double-byte unicode mapping table for codepage %s. Falling back to codepage 437.', codepage_name)
        return '437'
    # load lead and trail byte tables 
    name = os.path.join(encoding_dir, codepage_name + '.lead')
    try:
        f = open(name, 'rb')
        leadtrail = list(f)
        lead = [ chr(x[0]) for x in enumerate(leadtrail[0][:256]) if x[1] != '0']
        trail = [ chr(x[0]) for x in enumerate(leadtrail[1][:256]) if x[1] != '0']
    except IOError:
        logging.warning('Could not load lead-byte table for double-byte codepage %s. Falling back to codepage 437.', codepage_name)
        return '437'
    dbcs_cp_to_unicode = dict([ 
        ( l+t, dbcs_unicode_table[lead.index(l)*len(trail)+trail.index(t)]) for l in lead for t in trail])
    dbcs_cp_to_utf8 = dict([ (s[0], s[1].encode('utf-8')) for s in dbcs_cp_to_unicode.items()])
    dbcs_utf8_to_cp = dict((reversed(item) for item in dbcs_cp_to_utf8.items()))
    dbcs = True    
    dbcs_num_chars = len(dbcs_unicode_table)
    return codepage_name  

# convert utf8 wchar to codepage char        
def from_utf8(c):
    try:
        return utf8_to_cp[c]
    except KeyError:    
        return dbcs_utf8_to_cp[c]

# line buffer for conversion to UTF8 - supports DBCS                                    
class UTF8Converter (object):
    def __init__(self):
        self.buf = ''

    # add chars to buffer
    def to_utf8(self, s, preserve_control=False):        
        if not dbcs:
            # stateless if not dbcs
            return ''.join([ (c if (preserve_control and c in control) else cp_to_utf8[c]) for c in s ])
        else:
            out = ''
            if self.buf:
                # remove the naked lead-byte first
                out += '\b'                
            for c in s:
                if preserve_control and c in control:
                    if self.buf:
                        out += cp_to_unicode[self.buf]
                        self.buf = ''
                    out += c
                    continue
                elif self.buf:
                    if c in trail:
                        out += dbcs_cp_to_utf8[self.buf+c] 
                        self.buf = ''
                        continue
                    else:
                        out += cp_to_utf8[self.buf] 
                        self.buf = ''
                if c in lead:
                    self.buf = c
                else:
                    out += cp_to_utf8[c]
            # any naked lead-byte left will be printed        
            if self.buf:
                out += cp_to_utf8[self.buf]
            return out
        
    
    
