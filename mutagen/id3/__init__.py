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

from ._file import ID3, ID3FileType, delete
from ._file import ID3v1SaveOptions as ID3v1SaveOptions
from ._frames import AENC as AENC
from ._frames import APIC as APIC
from ._frames import ASPI as ASPI
from ._frames import BUF as BUF
from ._frames import CHAP as CHAP
from ._frames import CNT as CNT
from ._frames import COM as COM
from ._frames import COMM as COMM
from ._frames import COMR as COMR
from ._frames import CRA as CRA
from ._frames import CRM as CRM
from ._frames import CTOC as CTOC
from ._frames import ENCR as ENCR
from ._frames import EQU2 as EQU2
from ._frames import ETC as ETC
from ._frames import ETCO as ETCO
from ._frames import GEO as GEO
from ._frames import GEOB as GEOB
from ._frames import GP1 as GP1
from ._frames import GRID as GRID
from ._frames import GRP1 as GRP1
from ._frames import IPL as IPL
from ._frames import IPLS as IPLS
from ._frames import LINK as LINK
from ._frames import LNK as LNK
from ._frames import MCDI as MCDI
from ._frames import MCI as MCI
from ._frames import MLL as MLL
from ._frames import MLLT as MLLT
from ._frames import MVI as MVI
from ._frames import MVIN as MVIN
from ._frames import MVN as MVN
from ._frames import MVNM as MVNM
from ._frames import OWNE as OWNE
from ._frames import PCNT as PCNT
from ._frames import PCST as PCST
from ._frames import PIC as PIC
from ._frames import POP as POP
from ._frames import POPM as POPM
from ._frames import POSS as POSS
from ._frames import PRIV as PRIV
from ._frames import RBUF as RBUF
from ._frames import REV as REV
from ._frames import RVA as RVA
from ._frames import RVA2 as RVA2
from ._frames import RVAD as RVAD
from ._frames import RVRB as RVRB
from ._frames import SEEK as SEEK
from ._frames import SIGN as SIGN
from ._frames import SLT as SLT
from ._frames import STC as STC
from ._frames import SYLT as SYLT
from ._frames import SYTC as SYTC
from ._frames import TAL as TAL
from ._frames import TALB as TALB
from ._frames import TBP as TBP
from ._frames import TBPM as TBPM
from ._frames import TCAT as TCAT
from ._frames import TCM as TCM
from ._frames import TCMP as TCMP
from ._frames import TCO as TCO
from ._frames import TCOM as TCOM
from ._frames import TCON as TCON
from ._frames import TCOP as TCOP
from ._frames import TCP as TCP
from ._frames import TCR as TCR
from ._frames import TDA as TDA
from ._frames import TDAT as TDAT
from ._frames import TDEN as TDEN
from ._frames import TDES as TDES
from ._frames import TDLY as TDLY
from ._frames import TDOR as TDOR
from ._frames import TDRC as TDRC
from ._frames import TDRL as TDRL
from ._frames import TDTG as TDTG
from ._frames import TDY as TDY
from ._frames import TEN as TEN
from ._frames import TENC as TENC
from ._frames import TEXT as TEXT
from ._frames import TFLT as TFLT
from ._frames import TFT as TFT
from ._frames import TGID as TGID
from ._frames import TIM as TIM
from ._frames import TIME as TIME
from ._frames import TIPL as TIPL
from ._frames import TIT1 as TIT1
from ._frames import TIT2 as TIT2
from ._frames import TIT3 as TIT3
from ._frames import TKE as TKE
from ._frames import TKEY as TKEY
from ._frames import TKWD as TKWD
from ._frames import TLA as TLA
from ._frames import TLAN as TLAN
from ._frames import TLE as TLE
from ._frames import TLEN as TLEN
from ._frames import TMCL as TMCL
from ._frames import TMED as TMED
from ._frames import TMOO as TMOO
from ._frames import TMT as TMT
from ._frames import TOA as TOA
from ._frames import TOAL as TOAL
from ._frames import TOF as TOF
from ._frames import TOFN as TOFN
from ._frames import TOL as TOL
from ._frames import TOLY as TOLY
from ._frames import TOPE as TOPE
from ._frames import TOR as TOR
from ._frames import TORY as TORY
from ._frames import TOT as TOT
from ._frames import TOWN as TOWN
from ._frames import TP1 as TP1
from ._frames import TP2 as TP2
from ._frames import TP3 as TP3
from ._frames import TP4 as TP4
from ._frames import TPA as TPA
from ._frames import TPB as TPB
from ._frames import TPE1 as TPE1
from ._frames import TPE2 as TPE2
from ._frames import TPE3 as TPE3
from ._frames import TPE4 as TPE4
from ._frames import TPOS as TPOS
from ._frames import TPRO as TPRO
from ._frames import TPUB as TPUB
from ._frames import TRC as TRC
from ._frames import TRCK as TRCK
from ._frames import TRD as TRD
from ._frames import TRDA as TRDA
from ._frames import TRK as TRK
from ._frames import TRSN as TRSN
from ._frames import TRSO as TRSO
from ._frames import TS2 as TS2
from ._frames import TSA as TSA
from ._frames import TSC as TSC
from ._frames import TSI as TSI
from ._frames import TSIZ as TSIZ
from ._frames import TSO2 as TSO2
from ._frames import TSOA as TSOA
from ._frames import TSOC as TSOC
from ._frames import TSOP as TSOP
from ._frames import TSOT as TSOT
from ._frames import TSP as TSP
from ._frames import TSRC as TSRC
from ._frames import TSS as TSS
from ._frames import TSSE as TSSE
from ._frames import TSST as TSST
from ._frames import TST as TST
from ._frames import TT1 as TT1
from ._frames import TT2 as TT2
from ._frames import TT3 as TT3
from ._frames import TXT as TXT
from ._frames import TXX as TXX
from ._frames import TXXX as TXXX
from ._frames import TYE as TYE
from ._frames import TYER as TYER
from ._frames import UFI as UFI
from ._frames import UFID as UFID
from ._frames import ULT as ULT
from ._frames import USER as USER
from ._frames import USLT as USLT
from ._frames import WAF as WAF
from ._frames import WAR as WAR
from ._frames import WAS as WAS
from ._frames import WCM as WCM
from ._frames import WCOM as WCOM
from ._frames import WCOP as WCOP
from ._frames import WCP as WCP
from ._frames import WFED as WFED
from ._frames import WOAF as WOAF
from ._frames import WOAR as WOAR
from ._frames import WOAS as WOAS
from ._frames import WORS as WORS
from ._frames import WPAY as WPAY
from ._frames import WPB as WPB
from ._frames import WPUB as WPUB
from ._frames import WXX as WXX
from ._frames import WXXX as WXXX
from ._frames import BinaryFrame as BinaryFrame
from ._frames import Frame as Frame
from ._frames import Frames
from ._frames import Frames_2_2 as Frames_2_2
from ._frames import NumericPartTextFrame as NumericPartTextFrame
from ._frames import NumericTextFrame as NumericTextFrame
from ._frames import PairedTextFrame as PairedTextFrame
from ._frames import TextFrame as TextFrame
from ._frames import TimeStampTextFrame as TimeStampTextFrame
from ._frames import UrlFrame as UrlFrame
from ._frames import UrlFrameU as UrlFrameU
from ._id3v1 import MakeID3v1 as MakeID3v1
from ._id3v1 import ParseID3v1 as ParseID3v1
from ._specs import CTOCFlags as CTOCFlags
from ._specs import Encoding as Encoding
from ._specs import ID3TimeStamp as ID3TimeStamp
from ._specs import PictureType as PictureType
from ._tags import ID3Tags as ID3Tags
from ._util import BitPaddedInt as _BitPaddedIntForPicard
from ._util import ID3BadCompressedData as ID3BadCompressedData
from ._util import ID3BadUnsynchData as ID3BadUnsynchData

# deprecated
from ._util import ID3EncryptionUnsupportedError as ID3EncryptionUnsupportedError
from ._util import ID3JunkFrameError as ID3JunkFrameError
from ._util import ID3NoHeaderError as ID3NoHeaderError
from ._util import ID3TagError as ID3TagError
from ._util import ID3UnsupportedVersionError as ID3UnsupportedVersionError
from ._util import ID3Warning as ID3Warning
from ._util import error as error

# support open(filename) as interface
Open = ID3


# Workaround for http://tickets.musicbrainz.org/browse/PICARD-833
class _DummySpecForPicard:
    write = None

EncodedTextSpec = MultiSpec = _DummySpecForPicard
BitPaddedInt = _BitPaddedIntForPicard


__all__ = ['ID3', 'ID3FileType', 'Frames', 'Open', 'delete']
