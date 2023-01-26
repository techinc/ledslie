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

from datetime import datetime, timedelta
from collections import defaultdict

from twisted.logger import Logger
from twisted.internet import reactor, task
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

ShortNameOfStoparea = {
    '04318': 'Henk Sneevlietweg',
    '04094': 'Aletta Jacobslaan',
    '04088': 'Louwesweg'
}

ShortNameOfDestinationCode = {
    'SLL': 'Lely',
    'AMS': 'Amstl',
    'CS': 'CS',
    'NCS': 'CS',
    'M09501429': 'Schphl',
    'M19501429': 'Schphl',
    'M19534388': 'Schphl',
    'M19505436': 'Lely',
    'M09505436': 'Lely',
}

ShortnamesOfMetroDestinations = {
        'GEN': 'Gein',
        'CS': 'CS',
        'ITW': 'Iso'}

DestinationCode_ignore = {  # These are final stops walking distance from the space. No need to waste screen on these.
    'NSN',  # Nieuw Sloten
    'SLV',  # Slotervaart
    'NNSN',  # Nieuw Sloten
    'ONPN',  # Oudenaardeplantsoen
}

class Pass():
    def __init__(self, pass_info):
        self.p = pass_info

    def is_valid(self):
        indices = ['TransportType', 'DestinationCode', 'LinePublicNumber', 'ExpectedArrivalTime', 'StopAreaCode']
        return all(index in self.p for index in indices)

    def type(self) -> str:
        return self.p['TransportType'].upper()

    def destination(self) -> str:
        destination_code = self.p['DestinationCode']
        if self.type() == 'METRO':
            for x in ShortnamesOfMetroDestinations:
                if x in destination_code:
                    return ShortnamesOfMetroDestinations[x]
        s = ShortNameOfDestinationCode.get(destination_code)
        if s:
            return s
        return destination_code[:3]

    # Special case for metro 50/51 to Isolatorweg because they are identical
    def line(self) -> str:
        line = self.p['LinePublicNumber']
        if line in ["50", "51"] and self.destination() == ShortnamesOfMetroDestinations['ITW'] and self.type() == "METRO":
            line = "50/51"
        return line

    def short_stopareacode(self) -> str:
        return ShortNameOfStoparea[self.p['StopAreaCode']]

    def time(self) -> datetime:
        try:
            return datetime.fromisoformat(self.p['ExpectedArrivalTime'])
        except:
            return datetime.min

class Lines():
    def __init__(self, config):
        self.lines = defaultdict(list)
        self.config = config

    def add_pass(self, p: Pass):
        self.lines[(p.line(), p.destination(), p.type())].append(p)

    def from_location(self, idx):
        for p in self.lines[idx]:
            return p.short_stopareacode()

    def arrival_times(self, idx):
        times = [p.time() - datetime.now() for p in self.lines[idx]]
        times = sorted([time for time in times if time > timedelta(seconds=self.config['OVINFO_DISPLAY_CUTOFF'])])
        return times


class OVInfoContent(GenericContent):
    def __init__(self, endpoint, factory):
        self.log = Logger(self.__class__.__name__)
        super().__init__(endpoint, factory)
        self.update_task = None
        self.publish_task = None
        self.urls = CircularBuffer(self.config['OVINFO_STOPAREA_URLS'])
        self.lines = Lines(self.config)

    def onBrokerConnected(self):
        self.update_task = task.LoopingCall(self.request_ov_info)
        update_delay_time = float(self.config['OVINFO_UPDATE_FREQ']) / len(self.urls)
        self.update_task.start(update_delay_time, now=True)

        def publish():
            self.publish_ov_display(self.construct_lines(None))

        self.publish_task = task.LoopingCall(publish)
        self.publish_task.start(self.config['OVINFO_PUBLISH_FREQ'])

    def _logFailure(self, failure):
        self.log.debug("reported failure: {message}", message=failure.getErrorMessage())
        return failure

    def request_ov_info(self):
        url = next(self.urls)
        print(url)
        d = treq.get(url)
        d.addCallback(self.received_ov_info)

    def received_ov_info(self, response):
        if response.code == 200:
            d = response.json()
            d.addCallback(self.parse_json)
            d.addCallback(self.line_deduplication)
            d.addCallback(self.construct_lines)
            d.addCallback(self.publish_ov_display)

    def parse_json(self, json):
        for stopareacode in json:
            if stopareacode not in ShortNameOfStoparea:
                continue
            stoparea = json[stopareacode]
            for timingpointcode in stoparea:
                passes = stoparea[timingpointcode]['Passes']
                for pass_name in passes:
                    p = passes[pass_name]
                    if p['DestinationCode'] in DestinationCode_ignore:
                        continue
                    p = Pass(p)
                    if p.is_valid():
                        self.lines.add_pass(p)

    # Remove the busstop at Henk Sneevliet because they also passes Aletta Jacobs which is
    # closer to the space
    def line_deduplication(self, _):
        for line in self.lines.lines:
            passes = self.lines.lines[line]
            self.lines.lines[line] = [p for p in passes if not (p.p['StopAreaCode'] == '04318' and p.type() == "BUS")]

    def type_to_emoji(self, type):
        if type == "METRO":
            return "🚇"
        if type == "BUS":
            return "🚌"
        if type == "TRAM":
            return "🚊"
        return type

    def construct_lines(self, _):
        lines = [(self.lines.from_location(line), line) for line in self.lines.lines]

        def format_time(t):
            minutes = int(t/ 60)
            if minutes < 60:
                return str(minutes) + 'm'
            else:
                return (datetime.now() + timedelta(minutes=minutes)).strftime("%H:%M")

        info = str()
        for stopareacode in ['04318', '04088', '04094']:
            name = ShortNameOfStoparea[stopareacode]
            location_lines = sorted([line for (location, line) in lines if location == name], key=lambda x: len(x[0]))
            if len(location_lines) == 0:
                continue

            header = "Halte " + name + '\n'
            amount_of_arrivals = len([y for y in [self.lines.arrival_times(x) for x in location_lines] if y])
            if amount_of_arrivals == 0:
                continue
            info += header
            for (line_no, dest, type) in location_lines:
                line = ' ' + self.type_to_emoji(type) + '  ' + line_no + '➡' + dest + ' '

                arrival_times = self.lines.arrival_times((line_no, dest, type))
                arrival_times = sorted(set(format_time(arrival.total_seconds()) for arrival in arrival_times))
                if len(arrival_times) == 0:
                    continue
                arrival_times = " ".join(str(x) for x in arrival_times)
                line += arrival_times
                line += ' ' * 24

                line = line[:24]
                if (line[-1] == 'm' or line[-3] == ':' or line[-1] == ' '):
                    info += line
                else:
                    last_space = line.rindex(' ')
                    info += line[:last_space+1]
                info += '\n'

        return info.split('\n')[:-1]

    def publish_ov_display(self, info_lines: list):
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
