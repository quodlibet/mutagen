from os.path import join
from unittest import TestCase
from tests import registerCase
from mutagen.id3 import ID3, BitPaddedInt

try: from sets import Set as set
except ImportError: pass

class _ID3(dict): pass
_23 = _ID3(); _23.version = (2,3,0)
_24 = _ID3(); _24.version = (2,4,0)

class ID3Loading(TestCase):

    empty = join('tests', 'data', 'emptyfile.mp3')
    silence = join('tests', 'data', 'silence-44-s.mp3')

    def test_empty_file(self):
        name = self.empty
        self.assertRaises(ValueError, ID3, filename=name)
        #from_name = ID3(name)
        #obj = open(name, 'rb')
        #from_obj = ID3(fileobj=obj)
        #self.assertEquals(from_name, from_explicit_name)
        #self.assertEquals(from_name, from_obj)

    def test_nonexistent_file(self):
        name = join('tests', 'data', 'does', 'not', 'exist')
        self.assertRaises(EnvironmentError, ID3, name)

    def test_header_empty(self):
        id3 = ID3()
        id3._ID3__fileobj = file(self.empty, 'rb')
        self.assertRaises(EOFError, id3.load_header)

    def test_header_silence(self):
        id3 = ID3()
        id3._ID3__fileobj = file(self.silence, 'rb')
        id3.load_header()
        self.assertEquals(id3.version, (2,3,0))
        self.assertEquals(getattr(id3, '_ID3__size'), 1304)

class ID3Tags(TestCase):
    def setUp(self):
        self.silence = join('tests', 'data', 'silence-44-s.mp3')

    def test_None(self):
        id3 = ID3(self.silence, known_frames={})
        self.assertEquals(0, len(id3.keys()))
        self.assertEquals(9, len(id3.unknown_frames))

    def test_23(self):
        id3 = ID3(self.silence)
        self.assertEquals(8, len(id3.keys()))
        self.assertEquals(0, len(id3.unknown_frames))
        self.assertEquals('Quod Libet Test Data', id3['TALB'])
        self.assertEquals('Silence', str(id3['TCON']))
        self.assertEquals('Silence', str(id3['TIT1']))
        self.assertEquals('Silence', str(id3['TIT2']))
        self.assertEquals(3000, +id3['TLEN'])
        self.assertNotEquals(['piman','jzig'], id3['TPE1'])
        self.assertEquals('02/10', id3['TRCK'])
        self.assertEquals(2, +id3['TRCK'])
        self.assertEquals('2004', id3['TYER'])
        self.assertEquals(2004, +id3['TYER'])

    def test_23_multiframe_hack(self):
        class ID3hack(ID3):
            "Override 'correct' behavior with desired behavior"
            def loaded_frame(self, name, tag):
                if name == 'TXXX' or name == 'WXXX':
                    name += ':' + tag.desc
                if name in self: self[name].extend(tag[:])
                else: self[name] = tag

        id3 = ID3hack(self.silence)
        self.assertEquals(8, len(id3.keys()))
        self.assertEquals(0, len(id3.unknown_frames))
        self.assertEquals('Quod Libet Test Data', id3['TALB'])
        self.assertEquals('Silence', str(id3['TCON']))
        self.assertEquals('Silence', str(id3['TIT1']))
        self.assertEquals('Silence', str(id3['TIT2']))
        self.assertEquals(3000, +id3['TLEN'])
        self.assertEquals(['piman','jzig'], id3['TPE1'])
        self.assertEquals('02/10', id3['TRCK'])
        self.assertEquals(2, +id3['TRCK'])
        self.assertEquals('2004', id3['TYER'])
        self.assertEquals(2004, +id3['TYER'])

