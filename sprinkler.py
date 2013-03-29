from zope.interface import Interface, Attribute


class Sprinkler(Interface):
    num = Attribute("""Sprinkler number (id).""")

    def turn_on():
        """Turns on the sprinkler"""

    def turn_off():
        """Turns off the sprinkler"""


class SprinklerBoard(Interface):
    num_sprinklers = Attribute("""
            Number of sprinklers available""")

    def get_sprinkler(sprinklerNum):
        """Returns the :class:`Sprinkler`"""


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


class SprinklerHistoryService(Interface):
    """Provides the last sprinkler sprinkling times and durations."""


class ScheduledSprinkler(object):
    def __init__(self, sprinkler, event_listener):
        self._sprinkler = sprinkler
        self._event_listener = event_listener
        self._timer = None

    def turn_on_for(self, secs):
        if self._timer is not None:
            self._timer.cancel()
        self._timer = Timer(secs, self._on_off)
        self._sprinkler.turn_on()
        try:
            self._event_listener(self.num, self.is_on)
        finally:
            self._timer.start()

    def _on_off(self):
        self._sprinkler.turn_off()
        if self._timer is not None:
            self._timer = None
            self._event_listener(self)

    def turn_off(self, secs):
        if self._timer is not None:
            self._timer.cancel()
        self._on_off()

    @property
    def num(self):
        return self._sprinkler.num

    @property
    def is_on(self):
        return self._timer is not None


class SprinklerScheduler(object):
    def __init__(self):
        self.events = []

