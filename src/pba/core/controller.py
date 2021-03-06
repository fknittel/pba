# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
import time
from pba.core.task_ext import defer_later


class SprinklerException(Exception):
    pass


class NullInterceptor(object):
    def turn_on(self, sprinkler):
        sprinkler.turn_on()

    def turn_off(self, sprinkler):
        sprinkler.turn_off()


class AbstractBaseInterceptor(object):
    def __init__(self):
        self.chained_interceptor = NullInterceptor()


class GlobalMaximumOfActiveSprinklersInterceptor(AbstractBaseInterceptor):
    def __init__(self, max_active_sprinklers=2):
        AbstractBaseInterceptor.__init__(self)
        self._max_active_sprinklers = max_active_sprinklers
        self._active_sprinklers = 0

    def turn_on(self, sprinkler):
        if self._max_active_sprinklers_reached():
            raise SprinklerException(
                    'maximum number of active sprinklers exceeded')
        self.chained_interceptor.turn_on(sprinkler)
        self._active_sprinklers += 1

    def turn_off(self, sprinkler):
        self.chained_interceptor.turn_off(sprinkler)
        self._active_sprinklers -= 1

    def _max_active_sprinklers_reached(self):
        return self._active_sprinklers == self._max_active_sprinklers


class StateVerificationInterceptor(AbstractBaseInterceptor):
    def __init__(self):
        AbstractBaseInterceptor.__init__(self)
        self._state = {}

    def turn_on(self, sprinkler):
        if self._state.get(sprinkler, False):
            raise SprinklerException('sprinkler {} already turned on'.format(
                    sprinkler))
        self.chained_interceptor.turn_on(sprinkler)
        self._state[sprinkler] = True

    def turn_off(self, sprinkler):
        if not self._state.get(sprinkler, False):
            raise SprinklerException('sprinkler {} already turned off'.format(
                    sprinkler))
        self.chained_interceptor.turn_off(sprinkler)
        self._state[sprinkler] = False


class MaximumAverageRuntimeTracker(object):
    TWENTY_FOUR_HOURS_IN_SECS = 24 * 60 * 60

    def __init__(self, clock, sprinkler_id, sprinkler_ctrl, max_runtimes):
        self._clock = clock
        self._sprinkler_id = sprinkler_id
        self._sprinkler_ctrl = sprinkler_ctrl
        self._max_runtimes = max_runtimes
        self._timer = None
        self._historic_runtimes = []
        self._start_time = None

    def start(self):
        """Track sprinkler start event."""
        self._cancel()
        max_remaining_runtime = None
        for duration, max_runtime in self._max_runtimes:
            last_runtime = self._calculate_runtime_for(duration)
            max_remaining_runtime_for_duration = max_runtime - last_runtime
            if max_remaining_runtime is None:
                max_remaining_runtime = max_remaining_runtime_for_duration
            max_remaining_runtime = min(max_remaining_runtime_for_duration,
                     max_remaining_runtime)

        if max_remaining_runtime < 0:
            raise SprinklerException(
                    'sprinkler {} was already running for too long'.format(
                            self._sprinkler_id))

        print('sprinkler {} will be stopped in {} seconds'.format(
                self._sprinkler_id, max_remaining_runtime))
        self._timer = defer_later(self._clock, max_remaining_runtime,
                self._on_timeout)
        self._start_time = time.time()

    def _max_remaining_runtime(self, since):
        last_runtime = self._calculate_duration_for(since)
        max_remaining_runtime = self._max_runtime_secs - last_runtime
        return max_remaining_runtime

    def cancel(self):
        """Cancel the sprinkler start event."""
        self._cancel()

    def stop(self):
        """Track sprinkler stop event."""
        self._cancel()
        self._record_runtime()

    def _record_runtime(self):
        end_time = time.time()
        runtime = end_time - self._start_time
        print("Recording end runtime: {0}, {1}".format(end_time, runtime))
        self._historic_runtimes.append((end_time, runtime))
        self._start_time = None
        self._clean_history()

    def _calculate_runtime_for(self, duration):
        last_relevant_timestamp = time.time() - duration
        return sum([runtime \
                for end_time, runtime \
                in self._historic_runtimes \
                if end_time >= last_relevant_timestamp])

    def _clean_history(self):
        last_relevant_timestamp = time.time() - self.TWENTY_FOUR_HOURS_IN_SECS
        self._historic_runtimes = [(end_time, runtime) \
                for end_time, runtime \
                in self._historic_runtimes \
                if end_time >= last_relevant_timestamp]

    def _cancel(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _on_timeout(self):
        self._sprinkler_ctrl.turn_off(self._sprinkler_id)


class MaximumAverageRuntimeInterceptor(AbstractBaseInterceptor):
    def __init__(self, clock, sprinkler_ctrl, max_runtimes):
        AbstractBaseInterceptor.__init__(self)
        self._clock = clock
        self._sprinkler_ctrl = sprinkler_ctrl
        self._max_runtimes = max_runtimes
        self._sprinkler_tracker = {}

    def turn_on(self, sprinkler):
        if sprinkler not in self._sprinkler_tracker:
            self._sprinkler_tracker[sprinkler] = \
                    MaximumAverageRuntimeTracker(self._clock,
                            sprinkler.sprinkler_id,
                            self._sprinkler_ctrl,
                            max_runtimes=self._max_runtimes)
        self._sprinkler_tracker[sprinkler].start()
        try:
            self.chained_interceptor.turn_on(sprinkler)
        except:
            self._sprinkler_tracker[sprinkler].cancel()
            raise

    def turn_off(self, sprinkler):
        self.chained_interceptor.turn_off(sprinkler)
        self._sprinkler_tracker[sprinkler].stop()


class SprinklerController(object):
    def __init__(self):
        self._sprinkler_to_port = {}
        self._interceptor = NullInterceptor()

    def add_sprinkler(self, sprinkler_id, port):
        self._sprinkler_to_port[sprinkler_id] = port

    def add_interceptor(self, interceptor):
        interceptor.chained_interceptor = self._interceptor
        self._interceptor = interceptor

    def turn_on(self, sprinkler_id):
        return self._interceptor.turn_on(self._sprinkler_to_port[sprinkler_id])

    def turn_off(self, sprinkler_id):
        return self._interceptor.turn_off(
                self._sprinkler_to_port[sprinkler_id])

    def is_valid(self, sprinkler_id):
        return sprinkler_id in self._sprinkler_to_port

    @property
    def sprinkler_ids(self):
        return self._sprinkler_to_port.keys()
