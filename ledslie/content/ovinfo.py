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
import json
import os

from datetime import datetime
from dateutil.parser import parser as date_parser
from jsonpath_rw.parser import JsonPathParser
from twisted.internet.defer import Deferred
from twisted.logger import Logger

from twisted.internet import reactor, task
from twisted.web.client import readBody
import treq

from ledslie.config import Config
from ledslie.content.generic import GenericContent, CreateContent
from ledslie.content.utils import CircularBuffer
from ledslie.definitions import LEDSLIE_TOPIC_TYPESETTER_3LINES
from ledslie.messages import TextTripleLinesLayout

# The complete information can be obtained from
# https://reisinformatiegroep.nl/ndovloket/ but you need to request creds to get it.
# But this is the open API that's used.
# Info https://github.com/skywave/KV78Turbo-OVAPI/wiki
#
# An alternative would be to connect to the GVB websockets interface.
# Example of this interface: https://github.com/osresearch/esp32-ttgo/blob/master/demo/BusTimeNL/BusTimeNL.ino
# Twisted websockets client https://github.com/crossbario/autobahn-python/tree/master/examples/twisted/websocket/echo

DestinationCode_to_name = {
    'CS': 'CS',
    'NCS': 'CS',
    'SLL': 'Ly',
    'AMS': 'Am',
    'M09501429': 'SCH',
    'M19501429': 'SCH',
    'M19534388': 'SCH',
    'M19505436': 'Ly',
    'M09505436': 'Ly',
    'SNP': 'SNP',
}
DestinationCode_ignore = {  # These are final stops walking distance from the space. No need to waste screen on these.
    'NSN',  # Nieuw Sloten
    'SLV',  # Slotervaart
    'NNSN',  # Nieuw Sloten
    'ONPN',  # Oudenaardeplantsoen
}

class Transports(object):
    def __init__(self):
        self.routes = {}

    def add_pass(self, number: str, dest_code: str, journey_nr: int, pass_time: datetime):
        key = (number, dest_code)
        journeys = self.routes.setdefault(key, {})
        journeys[journey_nr] = pass_time

    def pass_overview(self, now=None):
        now = datetime.now() if now is None else now
        overview = []
        for key in sorted(self.routes):  # sorting makes testing easier and keeps display order consistent.
            (line_nr, dest_code) = key
            journeys = self.routes[key]
            passes = []
            for journey_nr, pass_moment in list(journeys.items()):
                if pass_moment > now:  # The transport is still to pass by.
                    passes.append(pass_moment)
                else:  # this moment has already passed
                    del journeys[journey_nr]
            if passes:  # only add to the overview if there are passes to report.
                overview.append([line_nr, dest_code, sorted(passes)])
        return overview


class OVInfoContent(GenericContent):
    def __init__(self, endpoint, factory):
        self.log = Logger(self.__class__.__name__)
        super().__init__(endpoint, factory)
        self.update_task = None
        self.publish_task = None
        self.urls = CircularBuffer(self.config['OVINFO_STOPAREA_URLS'])
        self.lines = Transports()

    def onBrokerConnected(self):
        self.update_task = task.LoopingCall(self.update_ov_info)
        # update_delay_time = float(60) / len(self.urls)
        update_delay_time = float(self.config['OVINFO_UPDATE_FREQ']) / len(self.urls)
        self.update_task.start(update_delay_time, now=True)
        self.publish_task = task.LoopingCall(self.publish_ov_info)
        self.publish_task.start(self.config['OVINFO_PUBLISH_FREQ'], now=True)
        # self.publish_task.start(15, now=True)

    def _logFailure(self, failure):
        self.log.debug("reported failure: {message}", message=failure.getErrorMessage())
        return failure

    def update_ov_info(self):
        d = treq.get(next(self.urls))
        d.addCallbacks(self.grab_json_response, self._logFailure)
        d.addCallbacks(self.update_depature_info, self._logFailure)

    def publish_ov_info(self):
        lines = self.create_ov_display()
        return self.publish_ov_display(lines)

    def now(self) -> datetime:
        return datetime.now()

    def time_formatter(self, dt: datetime, now=None):
        now = self.now() if now is None else now
        t_diff = (dt - now).seconds  # time difference in seconds.
        if t_diff < 30*60:  # difference smaller then 30 minutes:
            return "{}m".format(round(t_diff/60))
        elif t_diff < 60*60:  # difference smaller then an hour
            return ":{:02d}".format(dt.minute)
        else:
            return "{:02d}:{:02d}".format(dt.hour, dt.minute)

    def create_ov_display(self):
        lines = []
        for line_nr, dest_code, passes in self.lines.pass_overview():
            if dest_code in DestinationCode_ignore:
                continue
            dest_name = DestinationCode_to_name.get(dest_code, dest_code)
            formatted_passes = " ".join(map(self.time_formatter, passes))
            display_str = "{:>3}{} {}".format(line_nr, dest_name, formatted_passes)
            lines.append(display_str)
        return lines

    def grab_json_response(self, response):
        if response.code != 200:
            raise RuntimeError("Status is not 200 but '%s'" % response.code)
        return response.json()

    def update_depature_info(self, data):
        dparser = date_parser()
        for trans in [x.value for x in JsonPathParser().parse('$..Passes.*').find(data)]:
            expectedTime = dparser.parse(trans['ExpectedArrivalTime'])
            destination_code = trans['DestinationCode']
            self.lines.add_pass(trans['LinePublicNumber'], destination_code,
                                trans['JourneyNumber'], expectedTime)
            if (destination_code not in DestinationCode_to_name
                    and destination_code not in DestinationCode_ignore):
                self.log.warn("Missing DestinationCode: %s = %s" % (destination_code, trans['DestinationName50']))
            # 'LinePublicNumber'  -- '2'
            # 'JourneyNumber' -- 8,
            # 'DestinationCode' -- 'NSN'
            # 'DestinationName50' --  'Nieuw Sloten'
            # 'ExpectedArrivalTime' -- '2017-12-17T00:35:15'

    def publish_ov_display(self, info_lines: list) -> Deferred:
        def _logAll(*args):
            self.log.debug("all publishing complete args={args!r}", args=args)
        if not info_lines:
            return
        msg = TextTripleLinesLayout()
        msg.lines = info_lines
        msg.line_duration = self.config["OVINFO_LINE_DELAY"]
        msg.valid_time = 60  # Information is only valid for a minute.
        msg.program = 'ovinfo'
        msg.size = '6x7'
        msg.lines = info_lines
        d = self.publish(topic=LEDSLIE_TOPIC_TYPESETTER_3LINES, message=msg, qos=1)
        d.addCallbacks(_logAll, self._logFailure)
        return d


if __name__ == '__main__':
    ns = __file__.split(os.sep)[-1]
    Config(envvar_silent=False)
    CreateContent(OVInfoContent)
    reactor.run()