def TestReadTags():
    ID3_tags = {
    'TALB': {'[]':'\x00a/b', 'encoding':0, '':'a/b'},
    'TBPM': {'[]':'\x00120', 'encoding':0, '':'120', '+':120},
    'TCOM': {'[]':'\x00a/b', 'encoding':0, '':['a','b']},
    'TCON': {'[]':'\x00(21)Disco', 'encoding':0, '':'(21)Disco'},
    'TCOP': {'[]':'\x001900 c', 'encoding':0, '':'1900 c'},
    'TDAT': {'[]':'\x00a/b', 'encoding':0, '':'a/b'},
    'TDLY': {'[]':'\x001205', 'encoding':0, '':'1205'},
    'TENC': {'[]':'\x00a b/c d', 'encoding':0, '':'a b/c d'},
    'TEXT': {'[]':'\x00a b/c d', 'encoding':0, '':['a b', 'c d']},
    'TFLT': {'[]':'\x00MPG/3', 'encoding':0, '':'MPG/3'},
    'TIME': {'[]':'\x001205', 'encoding':0, '':'1205'},
    'TIT1': {'[]':'\x00a/b', 'encoding':0, '':'a/b'},
    # TIT2 checks misaligned terminator '\x00\x00' across crosses utf16 chars
    'TIT2': {'[]':'\x01\xff\xfe\x38\x00\x00\x38', 'encoding':1, '':u'8\u3800'},
    'TIT3': {'[]':'\x00a/b', 'encoding':0, '':'a/b'},
    'TKEY': {'[]':'\x00A#m', 'encoding':0, '':'A#m'},
    'TLAN': {'[]':'\x006241', 'encoding':0, '':'6241', '{}+':6241},
    'TLEN': {'[]':'\x006241', 'encoding':0, '':'6241', '+':6241},
    'TMED': {'[]':'\x00med', 'encoding':0, '':'med'},
    'TOAL': {'[]':'\x00alb', 'encoding':0, '':'alb'},
    'TOFN': {'[]':'\x0012 : bar', 'encoding':0, '':'12 : bar'},
    'TOLY': {'[]':'\x00lyr', 'encoding':0, '':'lyr'},
    'TOPE': {'[]':'\x00own/lic', 'encoding':0, '':'own/lic'},
    'TORY': {'[]':'\x001923', 'encoding':0, '':'1923', '+':1923},
    'TOWN': {'[]':'\x00own/lic', 'encoding':0, '':'own/lic'},
    'TPE1': {'[]':'\x00ab', 'encoding':0, '':['ab']},
    'TPE2': {'[]':'\x00ab/cd/ef', 'encoding':0, '':['ab','cd', 'ef']},
    'TPE3': {'[]':'\x00ab/cd', 'encoding':0, '':['ab','cd']},
    'TPE4': {'[]':'\x00ab/cd', 'encoding':0, '':['ab','cd']},
    'TPOS': {'[]':'\x0008/32', 'encoding':0, '':'08/32', '+':8},
    'TPUB': {'[]':'\x00pub', 'encoding':0, '':'pub'},
    'TRCK': {'[]':'\x004/9', 'encoding':0, '':'4/9', '+':4},
    'TRDA': {'[]':'\x00Sun Jun 12', 'encoding':0, '':'Sun Jun 12'},
    'TRSN': {'[]':'\x00ab/cd', 'encoding':0, '':'ab/cd'},
    'TRSO': {'[]':'\x00ab', 'encoding':0, '':'ab'},
    'TSIZ': {'[]':'\x0012345', 'encoding':0, '':'12345', '+':12345},
    'TSRC': {'[]':'\x0012345', 'encoding':0, '':'12345', '{}+':2004},
    'TSSE': {'[]':'\x0012345', 'encoding':0, '':'12345', '{}+':2004},
    'TYER': {'[]':'\x002004', 'encoding':0, '':'2004', '+':2004},

    'TXXX': {'[]':'\x00usr\x00a/b', 'encoding':0, '':'a/b', 'desc':'usr'},

    'WCOM': {'[]':'http://foo', '{}encoding':0, '':'http://foo'},
    'WCOP': {'[]':'http://bar', '':'http://bar'},
    'WOAF': {'[]':'http://baz', '':'http://baz'},
    'WOAS': {'[]':'http://bar', '':'http://bar'},
    'WORS': {'[]':'http://bar', '':'http://bar'},
    'WPAY': {'[]':'http://bar', '':'http://bar'},
    'WPUB': {'[]':'http://bar', '':'http://bar'},

    'IPLS': {'[]':'\x00a\x00A\x00b\x00B\x00', '':[['a','A'],['b','B']]},

    'MCDI': {'[]':'\x01\x02\x03\x04', '':'\x01\x02\x03\x04'},
    
    #'ETCO': {'[]':'\x01\x12\x00\x00\x7f\xff', '':[(18,32767)], 'format':1},

    'COMM': {'[]':'\x00ENUT\x00Com', '':'Com', 'desc':'T', 'lang':'ENU',
             'encoding':0},
    'APIC': {'[]':'\x00-->\x00\x03cover\x00cover.jpg', '':'cover.jpg',
             'mime':'-->', 'type':3, 'desc':'cover', 'encoding':0},
    'USER': {'[]':'\x00ENUCom', '':'Com', 'lang':'ENU', 'encoding':0},
    }

    tests = {}
    repr_tests = {}
    for tag, info in ID3_tags.iteritems():

        info = info.copy()
        data = info.pop('[]')
        value = info.pop('')

        def test_tag(self, tag=tag, data=data, value=value, info=info):
            from operator import pos
            id3 = __import__('mutagen.id3', globals(), locals(), [tag])
            TAG = getattr(id3, tag)
            tag = TAG.fromData(_23, 0, data)
            self.assertEquals(value, tag)
            for attr, value in info.iteritems():
                if not isinstance(value, list):
                    value = [value]
                    tag = [tag]
                for value, tag in zip(value, iter(tag)):
                    if attr.startswith('{}'):
                        self.assertRaises(AttributeError, getattr, tag, attr[2:])
                    elif attr == '+':
                        self.assertEquals(value, pos(tag))
                    else:
                        self.assertEquals(value, getattr(tag, attr))
        tests['test_' + tag] = test_tag

        def test_tag_repr(self, tag=tag, data=data):
            id3 = __import__('mutagen.id3', globals(), locals(), [tag])
            TAG = getattr(id3, tag)
            tag = TAG.fromData(_23, 0, data)
            tag2 = eval(repr(tag), {TAG.__name__:TAG})
            self.assertEquals(type(tag), type(tag2))
            for spec in TAG._framespec:
                attr = spec.name
                self.assertEquals(getattr(tag, attr), getattr(tag2, attr))
        repr_tests['test_repr_' + tag] = test_tag_repr

    testcase = type('TestReadTags', (TestCase,), tests)
    registerCase(testcase)
    testcase = type('TestReadReprTags', (TestCase,), repr_tests)
    registerCase(testcase)
