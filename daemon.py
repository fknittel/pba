from __future__ import print_function

import gpio


class SprinklerControl(object):
    def __init__(self):
        self._sprinkler_to_port = {}

    def add_sprinkler(self, sprinkler_id, port):
        self._sprinkler_to_port[sprinkler_id] = port

    def turn_on(self, sprinkler_id):
        self._sprinkler_to_port[sprinkler_id].turn_on()

    def turn_off(self, sprinkler_id):
        self._sprinkler_to_port[sprinkler_id].turn_off()
