# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
import logging

GPIO_BASES = {
        'GPIO0_BASE': 0 * 32,
        'GPIO1_BASE': 1 * 32,
        'GPIO2_BASE': 2 * 32,
        'GPIO3_BASE': 3 * 32,
    }
log = logging.getLogger(__name__)


class TestSprinkler(object):
    def __init__(self, sprinkler_id):
        self.sprinkler_id = sprinkler_id

    def turn_on(self):
        log.info("turning on sprinkler {}".format(self.sprinkler_id))

    def turn_off(self):
        log.info("turning off sprinkler {}".format(self.sprinkler_id))


class GpioSprinkler(object):
    def __init__(self, sprinkler_id, gpio_port):
        self.sprinkler_id = sprinkler_id
        self._gpio_port = gpio_port

    def turn_on(self):
        self._gpio_port.turn_on()

    def turn_off(self):
        self._gpio_port.turn_off()


def load_sprinklers(config, gpio_ctrl, sprinkler_ctrl):
    for sprinkler_name, value in config.items('sprinklers'):
        details = value.split()
        sprinkler_type = details.pop(0)
        log.info('adding sprinkler {0} of type {1}'.format(sprinkler_name,
                sprinkler_type))
        if sprinkler_type == 'dummy':
            sprinkler_ctrl.add_sprinkler(sprinkler_name,
                    TestSprinkler(sprinkler_name))
        elif sprinkler_type == 'gpio':
            gpio_base = details.pop(0)
            gpio_offset = int(details.pop(0))
            gpio_address = GPIO_BASES[gpio_base] + gpio_offset
            sprinkler_ctrl.add_sprinkler(sprinkler_name, GpioSprinkler(
                    sprinkler_name, gpio_ctrl.get_outgoing_port(gpio_address)))
        else:
            raise RuntimeError(
                    'unknown sprinkler type "{0}" for sprinkler "{1}"'.format(
                    sprinkler_type, sprinkler_name))