TestReadTags()
del TestReadTags

class BitPaddedIntTest(TestCase):

    def test_zero(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x00\x00'), 0)

    def test_1(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x00\x01'), 1)

    def test_1l(self):
        self.assertEquals(BitPaddedInt('\x01\x00\x00\x00', bigendian=False), 1)

    def test_129(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x01'), 0x81)

    def test_129b(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x81'), 0x81)

    def test_65(self):
        self.assertEquals(BitPaddedInt('\x00\x00\x01\x81', 6), 0x41)

    def test_s0(self):
        self.assertEquals(BitPaddedInt.to_str(0), '\x00\x00\x00\x00')

    def test_s1(self):
        self.assertEquals(BitPaddedInt.to_str(1), '\x00\x00\x00\x01')

    def test_s1l(self):
        self.assertEquals(
            BitPaddedInt.to_str(1, bigendian=False), '\x01\x00\x00\x00')

    def test_s129(self):
        self.assertEquals(BitPaddedInt.to_str(129), '\x00\x00\x01\x01')

    def test_s65(self):
        self.assertEquals(BitPaddedInt.to_str(0x41, 6), '\x00\x00\x01\x01')

    def test_w129(self):
        self.assertEquals(BitPaddedInt.to_str(129, width=2), '\x01\x01')

    def test_w129l(self):
        self.assertEquals(
            BitPaddedInt.to_str(129, width=2, bigendian=False), '\x01\x01')

    def test_wsmall(self):
        self.assertRaises(ValueError, BitPaddedInt.to_str, 129, width=1)

    def test_as_to(self):
        self.assertEquals(BitPaddedInt(238).as_str(), BitPaddedInt.to_str(238))

class FrameSanityChecks(TestCase):

    def test_TF(self):
        from mutagen.id3 import TextFrame
        self.assert_(isinstance(TextFrame(text='text'), TextFrame))

    def test_UF(self):
        from mutagen.id3 import UrlFrame
        self.assert_(isinstance(UrlFrame('url'), UrlFrame))

    def test_WXXX(self):
        from mutagen.id3 import WXXX
        self.assert_(isinstance(WXXX(url='durl'), WXXX))

    def test_NTF(self):
        from mutagen.id3 import NumericTextFrame
        self.assert_(isinstance(NumericTextFrame(text='1'), NumericTextFrame))

    def test_NTPF(self):
        from mutagen.id3 import NumericPartTextFrame
        self.assert_(isinstance(NumericPartTextFrame(text='1/2'), NumericPartTextFrame))

    def test_STF(self):
        from mutagen.id3 import SlashTextFrame
        self.assert_(isinstance(SlashTextFrame(texts=['a','b']), SlashTextFrame))

    def test_TXXX(self):
        from mutagen.id3 import TXXX
        self.assert_(isinstance(TXXX(desc='d',text='text'), TXXX))

    def test_zlib_latin1(self):
        from mutagen.id3 import TPE1
        tag = TPE1.fromData(_23, 0x80,
                'x\x9cc(\xc9\xc8,V\x00\xa2D\xfd\x92\xd4\xe2\x12\x00&\x7f\x05%')
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag, ['this is a', 'test'])

    def test_utf8(self):
        from mutagen.id3 import TPE1
        tag = TPE1.fromData(_23, 0x00, '\x03this is a test')
        self.assertEquals(tag.encoding, 3)
        self.assertEquals(tag, 'this is a test')

    def test_zlib_utf16(self):
        from mutagen.id3 import TPE1
        tag = TPE1.fromData(_23, 0x80, 'x\x9cc\xfc\xff\xaf\x84!\x83!\x93'
                '\xa1\x98A\x01J&2\xe83\x940\xa4\x02\xd9%\x0c\x00\x87\xc6\x07#')
        self.assertEquals(tag.encoding, 1)
        self.assertEquals(tag, ['this is a', 'test'])

    def test_unsync_encode(self):
        from mutagen.id3 import unsynch as un
        for d in ('\xff\xff\xff\xff', '\xff\xf0\x0f\x00', '\xff\x00\x0f\xf0'):
            self.assertEquals(d, un.decode(un.encode(d)))
            self.assertNotEqual(d, un.encode(d))

    def test_unsync_decode(self):
        from mutagen.id3 import unsynch as un
        self.assertRaises(ValueError, un.decode, '\xff\xff\xff\xff')
        self.assertRaises(ValueError, un.decode, '\xff\xf0\x0f\x00')

    def skip_test_harsh(self):
        from os import walk
        from traceback import print_exc
        total = 0
        failures = {}
        for path, dirs, files in walk('/vault/music'):
            for fn in files:
                if not fn.lower().endswith('.mp3'): continue
                ffn = join(path, fn)
                try:
                    total += 1
                    if not total & 0xFF: print total
                    #print ffn
                    id3 = ID3(ffn)
                    for frame, val in id3.iteritems():
                        pass #print frame, str(val)
                except Exception, err:
                    if err.__class__ not in failures:
                        print_exc()
                    failures.setdefault(err.__class__, []).append(ffn)

        failcount = 0
        for fail, files in failures.iteritems():
            failcount += len(files)
            print fail, len(files)

        print total-failcount, '/', total, 'success'

class BrokenButParsed(TestCase):
    def test_missing_encoding(self):
        from mutagen.id3 import TIT2
        tag = TIT2.fromData(_23, 0x00, 'a test')
        self.assertEquals(tag.encoding, 0)
        self.assertEquals(tag.text, 'a test')

registerCase(ID3Loading)
registerCase(BitPaddedIntTest)
registerCase(ID3Tags)
registerCase(BrokenButParsed)
registerCase(FrameSanityChecks)
