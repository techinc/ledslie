# Ledslie, a community information display
# Copyright (C) 2017-18  Chotee@openended.eu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
from twisted.internet import reactor, task
from twisted.logger import Logger

from ledslie.config import Config
from ledslie.content.generic import CreateContent, GenericContent
from ledslie.content.mpd import MPDFactory
from ledslie.definitions import LEDSLIE_TOPIC_TYPESETTER_3LINES
from ledslie.messages import TextTripleLinesLayout


class MpdPlaying(GenericContent):
    def __init__(self, endpoint, factory):
        self.log = Logger(self.__class__.__name__)
        super().__init__(endpoint, factory)
        self.update_task = None
        self.mpd = None
        self.program_name = 'playing'
        self.playing_state = False

    def onMpdConnected(self, mpdProtocol):
        self.log.info("MPD connected.")
        self.mpd = mpdProtocol
        self.get_playing_state()

    def onBrokerConnected(self):
        self.update_task = task.LoopingCall(self.get_playing_state)
        self.update_task.start(float(self.config['MPD_PLAYING_UPDATE']), now=True)

    def get_playing_state(self):
        if self.mpd is None:
            self.log.info("MPD not yet ready")
            return
        self.mpd.status().addCallback(self.get_song_info)

    def get_song_info(self, state_info):
        if state_info['state'] == 'play':
            self.mpd.currentsong().addCallback(self.display_song_info)
            self.playing_state = True
        else:
            if self.playing_state:
                self.log.info("No more songs playing")
                self.remove_display(self.program_name)
            self.playing_state = False

    def display_song_info(self, data):
        def _logAll(*args):
            self.log.debug("all publishing complete args={args!r}", args=args)

        playing_info = [
            data.get('title', "UNKNOWN"),
            "by {}".format(data.get('artist', "UNKNOWN")),
            "from {}".format(data.get('album', "UNKNOWN")),
        ]
        msg = TextTripleLinesLayout()
        msg.lines = playing_info
        msg.duration = self.config['INFO_DISPLAY_DURATION']
        msg.program = self.program_name
        msg.size = '6x7'
        self.log.info(repr(playing_info))
        d = self.publish(topic=LEDSLIE_TOPIC_TYPESETTER_3LINES, message=msg, qos=1)
        d.addCallbacks(_logAll, self._logFailure)
        return d

    def _logFailure(self, failure):
        self.log.debug("reported failure: {message}", message=failure.getErrorMessage())
        return failure


def connection_error(failure):
    Logger().error("connection failure: {message}", message=failure.getErrorMessage())



def _mpd_connection_lost(service):
    service.mpd = None

if __name__ == '__main__':
    ns = __file__.split(os.sep)[-1]
    config = Config(envvar_silent=False)

    mpdFactory = MPDFactory()
    service = CreateContent(MpdPlaying)

    def connection_made(mpd_connection):
        service.onMpdConnected(mpd_connection)
    mpdFactory.connectionMade = connection_made

    def connection_lost(service):
        service.mpd = None
    mpdFactory.connectionLost = connection_lost
    reactor.connectTCP(config['MPD_HOST'], config['MPD_PORT'], mpdFactory)
    reactor.run()
