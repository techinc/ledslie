import pytest
import json

from pytest import fail

import ledslie.processors.typesetter
from ledslie.definitions import LEDSLIE_TOPIC_TYPESETTER_SIMPLE_TEXT, LEDSLIE_TOPIC_TYPESETTER_1LINE, \
    LEDSLIE_TOPIC_TYPESETTER_3LINES, LEDSLIE_TOPIC_SEQUENCES_PROGRAMS, LEDSLIE_TOPIC_SEQUENCES_UNNAMED
from ledslie.messages import TextSingleLineLayout, TextTripleLinesLayout, FrameSequence
from ledslie.processors.service import Config
from ledslie.processors.typesetter import Typesetter
from ledslie.tests.fakes import FakeMqttProtocol, FakeLogger


class TestTypesetter(object):

    @pytest.fixture
    def tsetter(self):
        endpoint = None
        factory = None
        s = Typesetter(endpoint, factory)
        s.protocol = FakeMqttProtocol()
        return s

    def test_on_connect(self, tsetter):
        ledslie.processors.typesetter.log = FakeLogger()
        protocol = FakeMqttProtocol()
        tsetter.connectToBroker(protocol)

    def test_typeset_simple_text(self, tsetter):
        topic = LEDSLIE_TOPIC_TYPESETTER_SIMPLE_TEXT
        payload = "Hello world!"
        assert 0 == len(tsetter.protocol._published_messages)
        tsetter.onPublish(topic, payload, qos=0, dup=False, retain=False, msgId=0)
        assert 1 == len(tsetter.protocol._published_messages)
        seq_topic, seq_data = tsetter.protocol._published_messages[-1]
        assert seq_topic == LEDSLIE_TOPIC_SEQUENCES_UNNAMED

    def test_ledslie_typesetter_1line(self, tsetter):
        topic = LEDSLIE_TOPIC_TYPESETTER_1LINE
        msg = TextSingleLineLayout()
        msg.text = 'Foo bar quux.'
        assert 0 == len(tsetter.protocol._published_messages)
        tsetter.onPublish(topic, msg.serialize(), qos=0, dup=False, retain=False, msgId=0)
        assert 1 == len(tsetter.protocol._published_messages)
        seq_topic, seq_data = tsetter.protocol._published_messages[-1]
        assert seq_topic == LEDSLIE_TOPIC_SEQUENCES_UNNAMED

    def test_ledslie_typesetter_3lines(self, tsetter):
        topic = LEDSLIE_TOPIC_TYPESETTER_3LINES
        msg = TextTripleLinesLayout()
        msg.lines = ["Ledslie \\u00a9 GNU-AGPL3 ~ ;-)",
                     "https://wiki.techinc.nl/index.php/Ledslie",
                     "https://github.com/techinc/ledslie"]
        assert 0 == len(tsetter.protocol._published_messages)
        tsetter.onPublish(topic, msg.serialize(), qos=0, dup=False, retain=False, msgId=0)
        assert 1 == len(tsetter.protocol._published_messages)
        seq_topic, seq_data = tsetter.protocol._published_messages[-1]
        assert seq_topic == LEDSLIE_TOPIC_SEQUENCES_UNNAMED
        assert len(seq_data) > Config()['DISPLAY_SIZE']

    def test_ledslie_typesetting_3lines_multiline(self, tsetter):
        """I test sending more then 3 lines to the display in 3 lines mode."""
        topic = LEDSLIE_TOPIC_TYPESETTER_3LINES
        msg = TextTripleLinesLayout()
        msg.lines = ["Foo", "Bar", "Quux", "FOOBAR"]
        tsetter.onPublish(topic, msg.serialize(), qos=0, dup=False, retain=False, msgId=0)
        seq_topic, seq_data = tsetter.protocol._published_messages[-1]
        assert seq_topic == LEDSLIE_TOPIC_SEQUENCES_UNNAMED
        res_obj = json.loads(seq_data.decode())
        # assert len(res_obj[0]) > 1

    def test_ledslie_typesetter_fields(self, tsetter):
        topic = LEDSLIE_TOPIC_TYPESETTER_1LINE
        msg = TextSingleLineLayout()
        msg.text = 'Foo bar quux.'
        msg.duration = 1000
        msg.program = 'foobar'
        assert 0 == len(tsetter.protocol._published_messages)
        tsetter.onPublish(topic, msg.serialize(), qos=0, dup=False, retain=False, msgId=0)
        assert 1 == len(tsetter.protocol._published_messages)

        seq_topic, seq_data = tsetter.protocol._published_messages[-1]
        assert (LEDSLIE_TOPIC_SEQUENCES_PROGRAMS[:-1] + "foobar") == seq_topic
        seq = FrameSequence().load(seq_data)
        assert 1000 == seq.duration

    def test_font_size(self, monkeypatch, tsetter):
        font_size = 13
        text = "lala"
        def typetype(font_path, font_size):
            assert 13 == font_size
        monkeypatch.setattr("PIL.ImageFont.truetype", typetype)
        tsetter.typeset_1line(text, font_size)

    def test_typeset_3lines_none(self, tsetter):
        """
        I test the behaviour when 3lines gets empty lines or None. No Frame should be put onto the FrameSequence.
        """
        seq = FrameSequence()
        msg = TextTripleLinesLayout()
        msg.lines = []
        tsetter.typeset_3lines(seq, msg)
        assert 0 == len(seq)
        msg.lines = None
        tsetter.typeset_3lines(seq, msg)
        assert 0 == len(seq)

    def test_typeset_3lines_single(self, tsetter):
        seq = FrameSequence()
        msg = TextTripleLinesLayout()
        msg.lines = ["Foo", "Bar"]
        tsetter.typeset_3lines(seq, msg)
        assert 1 == len(seq)
        for f in seq.frames:
            assert len(f) == Config()['DISPLAY_SIZE']

    def test_typeset_3lines_multi(self, tsetter):
        seq = FrameSequence()
        msg = TextTripleLinesLayout()
        msg.lines = ["Foo", "Bar", "Quux", "Foobar", "FooQuux"]
        tsetter.typeset_3lines(seq, msg)
        assert len(seq) > 1
        for f in seq.frames:
            assert len(f) == Config()['DISPLAY_SIZE']

    def test_typeset_3lines_appends(self, tsetter):
        """
        I test that typeset_3lines appends new frames to the end of the sequence.
        """
        msg = TextTripleLinesLayout()
        msg.lines = ["Foo"]
        seq = FrameSequence()
        tsetter.typeset_3lines(seq, msg)
        assert 1 == len(seq)
        frame1 = seq[-1].raw()
        msg.lines = ["Bar"]
        tsetter.typeset_3lines(seq, msg)
        assert 2 == len(seq)
        assert frame1 != seq[-1].raw()

    def test_typeset_3lines_font(self, tsetter):
        """
        I test different fonts for 3lines.
        """
        msg = TextTripleLinesLayout()
        msg.lines = ["Foo"]
        seq = FrameSequence()
        tsetter.typeset_3lines(seq, msg)
        frame_font_default = seq[-1].raw()
        msg.size = '8x8'
        tsetter.typeset_3lines(seq, msg)
        assert frame_font_default == seq[-1].raw()

        msg.size = '6x7'
        tsetter.typeset_3lines(seq, msg)
        assert frame_font_default != seq[-1].raw()

        msg.size = '1x1'
        try:
            tsetter.typeset_3lines(seq, msg)
            fail("Should not get here.")
        except KeyError:
            pass
