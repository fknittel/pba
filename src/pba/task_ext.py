# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
from twisted.internet import task
from twisted.internet import defer


def ignore_cancelled_error(failure):
    failure.trap(defer.CancelledError)


def defer_later(clock, delay, callback, *args, **kwargs):
    """Ignores cancellation errors"""
    timer = task.deferLater(clock, delay, callback, *args, **kwargs)
    timer.addErrback(ignore_cancelled_error)
    return timer
