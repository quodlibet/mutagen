Frame Base Classes
------------------


.. autoclass:: mutagen.id3.Frame()
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.BinaryFrame(data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.FrameOpt()
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.PairedTextFrame(encoding=None, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TextFrame(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.UrlFrame(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.NumericPartTextFrame(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.NumericTextFrame(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TimeStampTextFrame(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.UrlFrameU(url=u'None')
    :show-inheritance:
    :members:

ID3v2.3/4 Frames
----------------


.. autoclass:: mutagen.id3.AENC(owner=u'None', preview_start=None, preview_length=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.APIC(encoding=None, mime=u'None', type=None, desc=u'None', data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.ASPI(S=None, L=None, N=None, b=None, Fi=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.COMM(encoding=None, lang=None, desc=u'None', text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.COMR(encoding=None, price=u'None', valid_until=None, contact=u'None', format=None, seller=u'None', desc=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.ENCR(owner=u'None', method=None, data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.EQU2(method=None, desc=u'None', adjustments=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.ETCO(format=None, events=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.GEOB(encoding=None, mime=u'None', filename=u'None', desc=u'None', data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.GRID(owner=u'None', group=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.IPLS(encoding=None, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.LINK(frameid=None, url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.MCDI(data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.MLLT(frames=None, bytes=None, milliseconds=None, bits_for_bytes=None, bits_for_milliseconds=None, data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.OWNE(encoding=None, price=u'None', date=None, seller=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.PCNT(count=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.POPM(email=u'None', rating=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.POSS(format=None, position=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.PRIV(owner=u'None', data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.RBUF(size=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.RVA2(desc=u'None', channel=None, gain=None, peak=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.RVRB(left=None, right=None, bounce_left=None, bounce_right=None, feedback_ltl=None, feedback_ltr=None, feedback_rtr=None, feedback_rtl=None, premix_ltr=None, premix_rtl=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SEEK(offset=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SIGN(group=None, sig='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SYLT(encoding=None, lang=None, format=None, type=None, desc=u'None', text=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SYTC(format=None, data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TALB(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TBPM(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCMP(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCOM(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCON(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCOP(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDAT(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDEN(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDES(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDLY(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDOR(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDRC(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDRL(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDTG(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TENC(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TEXT(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TFLT(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TGID(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIME(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIPL(encoding=None, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIT1(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIT2(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIT3(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TKEY(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TLAN(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TLEN(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TMCL(encoding=None, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TMED(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TMOO(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOAL(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOFN(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOLY(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOPE(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TORY(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOWN(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPE1(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPE2(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPE3(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPE4(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPOS(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPRO(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPUB(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRCK(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRDA(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRSN(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRSO(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSIZ(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSO2(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSOA(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSOC(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSOP(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSOT(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSRC(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSSE(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSST(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TXXX(encoding=None, desc=u'None', text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TYER(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.UFID(owner=u'None', data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.USER(encoding=None, lang=None, text=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.USLT(encoding=None, lang=None, desc=u'None', text=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WCOM(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WCOP(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WFED(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WOAF(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WOAR(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WOAS(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WORS(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WPAY(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WPUB(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WXXX(encoding=None, desc=u'None', url=u'None')
    :show-inheritance:
    :members:

ID3v2.2 Frames
--------------


.. autoclass:: mutagen.id3.BUF(size=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.CNT(count=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.COM(encoding=None, lang=None, desc=u'None', text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.CRA(owner=u'None', preview_start=None, preview_length=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.CRM(owner=u'None', desc=u'None', data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.ETC(format=None, events=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.GEO(encoding=None, mime=u'None', filename=u'None', desc=u'None', data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.IPL(encoding=None, people=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.LNK(frameid=None, url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.MCI(data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.MLL(frames=None, bytes=None, milliseconds=None, bits_for_bytes=None, bits_for_milliseconds=None, data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.PIC(encoding=None, mime=None, type=None, desc=u'None', data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.POP(email=u'None', rating=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.REV(left=None, right=None, bounce_left=None, bounce_right=None, feedback_ltl=None, feedback_ltr=None, feedback_rtr=None, feedback_rtl=None, premix_ltr=None, premix_rtl=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.SLT(encoding=None, lang=None, format=None, type=None, desc=u'None', text=None)
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.STC(format=None, data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TAL(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TBP(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCM(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCO(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCP(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TCR(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDA(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TDY(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TEN(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TFT(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TIM(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TKE(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TLA(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TLE(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TMT(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOA(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOF(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOL(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOR(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TOT(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TP1(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TP2(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TP3(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TP4(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPA(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TPB(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRC(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRD(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TRK(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSI(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TSS(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TT1(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TT2(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TT3(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TXT(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TXX(encoding=None, desc=u'None', text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.TYE(encoding=None, text=[])
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.UFI(owner=u'None', data='None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.ULT(encoding=None, lang=None, desc=u'None', text=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WAF(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WAR(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WAS(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WCM(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WCP(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WPB(url=u'None')
    :show-inheritance:
    :members:


.. autoclass:: mutagen.id3.WXX(encoding=None, desc=u'None', url=u'None')
    :show-inheritance:
    :members:

