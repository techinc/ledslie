#!/usr/bin/env python3

#     Ledslie, a community information display
#     Copyright (C) 2017-18  Chotee@openended.eu
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Affero General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ============
#
# I decide what information is to be shown on the screen. I do this by keeping track of animations and messages are
# available for displaying.
#
# Messages are send to topic «ledslie/sequences/1/» + «name». Where «name» is the name of the sequence to display. For
# each name only the last sequence is retained. THis allows producers to provide updated information.
#
# An image is simply a sequence of one frame
import json


from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.logger import Logger
from twisted.internet.serialport import SerialPort as RealSerialPort

from ledslie.config import Config
from ledslie.definitions import LEDSLIE_TOPIC_SEQUENCES_PROGRAMS, LEDSLIE_TOPIC_SEQUENCES_UNNAMED, LEDSLIE_ERROR, LEDSLIE_TOPIC_SCHEDULER_PROGRAMS
from ledslie.messages import FrameSequence
from ledslie.processors.animate import AnimateStill
from ledslie.processors.catalog import Catalog
from ledslie.processors.intermezzos import IntermezzoWipe, IntermezzoInvaders, IntermezzoPacman
from ledslie.processors.service import CreateService, GenericProcessor

# ----------------
# Global variables
# ----------------

serial_port = None

log = Logger()


class Scheduler(GenericProcessor):
    subscriptions = (
        (LEDSLIE_TOPIC_SEQUENCES_PROGRAMS, 1),
        (LEDSLIE_TOPIC_SEQUENCES_UNNAMED, 1),
    )

    def __init__(self, endpoint, factory):
        super().__init__(endpoint, factory)
        self.catalog = Catalog()
        self.sequencer = None
        self.frame_iterator = None
        self.led_screen = None

    def onPublish(self, topic, payload, qos, dup, retain, msgId):
        '''
        Callback Receiving messages from publisher
        '''
        log.debug("onPublish topic={topic}, msg={payload}", payload=payload, topic=topic)
        program_name = self.get_program_id(topic)
        if not payload:  # remove programs when the payload is empty.
            if program_name in self.catalog:
                self.catalog.remove_program(program_name)
            return
        seq = FrameSequence().load(payload)
        if seq is None:
            return
        if len(seq) == 1:
            seq = AnimateStill(seq[0])
        self.catalog.add_program(program_name, seq)
        if self.sequencer is None:
            self.sequencer = self.reactor.callLater(0, self.send_next_frame)
        content = json.dumps(self.catalog.list_current_programs())
        self.protocol.publish(LEDSLIE_TOPIC_SCHEDULER_PROGRAMS, content, 0, retain=False)

    def get_program_id(self, topic):
        if topic == LEDSLIE_TOPIC_SEQUENCES_UNNAMED:
            program_id = None
        else:
            program_id = topic.split('/')[-1]
        return program_id

    def send_next_frame(self):
        if self.frame_iterator is None:
            self.frame_iterator = self.catalog.frames_iter()
        try:
            frame = next(self.frame_iterator)
        except KeyError:
            return
        try:
            self.led_screen.publish_frame(frame)
        except FrameException as exc:
            log.error(str(exc))
            self.publish(LEDSLIE_ERROR + "/scheduler", "Program: %s: %s" % (
                self.catalog.current_program.name, str(exc)))
        duration = min(10, frame.duration/1000)
        self.sequencer = self.reactor.callLater(duration, self.send_next_frame)

    def add_intermezzo(self, intermezzo):
        self.catalog.add_intermezzo(intermezzo)


class FrameException(RuntimeError):
    pass


class LEDScreen(Protocol):
    def connectionMade(self):
        global serial_port
        serial_port = self
        log.info('LEDScreen device: %s is connected.' % serial_port)

    def publish_frame(self, frame):
        self.transport.write(self._prepare_image(frame.raw()))

    def _prepare_image(self, image_data):
        if len(image_data) != int(config.get("DISPLAY_SIZE")):
            raise FrameException("WRONG frame size. Expected %d but got %d." % (
                len(image_data), config.get("DISPLAY_SIZE")))
        shifted_data = bytearray()
        for b in image_data:
            shifted_data.append(b >> 1)  # Downshift the data one byte. making the highbyte 0.
        shifted_data.append(1 << 7)  ## end with a new frame marker, a byte with the high byte 1
        return bytes(shifted_data)


class FakeSerialPort(object):
    def __init__(self, protocol):
        log.warn("Starting the FakeSerialPort")
        self.protocol = protocol
        self.protocol.transport = self

    def write(self, data):
        log.info("FAKE WRITING #%d bytes" % len(data))


if __name__ == '__main__':
    log = Logger(__file__)
    config = Config(envvar_silent=False)
    scheduler = CreateService(Scheduler)
    scheduler.add_intermezzo(IntermezzoWipe)
    scheduler.add_intermezzo(IntermezzoInvaders)
    scheduler.add_intermezzo(IntermezzoPacman)
    led_screen = LEDScreen()
    serial_port = config.get('SERIAL_PORT')
    if serial_port == 'fake':
        log.warn("FAKE SERIAL SELECTED.")
        FakeSerialPort(led_screen)
    else:
        baudrate = config.get('SERIAL_BAUDRATE')
        log.info("REAL Serialport %s @ %s" % (serial_port, baudrate))
        RealSerialPort(led_screen, serial_port, reactor, baudrate=baudrate)
    scheduler.led_screen = led_screen
    reactor.run()
