# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)

import os.path


class GpioController(object):
    GPIO_BASE_PATH = '/sys/class/gpio'

    def __init__(self, base_path=GPIO_BASE_PATH):
        self._base_path = base_path

    def get_outgoing_port(self, port_id):
        return GpioOutPort(base_path=self._base_path, port_id=port_id)


class GpioOutPort(object):
    def __init__(self, base_path, port_id):
	self._base_path = base_path
	self._port_id = port_id
        self._state = False

    @property
    def is_exported(self):
        return os.path.exists(self._port_path)

    @property
    def _port_path(self):
        return os.path.join(self._base_path, 'gpio{}'.format(self._port_id))

    def export(self):
        with open(os.path.join(self._base_path, 'export'), 'w') as fp:
            fp.write('{}'.format(self._port_id))
        self.set_direction('out')

    def turn_on(self):
        print("activating port {}".format(self._port_path))
        self._set_value('1')
        self._state = True

    def turn_off(self):
        print("deactivating port {}".format(self._port_path))
        self._set_value('0')
        self._state = False

    def toggle(self):
        if self._state:
            self.turn_off()
        else:
            self.turn_on()

    def _set_value(self, value):
        self._write('value', value)

    def set_direction(self, value):
        self._write('direction', value)

    def _write(self, variable_name, value):
        with open(os.path.join(self._port_path, variable_name), 'w') as fp:
            fp.write(value)
