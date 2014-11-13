#
# PC-BASIC 3.23 
#
# Configuration file and command-line options parser
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import os
import sys
import ConfigParser
import logging
import zipfile
import plat

# by default, load what's in section [pcbasic] and override with anything 
# in os-specific section [windows] [android] [linux] [osx] [unknown_os]
default_presets = ['pcbasic', plat.system.lower()]

# get supported codepages
encodings = sorted([ x[0] for x in [ c.split('.ucp') 
                     for c in os.listdir(plat.encoding_dir) ] if len(x)>1])
# get supported font families
families = sorted(list(set([ x[0] for x in [ c.split('_') 
                  for c in os.listdir(plat.font_dir) ] if len(x)>1])))

# dictionary to hold all options chosen
options = {}
# flag True if we're running from a package
package = False

# GWBASIC invocation, for reference:
# GWBASIC [prog] [<inp] [[>]>outp] [/f:n] [/i] [/s:n] [/c:n] [/m:[n][,n]] [/d]
#   /d      Allow double-precision ATN, COS, EXP, LOG, SIN, SQR, and TAN. 
#   /f:n    Set maximum number of open files to n. Default is 3. 
#           Each additional file reduces free memory by 322 bytes.
#   /s:n    Set the maximum record length for RANDOM files. 
#           Default is 128, maximum is 32768.
#   /c:n    Set the COM receive buffer to n bytes. 
#           If n==0, disable the COM ports.   
# NOT IMPLEMENTED:
#   /i      Statically allocate file control blocks and data buffer.
#   /m:n,m  Set the highest memory location to n and maximum block size to m
short_args = { 
    'd': 'double', 'f': 'max-files', 
    's': 'max-reclen', 'c': 'serial-buffer-size',
    # 'm': 'max-memory', 'i': 'static-fcbs': 'i',
    'b': 'cli', 't': 'ansi', 'l': 'load', 'h': 'help',  
    'r': 'run', 'e': 'exec', 'q': 'quit', 'k': 'keys', 'v': 'version',
    }

# all long-form arguments
arguments = {
    'input': {'type': 'string', 'default': '', },
    'output': {'type': 'string', 'default': '', },
    'append': {'type': 'bool', 'default': 'False', },
    'cli': {'type': 'bool', 'default': 'False', },
    'ansi': {'type': 'bool', 'default': 'False', },
    'interface': { 
        'type': 'string', 'default': '',
        'choices': ('none', 'cli', 'ansi', 'graphical'), },
    'load': {'type': 'string', 'default': '', },
    'run': {'type': 'string', 'default': '',  },
    'convert': {'type': 'string', 'default': '', },
    'help': {'type': 'bool', 'default': 'False', },
    'keys': {'type': 'string', 'default': '', },
    'exec': {'type': 'string', 'default': '',  },
    'quit': {'type': 'bool', 'default': 'False',},
    'double': {'type': 'bool', 'default': 'False',},
    'max-files': {'type': 'int', 'default': 3,}, 
    'max-reclen': {'type': 'int', 'default': 128,},
    'serial-buffer-size': {'type': 'int', 'default': 256,},
    'peek': {'type': 'list', 'default': '',},
    'lpt1': {'type': 'string', 'default': '',},
    'lpt2': {'type': 'string', 'default': '',},
    'lpt3': {'type': 'string', 'default': '',},
    'com1': {'type': 'string', 'default': '',},
    'com2': {'type': 'string', 'default': '',},
    'codepage': {'type': 'string', 'choices': encodings, 'default': '437',},
    'font': { 
        'type': 'list', 'choices': families, 
        'default': 'unifont,univga,freedos',},
    'nosound': {'type': 'bool', 'default': 'False', },
    'dimensions': {'type': 'string', 'default': '',},
    'fullscreen': {'type': 'bool', 'default': 'False',},
    'noquit': {'type': 'bool', 'default': 'False',},
    'debug': {'type': 'bool', 'default': 'False',},
    'strict-hidden-lines': {'type': 'bool', 'default': 'False',},
    'strict-protect': {'type': 'bool', 'default': 'False',},
    'capture-caps': {'type': 'bool', 'default': 'False',},
    'mount': {'type': 'list', 'default': '',},
    'resume': {'type': 'bool', 'default': 'False',},
    'strict-newline': {'type': 'bool', 'default': 'False',},
    'syntax': { 
        'type': 'string', 'choices': ('advanced', 'pcjr', 'tandy'), 
        'default': 'advanced',},
    'pcjr-term': {'type': 'string', 'default': '',},
    'video': { 
        'type': 'string', 'default': 'vga',
        'choices': ('vga', 'ega', 'cga', 'cga_old', 'mda', 'pcjr', 'tandy',
                     'hercules', 'olivetti'), },
    'map-drives': {'type': 'bool', 'default': 'False',},
    'cga-low': {'type': 'bool', 'default': 'False',},
    'nobox': {'type': 'bool', 'default': 'False',},
    'utf8': {'type': 'bool', 'default': 'False',},
    'border': {'type': 'int', 'default': 5,},
    'mouse': {'type': 'string', 'default': 'copy,paste,pen',},
    'state': {'type': 'string', 'default': '',},
    'mono-tint': {'type': 'string', 'default': '255,255,255',},
    'monitor': { 
        'type': 'string', 'choices': ('rgb', 'composite', 'mono'),
        'default': 'rgb',},
    'aspect': {'type': 'string', 'default': '4,3',},
    'blocky': {'type': 'bool', 'default': 'False',},
    'version': {'type': 'bool', 'default': 'False',},
    'preset': {'type': 'list', 'default': ','.join(default_presets), },
    'config': {'type': 'string', 'default': '',},
}


