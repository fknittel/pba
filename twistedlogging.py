# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
from twisted.application.service import MultiService
from twisted.python.log import ILogObserver


class LogObserverInjectingMultiService(MultiService):
    """MultiService that needs to be the parent service (so that the
    application object is accessible) and allows the application
    object to be configured regarding the ILogObserver.
    """
    def __init__(self, observer, *args, **kwargs):
        MultiService.__init__(self, *args, **kwargs)
        self._observer = observer

    def setServiceParent(self, parent):
        MultiService.setServiceParent(self, parent)
        parent.setComponent(ILogObserver, self._observer)
