from zope.interface import Interface, Attribute

class Sprinkler(Interface):
    def turnOn():
        """Turns on the sprinkler"""

    def turnOff():
        """Turns off the sprinkler"""

class SprinklerBoard(Interface):
    numSprinklers = Attribute("""
            Number of sprinklers available""")

    def getSprinkler(sprinklerNum):
        """Returns the :class:`Sprinkler`"""


class TooManySprinklersActiveError(Exception):
    """Thrown when attempting to activate more sprinklers at the same time than
    the hardware can handle."""

class SprinklerService(Interface):
    numSprinklers = Attribute("""
            Number of sprinklers available""")
    maxNumSprinklersActive = Attribute("""
            Maximum number of sprinklers that may be active at the same time.
            This is not necessarily the recommended number of sprinklers but
            instead the physical maximum which potentially already stresses the
            system."""

    def turnOn(int sprinklerNum):
        """Turns on sprinkler with number sprinklerNum. Might throw
        :class:`TooManySprinklersActiveError`."""

    def turnOff(int sprinklerNum):
        """Turns off sprinkler with number sprinklerNum"""
