#
# PC-BASIC 3.23 - nosound.py
#
# Null sound implementation
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

music_foreground = True

def music_queue_length():
    return 0       
    
def beep():
    pass
    
def init_sound():
    return True
    
def stop_all_sound():
    pass
    
def play_sound(frequency, duration, fill=1, loop=False):
    pass
        
def check_sound():
    pass
    
def wait_music(wait_length=0, wait_last=True):
    pass
      
