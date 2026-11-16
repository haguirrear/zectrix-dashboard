"""Sinks deliver the collected data to the server that renders the screen.

Each module exposes send(data, cfg) -> str. To move off LaraPaper, add a module here
(e.g. zectrix_server.py) and select it with SINK=<name>; sources don't change.
"""

from . import larapaper

SINKS = {"larapaper": larapaper}
