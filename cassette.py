import wave
import math
import struct

token_to_ext = {0: 'D', 1:'M', 0xa0:'P', 0x20:'P', 0x40:'A', 0x80:'B'}
token_to_magic = {0: '', 1:'\xfd', 0xa0:'\xfe', 0x20:'\xfe', 0x40:'', 0x80:'\xff'}
magic_to_token = {'\xfd': 1, '\xfe': 0xa0, '\xff': 0x80}


#############################

class CassetteException(Exception):
    pass

class EOF(CassetteException):
    """ End-of-tape exception. """
    pass

class UnsupportedFormat(CassetteException):
    """ Format not supported. """
    def __str__(self):
        return "Cassette image format not supported."

class UnknownRecord(CassetteException):
    """ Unknown record type. """
    def __str__(self):
        return "Unknown record type."

class CRCError(CassetteException):
    """ CRC check failed. """
    def __init__(crc_read_dn, crc_dn, crc_read_up, crc_up):
        self.read_dn, self.dn, self.read_up, self.up = crc_read_dn, crc_dn, crc_read_up, crc_up

    def __str__(self):
        return "CRC check failed."

class PulseError(CassetteException):
    """ Incorrect pulse length."""
    def __str__(self):
        return "Incorrect pulse length."

#############################

def crc(data):
    """ Calculate 16-bit CRC-16-CCITT for data. """
    # see http://en.wikipedia.org/wiki/Computation_of_cyclic_redundancy_checks
    # for a lookup table version, see e.g. WAV2CAS v1.3 for Poisk PC. by Tronix (C) 2013
    # however, speed is not critical for this function
    rem = 0xffff
    for d in bytearray(data):
        rem ^= d << 8
        for _ in range(8):
            rem <<= 1
            if rem & 0x10000:
                rem ^= 0x1021
            rem &= 0xffff
    return rem ^ 0xffff

def word_le(word):
    """ Convert word to little-endian list of bytes. """
    hi, lo = divmod(word, 256)
    return [lo, hi]

#############################

def passthrough():
    """ Passthrough filter. """
    x = []
    while True:
        x = yield x

def simple_lowpass(sample_rate, cutoff_freq):
    """ Simple IIR low-pass filter. """
    # cf. http://en.wikipedia.org/wiki/Low-pass_filter#Simple_infinite_impulse_response_filter
    dt = 1./sample_rate
    RC = 1./(2.*math.pi*cutoff_freq)
    alpha = dt / (RC + dt)
    y = [0]
    while True:
        x = yield y[1:]
        x = [0] + x
        y = y[-1:] + [0]*len(x)
        for i in range(1, len(x)):
            y[i] = alpha * x[i] + (1-alpha) * y[i-1]

def butterworth(sample_rate, cutoff_freq):
    """ Second-order Butterworth low-pass filter. """
    # cf. src/arch/ibmpc/cassette.c (Hampa Hug) in PCE sources
    x, y = [0, 0], [0, 0]
    om = 1. / math.tan((math.pi * cutoff_freq) / sample_rate)
    rb0 = 1. / (om*om + om*math.sqrt(2.) + 1.)
    b1, b2 = 2.*(1.-om*om), (om*om-om*math.sqrt(2.)+1.)
    while True:
        inp = yield y[2:]
        x = x[-2:] + inp
        y = y[-2:] + [0]*len(inp)
        for i in range(2, len(x)):
            y[i] = (x[i] + 2*x[i-1] + x[i-2] - b1*y[i-1] - b2*y[i-2]) * rb0



#############################

