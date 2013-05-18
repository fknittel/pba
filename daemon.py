from __future__ import print_function

import gpio


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
        self._assure_state_prepared(sprinkler)
        if self._state[sprinkler]:
            raise SprinklerException('sprinkler {} already turned on'.format(sprinkler))
        self.child_interceptor.turn_on(sprinkler)
        self._state[sprinkler] = True

    def turn_off(self, sprinkler):
        self._assure_state_prepared(sprinkler)
        if not self._state[sprinkler]:
            raise SprinklerException('sprinkler {} already turned off'.format(sprinkler))
        self.child_interceptor.turn_off(sprinkler)
        self._state[sprinkler] = False

    def _assure_state_prepared(self, sprinkler):
        if not sprinkler in self._state:
            self._state[sprinkler] = False


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

    sprinkler_ctrl.add_sprinkler('court1', gpio_ctrl.get_outgoing_port(GPIO2_BASE +  6))
    sprinkler_ctrl.add_sprinkler('court2', gpio_ctrl.get_outgoing_port(GPIO2_BASE +  8))
    sprinkler_ctrl.add_sprinkler('court3', gpio_ctrl.get_outgoing_port(GPIO2_BASE + 10))
    sprinkler_ctrl.add_sprinkler('court4', gpio_ctrl.get_outgoing_port(GPIO2_BASE + 12))
    sprinkler_ctrl.add_sprinkler('court5', gpio_ctrl.get_outgoing_port(GPIO2_BASE + 23))
    sprinkler_ctrl.add_sprinkler('court6', gpio_ctrl.get_outgoing_port(GPIO2_BASE + 22))


class TestSprinkler(object):
    def __init__(self, sprinkler_id):
        self.sprinkler_id = sprinkler_id

    def turn_on(self):
        print("turning on sprinkler {}".format(self.sprinkler_id))

    def turn_off(self):
        print("turning off sprinkler {}".format(self.sprinkler_id))


def load_test_sprinklers(gpio_ctrl, sprinkler_ctrl):
    sprinkler_ctrl.add_sprinkler('court1', TestSprinkler('court1'))
    sprinkler_ctrl.add_sprinkler('court2', TestSprinkler('court2'))
    sprinkler_ctrl.add_sprinkler('court3', TestSprinkler('court3'))
    sprinkler_ctrl.add_sprinkler('court4', TestSprinkler('court4'))
    sprinkler_ctrl.add_sprinkler('court5', TestSprinkler('court5'))
    sprinkler_ctrl.add_sprinkler('court6', TestSprinkler('court6'))


def load_sprinkler_interceptors(sprinkler_ctrl):
    sprinkler_ctrl.add_interceptor(GlobalMaximumOfActiveSprinklersInterceptor())
    sprinkler_ctrl.add_interceptor(StateVerificationInterceptor())

def main():
    gpio_ctrl = gpio.GpioController()
    sprinkler_ctrl = SprinklerController()

    load_test_sprinklers(gpio_ctrl, sprinkler_ctrl)
    load_sprinkler_interceptors(sprinkler_ctrl)

    return sprinkler_ctrl
