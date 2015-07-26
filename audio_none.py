"""
PC-BASIC - audio_none.py
Null sound implementation

(c) 2013, 2014, 2015 Rob Hagemans
This file is released under the GNU GPL version 3.
"""

import datetime
import time
import threading
import Queue

import sound


##############################################################################
# interface

def init():
    """ Initialise sound system. """
    launch_thread()
    return True

def close():
    """ Clean up and exit sound system. """
    pass

def queue_length(voice):
    """ Number of unfinished sounds per voice. """
    # this is just sound.tone_queue[voice].unfinished_tasks but not part of API
    return sound.tone_queue[voice].qsize() + (next_tone[voice] is not None)



##############################################################################
# implementation

tick_s = 0.024

# sound generators for sounds not played yet
next_tone = [ None, None, None, None ]


def launch_thread():
    """ Launch consumer thread. """
    global thread
    thread = threading.Thread(target=consumer_thread)
    thread.daemon = True
    thread.start()

def consumer_thread():
    """ Audio signal queue consumer thread. """
    while True:
        drain_message_queue()
        empty = drain_tone_queue()
        # handle playing queues
        now = datetime.datetime.now()
        for voice in range(4):
            if next_tone[voice] is not None and now >= next_tone[voice]:
                next_tone[voice] = None
                sound.tone_queue[voice].task_done()
            empty = empty and not next_tone[voice]
        # do not hog cpu
        if empty:
            time.sleep(tick_s)

def drain_message_queue():
    """ Drain signal queue. """
    global next_tone
    while True:
        try:
            signal = sound.message_queue.get(False)
        except Queue.Empty:
            break
        if signal.event_type == sound.AUDIO_STOP:
            # stop all channels
            next_tone = [None, None, None, None]
        elif signal.event_type == sound.AUDIO_QUIT:
            # close thread
            return False
        elif signal.event_type == sound.AUDIO_PERSIST:
            # allow/disallow mixer to quit
            pass
        sound.message_queue.task_done()

def drain_tone_queue():
    """ Drain signal queue. """
    global next_tone
    empty = False
    while not empty:
        empty = True
        for voice, q in enumerate(sound.tone_queue):
            try:
                signal = q.get(False)
                empty = False
            except Queue.Empty:
                continue
            duration = 0
            if signal.event_type == sound.AUDIO_TONE:
                # enqueue a tone
                frequency, duration, fill, loop, voice, volume = signal.params
            elif signal.event_type == sound.AUDIO_NOISE:
                # enqueue a noise
                is_white, frequency, duration, fill, loop, volume = signal.params
            latest = next_tone[voice] or datetime.datetime.now()
            next_tone[voice] = latest + datetime.timedelta(seconds=duration)
    return empty
