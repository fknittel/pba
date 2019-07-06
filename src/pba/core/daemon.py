# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
import sys
from pba.core import gpio
from twisted.internet import reactor
import weakref
from pba.core.controller import MaximumAverageRuntimeInterceptor, \
    GlobalMaximumOfActiveSprinklersInterceptor, StateVerificationInterceptor, \
    SprinklerController
from pba.core.job_queue import MaxActiveSprinklerJobPolicy, SprinklerJobQueue
from ConfigParser import SafeConfigParser
from pba.core.sprinkler_config import load_sprinklers


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


def main(config):
    gpio_ctrl = gpio.GpioController()
    sprinkler_ctrl = SprinklerController()
    queue_policy = MaxActiveSprinklerJobPolicy(max_total=2, max_low_priority=1)
    sprinkler_job_queue = SprinklerJobQueue(reactor, sprinkler_ctrl,
            queue_policy)

    load_sprinklers(config, gpio_ctrl,
            lambda sprinkler_name, sprinkler: sprinkler_ctrl.add_sprinkler(sprinkler_name, sprinkler))
    load_sprinkler_interceptors(sprinkler_ctrl)

    return sprinkler_job_queue, sprinkler_ctrl


if __name__ == '__main__':
    config = SafeConfigParser()
    config.read(sys.argv[1])
    main(config)
