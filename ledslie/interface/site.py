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

import logging
import json

from PIL import Image, ImageSequence

from werkzeug.exceptions import UnsupportedMediaType
from flask import Flask, render_template, request, json, Response
from flask_mqtt import Mqtt

from ledslie.definitions import LEDSLIE_TOPIC_TYPESETTER_1LINE, LEDSLIE_TOPIC_TYPESETTER_3LINES, \
    LEDSLIE_TOPIC_SEQUENCES_PROGRAMS, LEDSLIE_TOPIC_SEQUENCES_UNNAMED, LEDSLIE_TOPIC_ALERT
from ledslie.messages import FrameSequence, Frame

app = Flask(__name__)
mqtt = Mqtt()


@app.route('/')
def index():
    return render_template('index.html')


def send_image(sequence, program_name):
    if not program_name:
        topic = LEDSLIE_TOPIC_SEQUENCES_UNNAMED
    else:
        topic = LEDSLIE_TOPIC_SEQUENCES_PROGRAMS[:-1] + program_name
    payload = sequence.serialize()
    mqtt.publish(topic, payload)
    return payload


@app.route('/gif', methods=['POST'])
def gif():
    f = request.files['f']
    program = request.form['program']
    try:
        im = Image.open(f)
    except OSError:
        raise UnsupportedMediaType()
    sequence = FrameSequence()
    for frame_raw in ImageSequence.Iterator(im):
        image_data, duration = process_frame(frame_raw)
        sequence.add_frame(Frame(image_data, duration))
    payload = send_image(sequence, program)
    return Response(payload, mimetype='application/json')


@app.route('/text', methods=['POST'])
def text1():
    text = request.form['text']
    duration = int(request.form['duration'])
    program = request.form['program']
    font_size = float(request.form['font_size'])
    set_data = {
        'text': text,
        'program': program,
        'duration': duration,
        'font_size': font_size
    }
    payload = json.dumps(set_data)
    mqtt.publish(LEDSLIE_TOPIC_TYPESETTER_1LINE, payload)
    return Response(payload, mimetype='application/json')


@app.route('/text3', methods=['POST'])
def text3():
    lines = request.form['l1'], request.form['l2'], request.form['l3']
    size = request.form['font']
    duration = int(request.form['duration'])
    program = request.form['program']
    set_data = {
        'lines': lines,
        'duration': duration,
        'program': program,
        'size': size,
    }
    payload = json.dumps(set_data)
    mqtt.publish(LEDSLIE_TOPIC_TYPESETTER_3LINES, payload)
    return Response(payload, mimetype='application/json')


@app.route('/alert', methods=['POST'])
def alert():
    text = request.form['text']
    who = request.form['who']
    alert_type = "spacealert"
    set_data = {
        'text': text,
        'who': who,
    }
    payload = json.dumps(set_data)
    mqtt.publish(LEDSLIE_TOPIC_ALERT + alert_type, payload)
    return Response(payload, mimetype='application/json')


def process_frame(frame_raw):
    frame = frame_raw.copy()
    if (app.config.get("DISPLAY_WIDTH"), app.config.get("DISPLAY_HEIGHT")) != frame.size:
        frame = frame.resize((app.config.get("DISPLAY_WIDTH"), app.config.get("DISPLAY_HEIGHT")))
    frame_image = frame.convert("L")
    encoded_image = frame_image.tobytes()
    if 'duration' in frame.info:
        duration = frame.info.get('duration')
    else:
        duration = app.config.get("DISPLAY_DEFAULT_DELAY")
    return bytearray(encoded_image), duration


def make_app():
    app.config.from_object('ledslie.defaults')
    app.config.from_envvar('LEDSLIE_CONFIG')
    mqtt.init_app(app)
    print(("broker url: %s. port: %s." % (mqtt.broker_url, mqtt.broker_port)))
    return app


def main():
    site_app = make_app()
    app.logger.setLevel(logging.DEBUG)
    site_app.run()


if __name__ == '__main__':
    main()
