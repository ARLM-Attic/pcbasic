#
# PC-BASIC 3.23  - os_windows.py
#
# Windows-specific OS utilities
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

import os
import msvcrt
import ctypes
import string
import fnmatch
import subprocess
import threading
import win32print
import win32ui
import win32api

import error
import console
 
shell = 'CMD'    
shell_cmd = shell + ' /c'

drives = { }
current_drive = os.path.abspath(os.sep).split(':')[0]
    
def disk_free(path):
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
    return free_bytes.value
   
def process_stdout(p, stream):
    while True:
        c = stream.read(1)
        if c != '': 
            if c!= '\r':
                console.write(c)
            else:
                console.check_events()
        elif p.poll() != None:
            break        

def spawn_interactive_shell(cmd):
    p = subprocess.Popen( str(cmd).split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True )
    outp = threading.Thread(target=process_stdout, args=(p, p.stdout))
    outp.daemon = True
    outp.start()
    errp = threading.Thread(target=process_stdout, args=(p, p.stderr))
    errp.daemon = True
    errp.start()
    chars = 0
    while p.poll() == None:
        console.idle()
        c = console.get_char()
        if p.poll () != None:
            break
        else:    
            if c in ('\r', '\n'): 
                # fix double echo after enter press
                console.write('\x1D'*chars)
                chars = 0
                p.stdin.write('\r\n')
            elif c != '':
                p.stdin.write(c)
                # windows only seems to echo this to the pipe after enter pressed
                console.write(c)
                chars +=1
    outp.join()
    errp.join()

# get windows short name
def dossify(path, name):
    if not path:
        path = current_drive
    try:
        shortname = win32api.GetShortPathName(os.path.join(path, name)).upper()
    except Exception as e:
        # something went wrong, show as dots in FILES
        return "........", "..."
    split = shortname.split('\\')[-1].split('.')
    trunk, ext = split[0], ''
    if len(split)>1:
        ext = split[1]
    if len(trunk)>8 or len(ext)>3:
        # on some file systems, ShortPathName returns the long name
        trunk = trunk[:8]
        ext = '...'    
    return trunk, ext    

def dossify_path(name):
    return win32api.GetShortPathName(name).upper()

def get_drive(s):
    if not s:
        return current_drive + ':'
    try:
        # any replacement path?
        return drives[s.upper()]
    except KeyError:
        return s + ":"
        
# print to Windows printer
def line_print(printbuf, printer_name):        
    if printer_name == '' or printer_name=='default':
        printer_name = win32print.GetDefaultPrinter()
    handle = win32ui.CreateDC()
    handle.CreatePrinterDC(printer_name)
    handle.StartDoc("PC-BASIC 3_23 Document")
    handle.StartPage()
    # a4 = 210x297mm = 4950x7001px; Letter = 216x280mm=5091x6600px; 
    # 65 tall, 100 wide with 50x50 margins works for US letter
    # 96 wide works for A4 with 75 x-margin
    y, yinc = 50, 100
    lines = printbuf.split('\r\n')
    slines = []
    for l in lines:
        slines += [l[i:i+96] for i in range(0, len(l), 96)]
    for line in slines:
        handle.TextOut(75, y, line) 
        y += yinc
        if y > 6500:  
            y = 50
            handle.EndPage()
            handle.StartPage()
    handle.EndPage()
    handle.EndDoc()       
        
