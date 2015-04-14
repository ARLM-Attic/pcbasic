"""
PC-BASIC 3.23 - sound.py
Sound handling

(c) 2013, 2014 Rob Hagemans 
This file is released under the GNU GPL version 3. 
"""

import Queue
import threading
import time

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import error
import config
import state
import util
import draw_and_play
import representation
import vartypes
import backend

# audio plugin
audio = None 

# sound capabilities - '', 'pcjr' or 'tandy'
pcjr_sound = ''

# base frequency for noise source
base_freq = 3579545./1024.

# 12-tone equal temperament
# C, C#, D, D#, E, F, F#, G, G#, A, A#, B
note_freq = [ 440.*2**((i-33.)/12.) for i in range(84) ]
notes = {   'C':0, 'C#':1, 'D-':1, 'D':2, 'D#':3, 'E-':3, 'E':4, 'F':5, 'F#':6, 
            'G-':6, 'G':7, 'G#':8, 'A-':8, 'A':9, 'A#':10, 'B-':10, 'B':11 }



class AudioEvent(object):
    """ Signal object for audio queue. """
    
    def __init__(self, event_type, params=None):
        """ Create signal. """
        self.event_type = event_type
        self.params = params


# audio queue signals
AUDIO_TONE = 0
AUDIO_STOP = 1
AUDIO_NOISE = 2
AUDIO_SYNC = 3
AUDIO_QUIT = 4
AUDIO_PERSIST = 6



def prepare():
    """ Prepare the audio subsystem. """
    global pcjr_sound
    # pcjr/tandy sound
    if config.options['syntax'] in ('pcjr', 'tandy'):
        pcjr_sound = config.options['syntax']
    # initialise sound queue
    state.console_state.sound = Sound()
    # tandy has SOUND ON by default, pcjr has it OFF
    state.console_state.sound.sound_on = (pcjr_sound == 'tandy')
    # pc-speaker on/off; (not implemented; not sure whether should be on)
    state.console_state.sound.beep_on = True

def init():
    """ Initialise the audio backend. """
    global audio
    if not audio or not audio.init():
        return False
    state.console_state.sound.launch_thread()
    return True


class PlayState(object):
    """ State variables of the PLAY command. """
    
    def __init__(self):
        """ Initialise play state. """
        self.octave = 4
        self.speed = 7./8.
        self.tempo = 2. # 2*0.25 =0 .5 seconds per quarter note
        self.length = 0.25
        self.volume = 15