class TapeReader(object):
    """ Cassette reading interface. """

    def read_byte(self):
        byte_dn, byte_up = 0, 0
        for i in xrange(8):
            bit_dn, bit_up = self.read_bit.next()
            if bit_dn == None or bit_up == None:
                return None, None
            byte_dn += bit_dn * 128 >> i
            byte_up += bit_up * 128 >> i
        return byte_dn, byte_up

    def read_leader(self):
        while True:
            while self.read_bit.next()[0] != 1:
                pass
            counter = 0
            start_frame = self.wav_pos
            while True:
                b = self.read_bit.next()[0]
                if b != 1:
                    break
                counter += 1
            # sync bit 0 has been read, check sync byte 0x16
            # at least 64*8 bits
            if b != None and counter >= 512:
                sync = self.read_byte()[0]
                if sync == 0x16:
                    return start_frame

    def read_block(self):
        count = 0
        data_dn, data_up = '', ''
        while True:
            if count == 256:
                bytes0 = self.read_byte()
                bytes1 = self.read_byte()
                crc_read_dn = bytes0[0] * 0x100 + bytes1[0]
                crc_read_up = bytes0[1] * 0x100 + bytes1[1]
                crc_dn = crc(data_dn)
                crc_up = crc(data_up)
                # if crc for either polarity matches, return that
                if crc_dn == crc_read_dn:
                    return data_dn
                if crc_up == crc_read_up:
                    return data_up
                raise CRCError(crc_read_dn, crc_dn, crc_read_up, crc_up)
            else:
                byte_dn, byte_up = self.read_byte()
                # if this is a header block, it must be 256 bytes
                if byte_dn == None or byte_up == None:
                    raise PulseError()
                data_dn += chr(byte_dn)
                data_up += chr(byte_up)
                count += 1

    def read_record(self, reclen):
        self.read_leader()
        record = ''
        self.block_num = 0
        byte_count = 0
        while byte_count < reclen or reclen == None:
            data = self.read_block()
            if not data:
                break
            record += data
            byte_count += len(data)
            if (reclen == None and
                    (data[:4] == '\xff\xff\xff\xff' or
                    (self.block_num == 0 and data[0] == '\xa5'))):
                break
            self.block_num += 1
        if reclen != None:
            return record[:reclen]
        return record

    def read_file(self):
        loc = self.wav_pos
        self.record_num = 0
        record = self.read_record(None)
        header = parse_header(record)
        print "[%d:%02d:%02d]" % self.hms(loc),
        print "File %d:" % self.file_num,
        if not header:
            # unknown record type
            print "Record of unknown type."
            return 'DATA.X%02x' % file_num, record
        else:
            file_trunk, file_token, file_bytes, seg, offs = header
            file_ext = token_to_ext[file_token]
            print '%s Found.' % (file_trunk + '.' + file_ext),
            print "%d bytes," % file_bytes,
            print "load address %04x:%04x." % (seg, offs)
            # for programs this is start address: cf to offset of next line in prgram
        file_name = file_trunk.rstrip() + '.' + file_ext + '%02x' % self.file_num
        data = token_to_magic[file_token]
        if file_token == 0x01:
            # bsave format: paste in 6-byte header for disk files
            data += ''.join(map(chr, word_le(seg)))
            data += ''.join(map(chr, word_le(offs)))
            data += ''.join(map(chr, word_le(file_bytes)))
        if file_token in (1, 0x80, 0x20, 0xa0):
            self.record_num += 1
            # bsave, tokenised and protected come in one multi-block record
            data += self.read_record(file_bytes)
        else:
            # ascii and data come as a sequence of one-block records
            # 256 bytes less 1 length byte. CRC trailer comes after 256-byte block
            while True:
                self.record_num += 1
                record = self.read_record(256)
                num_bytes = ord(record[0])
                record = record[1:]
                if num_bytes != 0:
                    record = record[:num_bytes-1]
                data += record
                if num_bytes != 0:
                    break
        # write EOF char
        data += '\x1a'
        return file_name, data

    def read_tape(self):
        # start parsing
        self.file_num = 0
        while True:
            try:
                file_name, data = self.read_file()
                with open(file_name, 'wb') as f:
                    f.write(str(bytearray(data)))
                self.file_num += 1
            except EOF:
                break

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()



