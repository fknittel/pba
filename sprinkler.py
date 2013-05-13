from zope.interface import Interface, Attribute, implements
from twisted.internet import task
from twisted.internet import reactor

class PhysicalSprinkler(Interface):
    num = Attribute("""Sprinkler number (id).""")

    def turn_on():
        """Turns on the sprinkler"""

    def turn_off():
        """Turns off the sprinkler"""


class PhysicalSprinklerBoard(Interface):
    num_sprinklers = Attribute("""
            Number of sprinklers available""")

    def get_sprinkler(sprinklerNum):
        """Returns the :class:`Sprinkler`"""


class Sprinkler(Interface):
    num = Attribute("""Sprinkler number (id).""")

    def turn_on_for(secs):
        """Turns on the sprinkler"""

    def turn_off():
        """Turns off the sprinkler"""

    def set_event_listener(event_listener_fun):
        """Sets the event listener function to `event_listener_fun`."""


class TooManySprinklersActiveError(Exception):
    """Thrown when attempting to activate more sprinklers at the same time than
    the hardware can handle."""


class SprinklerService(Interface):
    num_sprinklers = Attribute("""
            Number of sprinklers available""")
    max_num_sprinklers_active = Attribute("""
            Maximum number of sprinklers that may be active at the same time.
            This is not necessarily the recommended number of sprinklers but
            instead the physical maximum which potentially already stresses the
            system.""")

    def turn_on_for(sprinkler_num, secs):
        """Turns on sprinkler with number `sprinkler_num` for `secs` seconds.
        Might throw :class:`TooManySprinklersActiveError`."""

    def turn_off(sprinkler_num):
        """Turns off sprinkler with number `sprinkler_num`.  Does nothing if
        the sprinkler wasn't on."""


#class SprinklerHistoryService(Interface):
#    """Provides the last sprinkler sprinkling times and durations."""


class PhysicalSprinklerImpl(object):
    implements(PhysicalSprinkler)

    def __init__(self, num):
        self.num = num

    def turn_on(self):
        print "Sprinkler {} ON".format(self.num)

    def turn_off(self):
        print "Sprinkler {} OFF".format(self.num)


class PhysicalSprinklerBoardImpl(object):
    implements(PhysicalSprinklerBoard)

    def __init__(self):
        self._sprinklers = [PhysicalSprinklerImpl(1), PhysicalSprinklerImpl(2),
                PhysicalSprinklerImpl(3)]

    @property
    def num_sprinklers(self):
        return len(self._sprinklers)

    def get_sprinkler(self, sprinkler_num):
        return self._sprinklers[sprinkler_num]


class SprinklerImpl(object):
    implements(Sprinkler)

    def __init__(self, sprinkler):
        self._sprinkler = sprinkler
        self._event_listener = None
        self._timer = None

    def turn_on_for(self, secs):
        if self._timer is not None:
            self._timer.cancel()
        self._timer = task.deferLater(reactor, secs, self._on_off)
        self._sprinkler.turn_on()
        self._notify_event_listener()

    def _on_off(self):
        self._sprinkler.turn_off()
        if self._timer is not None:
            self._timer = None
            self._notify_event_listener()

    def _notify_event_listener(self):
        if self._event_listener is not None:
            self._event_listener(self.num, self.is_on)

    def turn_off(self):
        if self._timer is not None:
            self._timer.cancel()
        self._on_off()

    def set_event_listener(self, event_listener_fun):
        self._event_listener = event_listener_fun

    @property
    def num(self):
        return self._sprinkler.num

    @property
    def is_on(self):
        return self._timer is not None


class SprinklerServiceImpl(object):
    implements(SprinklerService)

    def __init__(self):
        self._sprinklers = {}
        self._active_sprinklers = 0

    def add_sprinkler(self, sprinkler):
        self._sprinklers[sprinkler.num] = sprinkler
        sprinkler.set_event_listener(self._update_sprinkler_count)

    def _update_sprinkler_count(self, sprinkler_num, sprinkler_on):
        if not sprinkler_on:
            self._active_sprinklers -= 1

    def _check_max_active_sprinklers(self):
        if (self._active_sprinklers + 1) > self.max_num_sprinklers_active:
            raise TooManySprinklersActiveError

    @property
    def num_sprinklers(self):
        return len(self._sprinklers)

    @property
    def max_num_sprinklers_active(self):
        return 2

    def turn_on_for(self, sprinkler_num, secs):
        self._check_max_active_sprinklers()
        self._sprinklers[sprinkler_num].turn_on_for(secs)

    def turn_off(self, sprinkler_num):
        self._sprinklers[sprinkler_num].turn_off()


def sprinkler_loader(physical_sprinkler_board, sprinkler_service):
    for sprinkler_num in range(physical_sprinkler_board.num_sprinklers):
        physical_sprinkler = physical_sprinkler_board.get_sprinkler(sprinkler_num)
        sprinkler = SprinklerImpl(physical_sprinkler)
        sprinkler_service.add_sprinkler(sprinkler)

