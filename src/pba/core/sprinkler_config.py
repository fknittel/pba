# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
import logging
from distutils.util import strtobool

log = logging.getLogger(__name__)


class TestSprinkler(object):
    def __init__(self, sprinkler_id):
        self.sprinkler_id = sprinkler_id

    def __str__(self):
        return 'test sprinkler {}'.format(self.sprinkler_id)

    def turn_on(self):
        log.info("turning on sprinkler {}".format(self.sprinkler_id))

    def turn_off(self):
        log.info("turning off sprinkler {}".format(self.sprinkler_id))

    @property
    def is_setup(self):
        return True

    def setup(self):
        log.info("simulating setup for sprinkler {}".format(self.sprinkler_id))


class GpioSprinkler(object):
    def __init__(self, sprinkler_id, gpio_port):
        self.sprinkler_id = sprinkler_id
        self._gpio_port = gpio_port

    def __str__(self):
        return 'gpio sprinkler {} on {}'.format(self.sprinkler_id, self._gpio_port)

    def turn_on(self):
        self._gpio_port.turn_on()

    def turn_off(self):
        self._gpio_port.turn_off()

    @property
    def is_setup(self):
        return self._gpio_port.is_exported

    def setup(self):
        log.info("setting up IO for sprinkler {}".format(self.sprinkler_id))
        self._gpio_port.export()


def load_sprinklers(config, gpio_ctrl, add_sprinkler):
    for sprinkler_name, value in config.items('sprinklers'):
        details = value.split()
        sprinkler_type = details.pop(0)
        log.info('adding sprinkler {0} of type {1}'.format(sprinkler_name,
                sprinkler_type))
        if sprinkler_type == 'dummy':
            add_sprinkler(sprinkler_name, TestSprinkler(sprinkler_name))
        elif sprinkler_type == 'gpio':
            gpio_address = int(details.pop(0))
            gpio_inverted = bool(strtobool(details.pop(0)))
            add_sprinkler(sprinkler_name, GpioSprinkler(
                    sprinkler_name, gpio_ctrl.get_outgoing_port(gpio_address, gpio_inverted)))
        else:
            raise RuntimeError(
                    'unknown sprinkler type "{0}" for sprinkler "{1}"'.format(
                    sprinkler_type, sprinkler_name))
