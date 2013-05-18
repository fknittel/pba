from __future__ import print_function

import gpio
import weakref
from twisted.internet import task
from twisted.internet import reactor


class SprinklerException(Exception):
    pass


class NullInterceptor(object):
    def turn_on(self, sprinkler):
        sprinkler.turn_on()

    def turn_off(self, sprinkler):
        sprinkler.turn_off()


class AbstractBaseInterceptor(object):
    def __init__(self):
        self.child_interceptor = NullInterceptor()


class GlobalMaximumOfActiveSprinklersInterceptor(AbstractBaseInterceptor):
    def __init__(self, max_active_sprinklers=2):
        AbstractBaseInterceptor.__init__(self)
        self._max_active_sprinklers = max_active_sprinklers
        self._active_sprinklers = 0

    def turn_on(self, sprinkler):
        if self._active_sprinklers == self._max_active_sprinklers:
            raise SprinklerException(
                    'maximum number of active sprinklers exceeded')
        self.child_interceptor.turn_on(sprinkler)
        self._active_sprinklers += 1

    def turn_off(self, sprinkler):
        self.child_interceptor.turn_off(sprinkler)
        self._active_sprinklers -= 1


class StateVerificationInterceptor(AbstractBaseInterceptor):
    def __init__(self):
        AbstractBaseInterceptor.__init__(self)
        self._state = {}

    def turn_on(self, sprinkler):
        if self._state.get(sprinkler, False):
            raise SprinklerException('sprinkler {} already turned on'.format(sprinkler))
        self.child_interceptor.turn_on(sprinkler)
        self._state[sprinkler] = True

    def turn_off(self, sprinkler):
        if not self._state.get(sprinkler, False):
            raise SprinklerException('sprinkler {} already turned off'.format(sprinkler))
        self.child_interceptor.turn_off(sprinkler)
        self._state[sprinkler] = False


class MaximumRuntimeTracker(object):
    def __init__(self, sprinkler_id, sprinkler_ctrl, max_runtime_minutes):
        self._sprinkler_id = sprinkler_id
        self._sprinkler_ctrl = sprinkler_ctrl
        self._max_runtime_minutes = max_runtime_minutes
        self._timer = None

    def start(self):
        """Track sprinkler start event."""
        self._cancel()
        self._timer = task.deferLater(reactor, self._max_runtime_minutes * 60,
                self._on_timeout)

    def cancel(self):
        """Cancel the sprinkler start event."""
        self._cancel()

    def stop(self):
        """Track sprinkler stop event."""
        self._cancel()

    def _cancel(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _on_timeout(self):
        self._sprinkler_ctrl.turn_off(self._sprinkler_id)


class MaximumRuntimeInterceptor(AbstractBaseInterceptor):
    def __init__(self, sprinkler_ctrl, max_runtime_minutes=10):
        AbstractBaseInterceptor.__init__(self)
        self._sprinkler_ctrl = sprinkler_ctrl
        self._max_runtime_minutes = max_runtime_minutes
        self._sprinkler_tracker = {}

    def turn_on(self, sprinkler):
        if sprinkler not in self._sprinkler_tracker:
            self._sprinkler_tracker[sprinkler] = \
                    MaximumRuntimeTracker(sprinkler.sprinkler_id,
                            self._sprinkler_ctrl,
                            max_runtime_minutes=self._max_runtime_minutes)
        self._sprinkler_tracker[sprinkler].start() 
        try:
            self.child_interceptor.turn_on(sprinkler)
        except:
            self._sprinkler_tracker[sprinkler].cancel() 
            raise

    def turn_off(self, sprinkler):
        self.child_interceptor.turn_off(sprinkler)
        self._sprinkler_tracker[sprinkler].stop() 


class SprinklerController(object):
    def __init__(self):
        self._sprinkler_to_port = {}
        self._interceptor = NullInterceptor()

    def add_sprinkler(self, sprinkler_id, port):
        self._sprinkler_to_port[sprinkler_id] = port

    def add_interceptor(self, interceptor):
        interceptor.child_interceptor = self._interceptor
        self._interceptor = interceptor

    def turn_on(self, sprinkler_id):
        return self._interceptor.turn_on(self._sprinkler_to_port[sprinkler_id])

    def turn_off(self, sprinkler_id):
        return self._interceptor.turn_off(self._sprinkler_to_port[sprinkler_id])


def load_sprinklers(gpio_ctrl, sprinkler_ctrl):
    GPIO2_BASE = 2 * 32

    add_gpio_sprinkler(sprinkler_ctrl, 'court1', GPIO2_BASE +  6)
    add_gpio_sprinkler(sprinkler_ctrl, 'court2', GPIO2_BASE +  8)
    add_gpio_sprinkler(sprinkler_ctrl, 'court3', GPIO2_BASE + 10)
    add_gpio_sprinkler(sprinkler_ctrl, 'court4', GPIO2_BASE + 12)
    add_gpio_sprinkler(sprinkler_ctrl, 'court5', GPIO2_BASE + 23)
    add_gpio_sprinkler(sprinkler_ctrl, 'court6', GPIO2_BASE + 22)


def add_gpio_sprinkler(sprinkler_ctrl, sprinkler_id, gpio_port_nr):
    sprinkler_ctrl.add_sprinkler(sprinkler_id, GpioSprinkler(sprinkler_id, gpio_ctrl.get_outgoing_port(gpio_port_nr)))


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
    sprinkler_ctrl.add_interceptor(MaximumRuntimeInterceptor(weakref.proxy(sprinkler_ctrl)))
    sprinkler_ctrl.add_interceptor(GlobalMaximumOfActiveSprinklersInterceptor())
    sprinkler_ctrl.add_interceptor(StateVerificationInterceptor())

def main():
    gpio_ctrl = gpio.GpioController()
    sprinkler_ctrl = SprinklerController()

    load_test_sprinklers(gpio_ctrl, sprinkler_ctrl)
    load_sprinkler_interceptors(sprinkler_ctrl)

    return sprinkler_ctrl
