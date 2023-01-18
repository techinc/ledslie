#!/usr/bin/python

from waitress import serve
from ledslie.interface.site import make_app

if __name__ == '__main__':
    site_app = make_app()
    serve(site_app, unix_socket="/var/run/ledslie/ledslie.sock")