def prepare():
    """ Initialise config.py """
    global options
    # store options in options dictionary
    options = get_options()
    
def get_options():
    """ Retrieve command line and option file options. """
    # convert command line arguments to string dictionary form
    remaining = get_arguments(sys.argv[1:])
    # set overall default arguments
    args = default_arguments()
    # unpack any packages and parse program arguments
    args.update(parse_package(remaining))
    # get arguments and presets from specified config file
    conf_dict = parse_config(remaining)
    # set defaults based on presets
    args.update(parse_presets(remaining, conf_dict))
    # parse rest of command line
    args.update(parse_args(remaining))
    # clean up arguments    
    clean_arguments(args)
    return args        

def clean_arguments(args):
    """ Convert arguments to required type. """
    for d in args:
        try:
            if (arguments[d]['type'] == 'list'):
                args[d] = parse_list(args[d])
            elif (arguments[d]['type'] == 'int'):
                args[d] = parse_int(args[d])
            elif (arguments[d]['type'] == 'bool'):
                args[d] = parse_bool(args[d])
        except KeyError:
            pass


def get_arguments(argv):
    """ Convert arguments to { key: value } dictionary. """
    args = {}
    for arg in argv:
        arglist = arg.split('=', 1)
        key = arglist[0]
        if len(arglist) > 0:
            value = arglist[0]
        else:
            value = ''
        pos = 0
        if key:
            if key[0:2] == '--':
                if key[2:]:
                    args[key[2:]] = value
            elif key[0] == '-':
                for i, short_arg in enumerate(key[1:]):
                    try:
                        if i == len(key)-1:
                            # assign value to last argument specified    
                            args[short_args[short_arg]] = value 
                        else:
                            args[short_args[short_arg]] = ''
                    except KeyError:    
                        logging.warning('Ignored unrecognised argument -%s', short_arg)
            else:
                # positional argument
                args[pos] = arg  
                pos += 1
        else:
            logging.warning('Ignored unrecognised argument =%s', value)
    return args    

def default_arguments():
    """ Set overall default arguments. """
    args = {}
    for arg in arguments:
        try:
            args[arg] = arguments[arg]['default']
        except KeyError:
            pass
    return args
            
def preset_default_args(conf_dict):
    """ Return default arguments for this operating system. """
    args = {}
    for p in default_presets:
        try:
            args.update(conf_dict[p])
        except KeyError:
            pass
    return args

def parse_presets(remaining, conf_dict):
    """ Parse presets. """
    try:
        presets = parse_list(remaining.pop('preset'))
    except KeyError:
        presets = []    
    # get dictionary of default config
    defaults = preset_default_args(conf_dict)
    # add any nested presets defined in [pcbasic] section
    try:
        presets += parse_list(conf_dict['pcbasic']['preset'])
    except KeyError:
        pass
    # set machine preset options; command-line args will override these
    if presets:
        for preset in presets:
            try:
                defaults.update(**conf_dict[preset])
            except KeyError:
                logging.warning('Preset %s not defined', preset)
    return defaults

