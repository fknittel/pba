from __future__ import print_function

import os.path


class GpioController(object):
    GPIO_BASE_PATH = '/sys/class/gpio'

    def __init__(self, base_path=GPIO_BASE_PATH):
        self._base_path = base_path

    def export(self, port_id):
        with open(os.path.join(self._base_path, 'export'), 'w') as fp:
            fp.write(port_id)
        port_path = os.path.join(self._base_path, 'gpio{}'.format(port_id))
        return GpioPort(port_path=port_path)


class GpioPort(object):
    def __init__(self, port_path):
        self._port_path = port_path

        self._set_direction('out')

    def turn_on(self):
        print("activating port {}".format(self._port_path))
        self._set_value('1')

    def turn_off(self):
        print("deactivating port {}".format(self._port_path))
        self._set_value('0')

    def _set_value(self, value):
        self._write('value', value)

    def _set_direction(self, value):
        self._write('direction', value)

    def _write(self, variable_name, value):
        with open(os.path.join(self._port_path, variable_name), 'w') as fp:
            fp.write(value)
