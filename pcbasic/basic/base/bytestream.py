"""
PC-BASIC - bytestream.py
BytesIO extension with externally provided buffer

(c) 2013--2018 Rob Hagemans
This file is released under the GNU GPL version 3 or later.
"""

from _pyio import BytesIO


class ByteStream(BytesIO):
    """Extension of BytesIO with accessible buffer."""

    def __init__(self, initial_bytes):
        """Create new ByteStream."""
        BytesIO.__init__(self)
        assert isinstance(initial_bytes, bytearray)
        # use the actual object as a buffer, do not copy
        self._buffer = initial_bytes