class Sound(object):
    """ Sound queue manipulations. """

    def __init__(self):
        """ Initialise sound queue. """
        self.thread_queue = [Queue.Queue(), Queue.Queue(), Queue.Queue(), Queue.Queue()]
        self.thread = None
        
        # Tandy/PCjr noise generator
        # frequency for noise sources
        self.noise_freq = [base_freq / v for v in [1., 2., 4., 1., 1., 2., 4., 1.]]
        self.noise_freq[3] = 0.
        self.noise_freq[7] = 0.
        # Tandy/PCjr SOUND ON and BEEP ON
        self.sound_on = False
        self.beep_on = True
        self.reset()

    def close(self):
        """ Close sound queue at exit. """
        if self.thread and self.thread.is_alive() and self.thread_queue:
            # signal quit and wait for thread to finish
            self.thread_queue[0].put(AudioEvent(AUDIO_QUIT))
            self.thread.join()

    def __getstate__(self):
        """ Return picklable state. """
        # copy object dict and remove un-picklable Queues
        d = dict(self.__dict__)
        d['thread_queue'] = None
        d['thread'] = None
        return d

    def __setstate__(self, d):
        """ Rebuild from pickled state. """
        self.__dict__.update(d)
        self.thread_queue = [Queue.Queue(), Queue.Queue(), Queue.Queue(), Queue.Queue()]
        
    def reset(self):
        """ Reset PLAY state (CLEAR). """
        # music foreground (MF) mode        
        self.foreground = True
        # reset all PLAY state
        self.play_state = [ PlayState(), PlayState(), PlayState() ]

    def beep(self):
        """ Play the BEEP sound. """
        self.play_sound(800, 0.25)

    def play_sound(self, frequency, duration, fill=1, loop=False, voice=0, volume=15):
        """ Play a sound on the tone generator. """
        if frequency < 0:
            frequency = 0
        if ((pcjr_sound == 'tandy' or 
                (pcjr_sound == 'pcjr' and self.sound_on)) and
                frequency < 110. and frequency != 0):
            # pcjr, tandy play low frequencies as 110Hz
            frequency = 110.
        tone = AudioEvent(AUDIO_TONE, (frequency, duration, fill, loop, voice, volume))
        self.thread_queue[voice].put(tone)
        if voice == 2:
            # reset linked noise frequencies
            # /2 because we're using a 0x4000 rotation rather than 0x8000
            self.noise_freq[3] = frequency/2.
            self.noise_freq[7] = frequency/2.
        # at most 16 notes in the sound queue (not 32 as the guide says!)
        self.wait_music(15)    

    def wait_music(self, wait_length=0):
        """ Wait until a given number of notes are left on the queue. """
        while (self.queue_length(0) > wait_length or
                self.queue_length(1) > wait_length or
                self.queue_length(2) > wait_length):
            backend.wait()

    def wait_all_music(self):
        """ Wait until all music (not noise) has finished playing. """
        while (audio.busy() or audio.queue_length(0) or audio.queue_length(1) or audio.queue_length(2) or
                self.thread_queue[0].qsize() or self.thread_queue[1].qsize() or self.thread_queue[2].qsize()):
            backend.wait()

    def stop_all_sound(self):
        """ Terminate all sounds immediately. """
        for q in self.thread_queue:
            while not q.empty():
                try:
                    q.get(False)
                except Empty:
                    continue
                q.task_done()
        for q in self.thread_queue:
            q.put(AudioEvent(AUDIO_STOP))
        
    def play_noise(self, source, volume, duration, loop=False):
        """ Play a sound on the noise generator. """
        frequency = self.noise_freq[source]
        noise = AudioEvent(AUDIO_NOISE, (source > 3, frequency, duration, 1, loop, volume)) 
        self.thread_queue[3].put(noise)
        # don't wait for noise

    def queue_length(self, voice=0):
        """ Return the number of notes in the queue. """
        # top of sound_queue is currently playing
        return max(0, self.thread_queue[voice].qsize() + audio.queue_length(voice)-1)

    def persist(self, flag):
        """ Set mixer persistence flag (runmode). """
        self.thread_queue[0].put(AudioEvent(AUDIO_PERSIST, flag))
        
    def launch_thread(self):
        """ Launch consumer thread. """
        self.thread = threading.Thread(target=self.check_queue)
        self.thread.daemon = True
        self.thread.start()
        
    def check_queue(self):
        """ Audio queue consumer thread. """
        empty = True        
        while True:
            for i, q in enumerate(self.thread_queue):
                try:
                    signal = q.get(False)
                except Queue.Empty:
                    empty = empty and True
                    continue
                if signal.event_type == AUDIO_TONE:
                    audio.play_sound(*signal.params)
                elif signal.event_type == AUDIO_STOP:
                    audio.stop_all_sound()
                elif signal.event_type == AUDIO_NOISE:
                    audio.play_noise(*signal.params)
                elif signal.event_type == AUDIO_QUIT:
                    # close thread
                    return
                elif signal.event_type == AUDIO_PERSIST:
                    audio.persist = signal.params
                q.task_done()
            # handle playing queues
            audio.check_sound()
            # check if mixer can be quit
            audio.check_quit()
            # do not hog cpu
            if empty:
                time.sleep(0.024)

    ### PLAY statement

    def play(self, mml_list):
        """ Parse a list of Music Macro Language strings. """
        gmls_list = []
        for mml in mml_list:
            gmls = StringIO()
            # don't convert to uppercase as VARPTR$ elements are case sensitive
            gmls.write(str(mml))
            gmls.seek(0)
            gmls_list.append(gmls)
        next_oct = 0
        total_time = [0, 0, 0, 0]
        voices = range(3)
        total_time = [0, 0, 0, 0]
        while True:
            if not voices:
                break
            for voice in voices:
                vstate = self.play_state[voice]
                gmls = gmls_list[voice]
                c = util.skip_read(gmls, draw_and_play.ml_whitepace).upper()
                if c == '':
                    voices.remove(voice)
                    continue
                elif c == ';':
                    continue
                elif c == 'X':
                    # execute substring
                    sub = draw_and_play.ml_parse_string(gmls)
                    pos = gmls.tell()
                    rest = gmls.read()
                    gmls.truncate(pos)
                    gmls.write(str(sub))
                    gmls.write(rest)
                    gmls.seek(pos)
                elif c == 'N':
                    note = draw_and_play.ml_parse_number(gmls)
                    dur = vstate.length
                    c = util.skip(gmls, draw_and_play.ml_whitepace).upper()
                    if c == '.':
                        gmls.read(1)
                        dur *= 1.5
                    if note > 0 and note <= 84:
                        self.play_sound(note_freq[note-1], dur*vstate.tempo, 
                                         vstate.speed, volume=vstate.volume,
                                         voice=voice)
                        total_time[voice] += dur*vstate.tempo
                    elif note == 0:
                        self.play_sound(0, dur*vstate.tempo, vstate.speed,
                                        volume=0, voice=voice)
                        total_time[voice] += dur*vstate.tempo
                elif c == 'L':
                    vstate.length = 1./draw_and_play.ml_parse_number(gmls)    
                elif c == 'T':
                    vstate.tempo = 240./draw_and_play.ml_parse_number(gmls)    
                elif c == 'O':
                    vstate.octave = min(6, max(0, draw_and_play.ml_parse_number(gmls)))
                elif c == '>':
                    vstate.octave += 1
                    if vstate.octave > 6:
                        vstate.octave = 6
                elif c == '<':
                    vstate.octave -= 1
                    if vstate.octave < 0:
                        vstate.octave = 0
                elif c in ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'P'):
                    note = c
                    dur = vstate.length
                    while True:    
                        c = util.skip(gmls, draw_and_play.ml_whitepace).upper()
                        if c == '.':
                            gmls.read(1)
                            dur *= 1.5
                        elif c in representation.ascii_digits:
                            numstr = ''
                            while c in representation.ascii_digits:
                                gmls.read(1)
                                numstr += c 
                                c = util.skip(gmls, draw_and_play.ml_whitepace) 
                            length = vartypes.pass_int_unpack(representation.str_to_value_keep(('$', numstr)))
                            dur = 1. / float(length)
                        elif c in ('#', '+'):
                            gmls.read(1)
                            note += '#'
                        elif c == '-':
                            gmls.read(1)
                            note += '-'
                        else:
                            break                    
                    if note == 'P':
                        self.play_sound(0, dur * vstate.tempo, vstate.speed,
                                        volume=vstate.volume, voice=voice)
                        total_time[voice] += dur*vstate.tempo
                    else:
                        try:
                            self.play_sound(
                                note_freq[(vstate.octave+next_oct)*12 + notes[note]], 
                                dur * vstate.tempo, vstate.speed, 
                                volume=vstate.volume, voice=voice)
                            total_time[voice] += dur*vstate.tempo
                        except KeyError:
                            raise error.RunError(5)
                    next_oct = 0
                elif c == 'M':
                    c = util.skip_read(gmls, draw_and_play.ml_whitepace).upper()
                    if c == 'N':        
                        vstate.speed = 7./8.
                    elif c == 'L':      
                        vstate.speed = 1.
                    elif c == 'S':      
                        vstate.speed = 3./4.        
                    elif c == 'F':      
                        self.foreground = True
                    elif c == 'B':      
                        self.foreground = False
                    else:
                        raise error.RunError(5)    
                elif c == 'V' and (pcjr_sound == 'tandy' or 
                                    (pcjr_sound == 'pcjr' and self.sound_on)): 
                    vstate.volume = min(15, 
                                    max(0, draw_and_play.ml_parse_number(gmls)))
                else:
                    raise error.RunError(5)    
        max_time = max(total_time)
        for voice in range(3):
            if total_time[voice] < max_time:
                self.play_sound(0, max_time - total_time[voice], 1, 0, voice)
        if self.foreground:
            self.wait_all_music()



###############################################################################
         
prepare()