class WAVReader(TapeReader):
    """ WAV-file cassette image reader. """

    #D
    def warning(self, msg):
        """ Print a warning message. """
        print "[%d:%02d:%02d]" % self.hms(self.wav_pos),
        print "File %d, record %d, block %d: %s" % (
                        self.file_num, self.record_num, self.block_num, msg)

    #D?
    def hms(self, loc):
        """ Return elapsed cassette time at given frame. """
        m, s = divmod(loc/self.framerate, 60)
        h, m = divmod(m, 60)
        return h, m, s


    def read_buffer(self):
        """ Fill buffer with frames and pre-process. """
        frame_buf = []
        frames = self.wav.readframes(self.buf_len)
        # convert bytes into ints (little-endian if 16 bit)
        try:
            frames2 = struct.unpack(self.conv_format, frames)
        except struct.error:
            if not frames:
                raise EOF
            frames2 = struct.unpack(self.conv_format[:len(frames)//self.sampwidth+1], frames)
        # sum frames over channels
        frames3 = map(sum, zip(*[iter(frames2)]*self.nchannels))
        frames4 = [ x-self.subtractor if x >= self.threshold else x for x in frames3 ]
        return self.lowpass.send(frames4)

    def gen_read_halfpulse(self):
        """ Generator to read a half-pulse and yield its length. """
        pos_in_frame = 0
        length = 0
        frame = False
        frame_buf = []
        while True:
            try:
                last = frame
                frame = frame_buf[pos_in_frame] < 0
                pos_in_frame += 1
                length += 1
            except IndexError:
                frame_buf = self.read_buffer()
                pos_in_frame = 0
            if last != frame:
                self.wav_pos += length
                yield length
                length = 0

    def read_pulse(self):
        """ Read a pulse and return length of down and up halves. """
        length_up = self.read_half.next()
        length_dn = self.read_half.next()
        return length_dn, length_up

    def gen_read_bit(self):
        """ Generator to yield the next bit. """
        while True:
            pulse = self.read_pulse()
            dn = 1 if pulse[0] >= self.length_cut else 0
            up = 1 if pulse[1] >= self.length_cut else 0
            if pulse[0] > 2*self.length_cut or pulse[1] > 2*self.length_cut:
                dn, up = None, None
            if pulse[0] < self.length_cut/2 or pulse[1] < self.length_cut/2:
                dn, up = None, None
            yield dn, up


    def __init__(self, filename):
        """ Initialise WAV-file for reading. """
        self.wav_pos = 0
        self.buf_len = 1024
        self.wav = wave.open(filename, 'rb')
        self.nchannels =  self.wav.getnchannels()
        self.sampwidth = self.wav.getsampwidth()
        self.framerate = self.wav.getframerate()
        nframes = self.wav.getnframes()
        if self.sampwidth == 1:
            self.threshold = 0
            self.subtractor = 128
        else:
            self.threshold = (1 << (self.sampwidth*8-1))*self.nchannels
            self.subtractor =  (1 << (self.sampwidth*8))*self.nchannels
        if self.sampwidth > 3:
            raise UnsupportedFormat()
        self.conv_format = '<' + {1:'B', 2:'h'}[self.sampwidth]*self.nchannels*self.buf_len
        # 1000 us for 1, 500 us for 0; threshould for half-pulse (500 us, 250 us)
        self.length_cut = 375*self.framerate/1000000
        self.halflength = (250*self.framerate/1000000, 500*self.framerate/1000000)
        # initialise generators
        self.lowpass = butterworth(self.framerate, 3000)
        self.lowpass.send(None)
        self.read_half = self.gen_read_halfpulse()
        self.read_bit = self.gen_read_bit()
        
    def close(self):
        """ Close WAV-file. """
        self.wav.close()


class CASReader(TapeReader):
    """ CAS-file cassette image reader. """

    def gen_read_bit(self):
        """ Generator to yield the next bit. """
        while True:
            cas_byte_read = 0
            cas_mask = 0
            cas_mask >>= 1
            if cas_mask <= 0:
                cas_byte_read = self.cas.read(1)
                if not cas_byte_read:
                    raise EOF
                cas_mask = 0x80
            bit = 0 if (ord(cas_byte_read) & cas_mask == 0) else 1
            yield bit, bit


    def __init__(self, filename):
        """ Initialise CAS-file for reading. """
        self.framerate = 1
        self.read_bit = self.gen_read_bit()
        self.cas = open(filename, 'rb')

    def close(self):
        """ Close CAS-file. """
        self.cas.close()



#######################################

def parse_header(record):
    if not record or record[0] != '\xa5':
        return None
    name = record[1:9]
    token = ord(record[9])
    nbytes = ord(record[10]) + ord(record[11]) * 0x100
    seg = ord(record[12]) + ord(record[13]) * 0x100
    offs = ord(record[14]) + ord(record[15]) * 0x100
    return name, token, nbytes, seg, offs

def header(name, token, nbytes, seg, offs):
    data = '\xa5'
    data += name[:8] + ' ' * (8-len(name))
    data += chr(token)
    # length
    data += ''.join(map(chr, word_le(nbytes)))
    # load address segment
    data += ''.join(map(chr, word_le(seg)))
    # load address offset
    data += ''.join(map(chr, word_le(offs)))
    # seems to end at 0x00, 0x01, then filled out with last char
    data += '\x00\x01'
    return data    

#######################################

class TapeWriter(object):
    """ Cassette recording interface. """

    def write_byte(self, byte):
        bits = [ 1 if (byte & ( 128 >> i) != 0) else 0 for i in range(8) ]
        for bit in bits:
            self.write_bit.send(bit)

    def write_intro(self):
        # write some noise to give the reader something to get started
        for b in bytearray('CAS1:'):
            self.write_byte(b)
        for _ in range(7):
            self.write_bit.send(0)
        self.write_pause(100)

    def write_leader(self):
        for _ in range(256):
            self.write_byte(0xff)
        self.write_bit.send(0)
        self.write_byte(0x16)

    def write_block(self, data):
        # fill out short blocks with last byte
        data += data[-1]*(256-len(data))
        for b in data:
            self.write_byte(ord(b))
        crc_word = crc(data)
        # crc is written big-endian
        lo, hi = word_le(crc_word)
        self.write_byte(hi)
        self.write_byte(lo)

    def write_record(self, data):
        self.write_leader()
        while len(data) > 0:
            self.write_block(data[:256])
            data = data[256:]
        self.write_byte(0xff)
        self.write_byte(0xff)
        self.write_byte(0xff)
        for b in (1,1,1,1,1,1,0):
            self.write_bit.send(b)
        # write 100 ms second pause to make clear separation between blocks
        self.write_pause(100)

    def write_file(self, name, token, data):
        if token == 0x01:
            # bsave 6-byte header is cut off (magic byte has been cut off before)
            seg = ord(data[0]) + ord(data[1])*0x100
            offs = ord(data[2]) + ord(data[3])*0x100
            length = ord(data[4]) + ord(data[5])*0x100
            data = data[6:6+length]
        elif token in (0x80, 0x20, 0xa0):
            # TODO: calculate seg and offs from program data, if program file
            # protected file? unprotect first 3 bytes & use values
            seg = 0x60
            offs = 0x81e
            bytes = len(data)
        else:
            # TODO: ASCII program files: length, seg, offset are untouched, remain that of the previous file recorded!
            seg, offs, bytes = 0, 0, 0
            # text files have CR line endings on tape, not CR LF
            # they should also get a NUL at the end
            data = data.replace('\r\n', '\r')
            data += '\0'
        self.write_record(header(name, token, bytes, seg, offs))
        if token in (1, 0x80, 0x20, 0xa0):
            # bsave, tokenised and protected come in one multi-block record
            self.write_record(data)
        else:
            # ascii and data come as a sequence of one-block records
            # 256 bytes less 1 length byte. CRC trailer comes after 256-byte block
            blocks, last = divmod(len(data), 255)
            for i in range(blocks):
                offset = i*255
                self.write_record('\0' + data[offset:offset+255])
            if last > 0:
                self.write_record(chr(last) + data[-last:])


    def write_tape(self, files):
        self.write_intro()
        # write files
        for file_name in files:
            name = file_name.split('.')[0][:8]
            print "Recording %s to cassette." % file_name
            with open(file_name, 'rb') as f:
                magic = f.read(1)
                data = f.read()
                # cut off EOF marker
                if data and data[-1] == '\x1a':
                    data = data[:-1]
                try:
                    token = magic_to_token[magic]
                except KeyError:
                    # could also be data file, need some other test (extension?)
                    token = 0x40
                    data = magic + data
                self.write_file(name, token, data)

    def __init__(self):
        self.write_bit = self.gen_write_bit()
        self.write_bit.send(None)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class WAVWriter(TapeWriter):
    """ WAV-file recording interface. """

    def write_pulse(self, half_length):
        self.wav.writeframes('\x00' * half_length + '\xff' * half_length)

    def write_pause(self, milliseconds):
        self.wav.writeframes('\x7f' * (milliseconds * self.framerate / 1000))

    def gen_write_bit(self):
        while True:
            bit = yield
            self.write_pulse(self.halflength[bit])

    def __init__(self, filename):
        self.framerate = 22050
        self.sampwidth = 1
        self.wav = wave.open(filename, 'wb')
        self.wav.setnchannels(1)
        self.wav.setsampwidth(1)
        self.wav.setframerate(self.framerate)
        self.halflength = [250*self.framerate/1000000, 500*self.framerate/1000000]
        TapeWriter.__init__(self)

    def close(self):
        self.wav.close()


class CASWriter(TapeWriter):
    """ CAS-file recording interface. """

    def write_pause(self, milliseconds):
        pass

    def gen_write_bit(self):
        count, byte = 0, 0
        while True:
            bit = yield
            byte = (byte << 1) | bit
            count += 1
            if cas_count >= 8:
                self.cas.write(chr(byte))
                count, byte = 0, 0

    def __init__(self, filename):
        #D, need this for hms calls
        self.framerate = 1
        self.cas = open(filename, 'wb')
        TapeWriter.__init__(self)

    def close(self):
        # ensure any buffered bits are written
        self.write_byte(0xff)
        self.cas.close()
    

