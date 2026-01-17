# Copyright (C) 2005  Michael Urman
#               2006  Lukas Lalinsky
#               2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""ID3v2 reading and writing.

This is based off of the following references:

* http://id3.org/id3v2.4.0-structure
* http://id3.org/id3v2.4.0-frames
* http://id3.org/id3v2.3.0
* http://id3.org/id3v2-00
* http://id3.org/ID3v1

Its largest deviation from the above (versions 2.3 and 2.2) is that it
will not interpret the / characters as a separator, and will almost
always accept null separators to generate multi-valued text frames.

Because ID3 frame structure differs between frame types, each frame is
implemented as a different class (e.g. TIT2 as mutagen.id3.TIT2). Each
frame's documentation contains a list of its attributes.

Since this file's documentation is a little unwieldy, you are probably
interested in the :class:`ID3` class to start with.
"""

from ._file import ID3, ID3FileType, delete, ID3v1SaveOptions as ID3v1SaveOptions
from ._specs import Encoding as Encoding, PictureType as PictureType, \
    CTOCFlags as CTOCFlags, ID3TimeStamp as ID3TimeStamp
from ._frames import Frames, Frames_2_2 as Frames_2_2, Frame as Frame, \
    TextFrame as TextFrame, UrlFrame as UrlFrame, UrlFrameU as UrlFrameU, \
    TimeStampTextFrame as TimeStampTextFrame, BinaryFrame as BinaryFrame, \
    NumericPartTextFrame as NumericPartTextFrame, \
    NumericTextFrame as NumericTextFrame, PairedTextFrame as PairedTextFrame
from ._util import ID3NoHeaderError as ID3NoHeaderError, error as error, \
    ID3UnsupportedVersionError as ID3UnsupportedVersionError
from ._id3v1 import ParseID3v1 as ParseID3v1, MakeID3v1 as MakeID3v1
from ._tags import ID3Tags as ID3Tags
from ._frames import AENC as AENC, APIC as APIC, ASPI as ASPI, BUF as BUF, \
    CHAP as CHAP, CNT as CNT, COM as COM, COMM as COMM, COMR as COMR, \
    CRA as CRA, CRM as CRM, CTOC as CTOC, ENCR as ENCR, EQU2 as EQU2, \
    ETC as ETC, ETCO as ETCO, GEO as GEO, GEOB as GEOB, GP1 as GP1, \
    GRID as GRID, GRP1 as GRP1, IPL as IPL, IPLS as IPLS, LINK as LINK, \
    LNK as LNK, MCDI as MCDI, MCI as MCI, MLL as MLL, MLLT as MLLT, MVI as MVI, \
    MVIN as MVIN, MVN as MVN, MVNM as MVNM, OWNE as OWNE, PCNT as PCNT, \
    PCST as PCST, PIC as PIC, POP as POP, POPM as POPM, \
    POSS as POSS, PRIV as PRIV, RBUF as RBUF, REV as REV, RVA as RVA, RVA2 as RVA2, \
    RVAD as RVAD, RVRB as RVRB, SEEK as SEEK, SIGN as SIGN, SLT as SLT, STC as STC, \
    SYLT as SYLT, SYTC as SYTC, TAL as TAL, TALB as TALB, TBP as TBP, TBPM as TBPM, \
    TCAT as TCAT, TCM as TCM, TCMP as TCMP, TCO as TCO, TCOM as TCOM, TCON as TCON, \
    TCOP as TCOP, TCP as TCP, TCR as TCR, TDA as TDA, TDAT as TDAT, TDEN as TDEN, \
    TDES as TDES, TDLY as TDLY, TDOR as TDOR, TDRC as TDRC, TDRL as TDRL, \
    TDTG as TDTG, TDY as TDY, TEN as TEN, TENC as TENC, TEXT as TEXT, TFLT as TFLT, \
    TFT as TFT, TGID as TGID, TIM as TIM, TIME as TIME, TIPL as TIPL, TIT1 as TIT1, \
    TIT2 as TIT2, TIT3 as TIT3, TKE as TKE, TKEY as TKEY, TKWD as TKWD, TLA as TLA, \
    TLAN as TLAN, TLE as TLE, TLEN as TLEN, TMCL as TMCL, TMED as TMED, \
    TMOO as TMOO, TMT as TMT, TOA as TOA, TOAL as TOAL, TOF as TOF, TOFN as TOFN, \
    TOL as TOL, TOLY as TOLY, TOPE as TOPE, TOR as TOR, TORY as TORY, TOT as TOT, \
    TOWN as TOWN, TP1 as TP1, TP2 as TP2, TP3 as TP3, TP4 as TP4, TPA as TPA, \
    TPB as TPB, TPE1 as TPE1, TPE2 as TPE2, TPE3 as TPE3, TPE4 as TPE4, \
    TPOS as TPOS, TPRO as TPRO, TPUB as TPUB, TRC as TRC, TRCK as TRCK, TRD as TRD, \
    TRDA as TRDA, TRK as TRK, TRSN as TRSN, TRSO as TRSO, TS2 as TS2, TSA as TSA, \
    TSC as TSC, TSI as TSI, TSIZ as TSIZ, TSO2 as TSO2, TSOA as TSOA, TSOC as TSOC, \
    TSOP as TSOP, TSOT as TSOT, TSP as TSP, TSRC as TSRC, TSS as TSS, TSSE as TSSE, \
    TSST as TSST, TST as TST, TT1 as TT1, TT2 as TT2, TT3 as TT3, TXT as TXT, \
    TXX as TXX, TXXX as TXXX, TYE as TYE, TYER as TYER, UFI as UFI, UFID as UFID, \
    ULT as ULT, USER as USER, USLT as USLT, WAF as WAF, WAR as WAR, WAS as WAS, \
    WCM as WCM, WCOM as WCOM, WCOP as WCOP, WCP as WCP, WFED as WFED, WOAF as WOAF, \
    WOAR as WOAR, WOAS as WOAS, WORS as WORS, WPAY as WPAY, WPB as WPB, WPUB as WPUB, \
    WXX as WXX, WXXX as WXXX

# deprecated
from ._util import ID3EncryptionUnsupportedError as ID3EncryptionUnsupportedError, \
    ID3JunkFrameError as ID3JunkFrameError, ID3BadUnsynchData as ID3BadUnsynchData, \
    ID3BadCompressedData as ID3BadCompressedData, ID3TagError as ID3TagError, \
    ID3Warning as ID3Warning, BitPaddedInt as _BitPaddedIntForPicard

# support open(filename) as interface
Open = ID3


# Workaround for http://tickets.musicbrainz.org/browse/PICARD-833
class _DummySpecForPicard(object):
    write = None

EncodedTextSpec = MultiSpec = _DummySpecForPicard
BitPaddedInt = _BitPaddedIntForPicard


__all__ = ['ID3', 'ID3FileType', 'Frames', 'Open', 'delete']
