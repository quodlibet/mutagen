Frame Base Classes
------------------


.. autoclass:: mutagen.id3.Frame()
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.BinaryFrame(data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.PairedTextFrame(encoding=<Encoding.UTF16: 1>, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TextFrame(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.UrlFrame(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.NumericPartTextFrame(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.NumericTextFrame(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TimeStampTextFrame(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.UrlFrameU(url='')
    :show-inheritance:
    :members:

ID3v2.3/4 Frames
----------------


.. autoclass:: mutagen.id3.AENC(owner='', preview_start=0, preview_length=0, data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.APIC(encoding=<Encoding.UTF16: 1>, mime='', type=<PictureType.COVER_FRONT: 3>, desc='', data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.ASPI(S=0, L=0, N=0, b=0, Fi=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.CHAP(element_id='', start_time=0, end_time=0, start_offset=4294967295, end_offset=4294967295, sub_frames={})
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.COMM(encoding=<Encoding.UTF16: 1>, lang='XXX', desc='', text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.COMR(encoding=<Encoding.UTF16: 1>, price='', valid_until='19700101', contact='', format=0, seller='', desc='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.CTOC(element_id='', flags=<0: 0>, child_element_ids=[], sub_frames={})
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.ENCR(owner='', method=128, data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.EQU2(method=0, desc='', adjustments=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.ETCO(format=1, events=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.GEOB(encoding=<Encoding.UTF16: 1>, mime='', filename='', desc='', data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.GRID(owner='', group=128, data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.GRP1(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.IPLS(encoding=<Encoding.UTF16: 1>, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.LINK(frameid='XXXX', url='', data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.MCDI(data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.MLLT(frames=0, bytes=0, milliseconds=0, bits_for_bytes=0, bits_for_milliseconds=0, data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.MVIN(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.MVNM(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.OWNE(encoding=<Encoding.UTF16: 1>, price='', date='19700101', seller='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.PCNT(count=0)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.PCST(value=0)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.POPM(email='', rating=0)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.POSS(format=1, position=0)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.PRIV(owner='', data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.RBUF(size=0)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.RVA2(desc='', channel=1, gain=1, peak=1)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.RVAD(adjustments=[0, 0])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.RVRB(left=0, right=0, bounce_left=0, bounce_right=0, feedback_ltl=0, feedback_ltr=0, feedback_rtr=0, feedback_rtl=0, premix_ltr=0, premix_rtl=0)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SEEK(offset=0)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SIGN(group=128, sig=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SYLT(encoding=<Encoding.UTF16: 1>, lang='XXX', format=1, type=0, desc='', text='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SYTC(format=1, data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TALB(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TBPM(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCAT(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCMP(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCOM(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCON(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCOP(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDAT(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDEN(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDES(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDLY(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDOR(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDRC(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDRL(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDTG(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TENC(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TEXT(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TFLT(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TGID(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIME(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIPL(encoding=<Encoding.UTF16: 1>, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIT1(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIT2(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIT3(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TKEY(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TKWD(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TLAN(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TLEN(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TMCL(encoding=<Encoding.UTF16: 1>, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TMED(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TMOO(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOAL(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOFN(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOLY(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOPE(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TORY(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOWN(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPE1(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPE2(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPE3(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPE4(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPOS(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPRO(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPUB(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRCK(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRDA(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRSN(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRSO(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSIZ(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSO2(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSOA(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSOC(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSOP(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSOT(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSRC(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSSE(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSST(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TXXX(encoding=<Encoding.UTF16: 1>, desc='', text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TYER(encoding=<Encoding.UTF16: 1>, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.UFID(owner='', data=b'')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.USER(encoding=<Encoding.UTF16: 1>, lang='XXX', text='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.USLT(encoding=<Encoding.UTF16: 1>, lang='XXX', desc='', text='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WCOM(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WCOP(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WFED(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WOAF(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WOAR(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WOAS(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WORS(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WPAY(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WPUB(url='')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WXXX(encoding=<Encoding.UTF16: 1>, desc='', url='')
    :show-inheritance:
    :members:

