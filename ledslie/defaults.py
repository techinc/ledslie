"""
I contain the default base configuration variables and values  that may be adapted for either different deployment
situations or even run-time. If these variables are not overridden anywhere, these are the values. We should not have
any configuration values that are not defined here, making this the list of all available settings.
"""

DEBUG=False
MQTT_BROKER_URL = 'localhost'  # use the free broker from HIVEMQ
MQTT_BROKER_PORT = 1883  # default port for non-tls connection
MQTT_BROKER_CONN_STRING = 'tcp:%s:%s' % (MQTT_BROKER_URL, MQTT_BROKER_PORT)
MQTT_KEEPALIVE = 60  # set the time interval for sending a ping to the broker to 5 seconds
# app.config['MQTT_USERNAME'] = ''  # set the username here if you need authentication for the broker
# app.config['MQTT_PASSWORD'] = ''  # set the password here if the broker demands authentication
# app.config['MQTT_TLS_ENABLED'] = False  # set TLS to disabled for testing purposes

FONT_DIRECTORY = '../../resources/fonts/'

SERIAL_BAUDRATE = 115200
SERIAL_PORT = '/dev/ttyACM0'  # set to "fake" to run without serial port.

DISPLAY_WIDTH = 144
DISPLAY_HEIGHT = 24
DISPLAY_SIZE = DISPLAY_WIDTH * DISPLAY_HEIGHT
DISPLAY_DEFAULT_DELAY = 5000  # Delay in miliseconds for the whole screen
DISPLAY_LINE_DURATION = 2500  # Delay in miliseconds for each line.

TYPESETTER_1LINE_DEFAULT_FONT_SIZE = 20
TYPESETTER_ANIMATE_VERTICAL_SCROLL_DELAY = 30  # ms to wait between each scrolling frame.

PROGRAM_RETIREMENT_AGE = 30*60  # Age in seconds before the program is removed. 30 minutes.
ALERT_RETIREMENT_AGE   = 5*60   # Age in seconds before a alert is removed
ALERT_INITIAL_REPEAT   = 5      # Number of times an alert is repeated before it is seen as a normal program.

PROGRESS_DISPLAY_DURATION = 5*1000  # Miliseconds that the progress message is shown.

LOCATION_LAT = 52.34557
LOCATION_LON =  4.82647
TIMEZONE = 'Europe/Amsterdam'

RAIN_DATA_SOURCE = "https://gpsgadget.buienradar.nl/data/raintext/?lat=%s&lon=%s" % (LOCATION_LAT, LOCATION_LON)
RAIN_UPDATE_FREQ = 5*60  # Seconds between updates
RAIN_DISPLAY_DURATION = 3*1000  # Mili-Seconds that the rain message is shown.

INFO_UPDATE_FREQ  = 15*60  # Seconds between updates
INFO_DISPLAY_DURATION = 4*1000  # Mili-Seconds that the rain message is shown.

EVENTS_DATA_SOURCE = 'https://wiki.techinc.nl/index.php/Events'
EVENTS_UPDATE_FREQ = 5*60  # Seconds between updates.
EVENTS_LINE_DURATION = 2500  # Mili-seconds that each information line is shown.

MIDNIGHT_DISPLAY_DURATION = 5*1000  # Mili-seconds that information is shown.
MIDNIGHT_SHOW_VALIDITY    = 5*60    # Seconds the program is considered to be shown.
MIDNIGHT_FONT_SIZE        = 16      # Font-size of the message

COINS_PRICE_SOURCE        = 'https://min-api.cryptocompare.com/data/pricemulti?fsyms=BTC,BCH,ETH&tsyms=EUR'
COINS_UPDATE_FREQ         = 5*60  # Seconds between price updates.
COINS_DISPLAY_DURATION    = 6*1000  # Mili-seconds that information is shown.


OVINFO_STOPAREA_URLS      = [  # This defines the different stops we want to know what traffic passes there.
    # 04318: Henk Sneevlietweg
    # 04094: Aletta Jacobslaan
    # 04088: Louwesweg
    "http://v0.ovapi.nl/stopareacode/04318,04094,04088/departures"
]
OVINFO_UPDATE_FREQ        = 5*60  # Seconds between pulling new information in from the API.
OVINFO_PUBLISH_FREQ       = 1*60   # Seconds between updating the display program.
OVINFO_LINE_DELAY         = 2000  # Miliseconds per displayed line.
OVINFO_DISPLAY_CUTOFF     = 120  # The amount of seconds that have to be left for the arrival to be displayed

MPD_PLAYING_UPDATE = 10
MPD_HOST = 'mpd.ti'
MPD_PORT = 6600

INTERMEZZO_WIPE_FRAME_DELAY = 10  # Delay in miliseconds between wipe frames
INTERMEZZO_WIPE_FRAME_STEP_SIZE = 3  # number of pixels to move with each wipe frame.

INVADERS_FRAME_DELAY = 30  # How many milliseconds between.

PACMAN_MOVE = 4
PACMAN_DELAY = 40