def parse_package(remaining):
    """ Load options from BAZ package, if specified. """
    global package
    # first positional arg: program or package name
    args = { 'program': None }
    try:
        arg_package = remaining.pop(0)
    except KeyError:
        return args
    if zipfile.is_zipfile(arg_package):
        # extract the package to a temp directory
        # and make that the current dir for our run
        zipfile.ZipFile(arg_package).extractall(path=plat.temp_dir)
        os.chdir(plat.temp_dir)    
        # recursively rename all files to all-caps to avoid case issues on Unix
        # collisions: the last file renamed overwrites earlier ones
        for root, dirs, files in os.walk('.', topdown=False):
            for name in dirs + files:
                try:
                    os.rename(os.path.join(root, name), 
                              os.path.join(root, name.upper()))
                except OSError:
                    # if we can't rename, ignore
                    pass    
        package = arg_package
    else:
        # it's not a package, treat it as a BAS program.
        args['program'] = arg_package
    return args

def parse_config(remaining):
    """ Find the correct config file and read it. """
    # always read default config file
    conf_dict = read_config_file(os.path.join(plat.info_dir, plat.config_name))
    # find any overriding config file & read it
    config_file = None
    try:
        config_file = remaining.pop('config')
    except KeyError:
        if os.path.exists(plat.config_name):
            config_file = plat.config_name
    # update a whole preset at once, there's no joining of settings.                
    if config_file:
        conf_dict.update(read_config_file(config_file))
    return conf_dict
    
def parse_args(remaining):
    """ Retrieve command line options. """
    # set arguments
    args = { d:remaining[d] for d in remaining if d in arguments }
    not_recognised = { d:remaining[d] for d in remaining if d not in arguments }
    for d in not_recognised:
        logging.warning('Ignored unrecognised argument %s=%s', d, not_recognised[d])
    return args

################################################

def read_config_file(config_file):
    """ Read config file. """
    path = plat.basepath
    try:
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(config_file)
    except (ConfigParser.Error, IOError):
        logging.warning('Error in configuration file %s. '
                        'Configuration not loaded.', config_file)
        return {}
    presets = { header: dict(config.items(header)) 
                for header in config.sections() }    
    return presets

################################################
    
def parse_list(s):
    """ Convert list strings from option file to lists. """
    lst = s.split(',')
    if lst == ['']:
        return []
    return lst

def parse_bool(s):
    """ Parse bool option. Empty means True (like store_true). """
    if s == '' or s == []:
        return True
    try:
        if s.upper() in ('YES', 'TRUE', 'ON'):
            return True
        elif s.upper() in ('NO', 'FALSE', 'OFF'):
            return False   
    except AttributeError:
        return None

def parse_int(inargs):
    """ Parse int option provided as a one-element list of string. """
    if inargs:
        try:
            return int(inargs)
        except ValueError:
            logging.warning('Illegal number value %s ignored', inargs)         
    return None


# DEPRECATE
def parse_pair(option, default):
    """ Split a string option into int values. """
    if options[option]:
        try:
            sx, sy = options[option].split(',')
            x, y = int(sx), int(sy)
        except (ValueError, TypeError):
            logging.warning('Could not parse option: %s=%s. '
                            'Provide two values separated by a comma.', 
                            option, options[option]) 
        return x, y
    return default    

#########################################################

def write_config():
    """ Write a default config file. """
    argnames = sorted(arguments.keys())
    f = open(plat.config_name, 'w')
    f.write('[pcbasic]\n')
    for a in argnames:
        f.write("# %s\n" % arguments[a]['help'])
        try:
            f.write('# %s=%s\n' % (a, arguments[a]['metavar']))
        except (KeyError, TypeError):
            pass
        try:
            f.write('# choices: %s\n' % repr(arguments[a]['choices']))
        except (KeyError, TypeError):
            pass
        if arguments[a]['type'] == 'list':
            formatted = ','.join(arguments[a]['default'])
        else:
            formatted = str(arguments[a]['default'])
        f.write("%s=%s\n" % (a, formatted))
    f.close()    
        
# initialise this module    
prepare()
    
