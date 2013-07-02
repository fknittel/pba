# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
import gpio
from twisted.internet import reactor
import weakref
from controller import MaximumAverageRuntimeInterceptor, \
    GlobalMaximumOfActiveSprinklersInterceptor, StateVerificationInterceptor, \
    SprinklerController
from job_queue import MaxActiveSprinklerJobPolicy, SprinklerJobQueue


def load_sprinklers(gpio_ctrl, sprinkler_ctrl):
    GPIO0_BASE = 0 * 32
    GPIO2_BASE = 2 * 32

    add_gpio_sprinkler(gpio_ctrl, sprinkler_ctrl, 'court1', GPIO2_BASE + 25)
    add_gpio_sprinkler(gpio_ctrl, sprinkler_ctrl, 'court2', GPIO2_BASE + 24)
    add_gpio_sprinkler(gpio_ctrl, sprinkler_ctrl, 'court3', GPIO2_BASE + 1)
    add_gpio_sprinkler(gpio_ctrl, sprinkler_ctrl, 'court4', GPIO0_BASE + 27)
    add_gpio_sprinkler(gpio_ctrl, sprinkler_ctrl, 'court5', GPIO2_BASE + 23)
    add_gpio_sprinkler(gpio_ctrl, sprinkler_ctrl, 'court6', GPIO2_BASE + 22)


def add_gpio_sprinkler(gpio_ctrl, sprinkler_ctrl, sprinkler_id, gpio_port_nr):
    sprinkler_ctrl.add_sprinkler(sprinkler_id, GpioSprinkler(sprinkler_id,
            gpio_ctrl.get_outgoing_port(gpio_port_nr)))


class TestSprinkler(object):
    def __init__(self, sprinkler_id):
        self.sprinkler_id = sprinkler_id

    def turn_on(self):
        print("turning on sprinkler {}".format(self.sprinkler_id))

    def turn_off(self):
        print("turning off sprinkler {}".format(self.sprinkler_id))


class GpioSprinkler(object):
    def __init__(self, sprinkler_id, gpio_port):
        self.sprinkler_id = sprinkler_id
        self._gpio_port = gpio_port

    def turn_on(self):
        self._gpio_port.turn_on()

    def turn_off(self):
        self._gpio_port.turn_off()


def load_test_sprinklers(gpio_ctrl, sprinkler_ctrl):
    sprinkler_ctrl.add_sprinkler('court1', TestSprinkler('court1'))
    sprinkler_ctrl.add_sprinkler('court2', TestSprinkler('court2'))
    sprinkler_ctrl.add_sprinkler('court3', TestSprinkler('court3'))
    sprinkler_ctrl.add_sprinkler('court4', TestSprinkler('court4'))
    sprinkler_ctrl.add_sprinkler('court5', TestSprinkler('court5'))
    sprinkler_ctrl.add_sprinkler('court6', TestSprinkler('court6'))


def load_sprinkler_interceptors(sprinkler_ctrl):
    sprinkler_ctrl.add_interceptor(MaximumAverageRuntimeInterceptor(
            reactor,
            weakref.proxy(sprinkler_ctrl),
            max_runtimes=[
                (60 * 60, 10 * 60),
                (12 * 60 * 60, 30 * 60),
                (24 * 60 * 60, 1 * 60 * 60),
            ]))
    sprinkler_ctrl.add_interceptor(
            GlobalMaximumOfActiveSprinklersInterceptor())
    sprinkler_ctrl.add_interceptor(
            StateVerificationInterceptor())


def main():
    gpio_ctrl = gpio.GpioController()
    sprinkler_ctrl = SprinklerController()
    queue_policy = MaxActiveSprinklerJobPolicy(max_total=2, max_low_priority=1)
    sprinkler_job_queue = SprinklerJobQueue(reactor, sprinkler_ctrl,
            queue_policy)

    load_test_sprinklers(gpio_ctrl, sprinkler_ctrl)
    load_sprinkler_interceptors(sprinkler_ctrl)

    return sprinkler_job_queue

if __name__ == '__main__':
    main()
