from __future__ import print_function

import gpio
import weakref
import time
import copy
from twisted.internet import task
from twisted.internet import reactor
from twisted.internet import defer


class SprinklerException(Exception):
    pass


class NullInterceptor(object):
    def turn_on(self, sprinkler):
        sprinkler.turn_on()

    def turn_off(self, sprinkler):
        sprinkler.turn_off()

    def check_delay_activation(self):
        return False


class AbstractBaseInterceptor(object):
    def __init__(self):
        self.chained_interceptor = NullInterceptor()

    def check_delay_activation(self):
        return self.chained_interceptor.check_delay_activation()


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

    def check_delay_activation(self):
        if self._max_active_sprinklers_reached():
            return True
        return AbstractBaseInterceptor.check_delay_activation(self)


class StateVerificationInterceptor(AbstractBaseInterceptor):
    def __init__(self):
        AbstractBaseInterceptor.__init__(self)
        self._state = {}

    def turn_on(self, sprinkler):
        if self._state.get(sprinkler, False):
            raise SprinklerException('sprinkler {} already turned on'.format(sprinkler))
        self.chained_interceptor.turn_on(sprinkler)
        self._state[sprinkler] = True

    def turn_off(self, sprinkler):
        if not self._state.get(sprinkler, False):
            raise SprinklerException('sprinkler {} already turned off'.format(sprinkler))
        self.chained_interceptor.turn_off(sprinkler)
        self._state[sprinkler] = False


def ignore_cancelled_error(failure):
    failure.trap(defer.CancelledError)

def deferLater(clock, delay, callback, *args, **kwargs):
    timer = task.deferLater(clock, delay, callback, *args, **kwargs)
    timer.addErrback(ignore_cancelled_error)
    return timer


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
            max_remaining_runtime = min(max_remaining_runtime_for_duration, max_remaining_runtime)

        if max_remaining_runtime < 0:
            raise SprinklerException('sprinkler {} was already running for too long'.format(self._sprinkler_id))

        print('sprinkler {} will be stopped in {} secs'.format(self._sprinkler_id, max_remaining_runtime))
        self._timer = deferLater(self._clock, max_remaining_runtime,
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
        return self._interceptor.turn_off(self._sprinkler_to_port[sprinkler_id])

    def check_delay_activation(self):
        return self._interceptor.check_delay_activation()

    def is_valid(self, sprinkler_id):
        return sprinkler_id in self._sprinkler_to_port


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
    sprinkler_ctrl.add_interceptor(MaximumAverageRuntimeInterceptor(
            reactor,
            weakref.proxy(sprinkler_ctrl),
            max_runtimes=[
                (     60 * 60,     10 * 60),
                (12 * 60 * 60,     30 * 60),
                (24 * 60 * 60, 1 * 60 * 60),
            ]))
    sprinkler_ctrl.add_interceptor(GlobalMaximumOfActiveSprinklersInterceptor())
    sprinkler_ctrl.add_interceptor(StateVerificationInterceptor())


class Queue(object):
    def __init__(self):
        self._queue = []

    def push(self, item):
        self._queue.append(item)

    def is_empty(self):
        return len(self._queue) == 0

    def pop(self):
        return self._queue.pop(0)

    def remove(self, search_func):
        for idx, item in enumerate(self._queue):
            if search_func(item):
                del self._queue[idx]
                return item

    def list_all(self):
        return copy.deepcopy(self._queue)


class SprinklerJob(object):
    def __init__(self, job_id, sprinkler_id, duration):
        self.job_id = job_id
        self.sprinkler_id = sprinkler_id
        self.duration = duration

        self.start_time = None
        self.timer = None


class JobQueue(object):
    def __init__(self):
        self._queue = Queue()

    def push(self, job):
        self._queue.push(job)

    def is_empty(self):
        return self._queue.is_empty()

    def pop(self):
        return self._queue.pop()

    def remove(self, job_id):
        job = self._queue.remove(lambda x: x.job_id == job_id)
        if job is None:
            raise ValueError('job with id {} not found'.format(job_id))
        return job

    def list_all(self):
        return self._queue.list_all()


class SprinklerJobQueue(object):
    def __init__(self, clock, sprinkler_ctrl):
        self._clock = clock
        self._sprinkler_ctrl = sprinkler_ctrl
        self._last_job_id = 0
        self._waiting_jobs = JobQueue()
        self._active_jobs = JobQueue()

    def add(self, sprinkler_id, duration):
        if not self._sprinkler_ctrl.is_valid(sprinkler_id):
            raise RuntimeError('Invalid sprinkler id {}'.format(sprinkler_id))

        job_id = self._get_next_job_id()
        job = SprinklerJob(job_id, sprinkler_id, duration)
        self._waiting_jobs.push(job)
        self._attempt_next_job()
        return job_id

    def _get_next_job_id(self):
        self._last_job_id += 1
        return self._last_job_id

    def remove_waiting_job(self, job_id):
        self._waiting_jobs.remove(job_id)

    def list_waiting_jobs(self):
        return self._waiting_jobs.list_all()

    def _attempt_next_job(self):
        while not self._waiting_jobs.is_empty() and \
                not self._sprinkler_ctrl.check_delay_activation():
            job = self._waiting_jobs.pop()
            try:
                self._sprinkler_ctrl.turn_on(job.sprinkler_id)
            except SprinklerException, e:
                print('activating sprinkler failed: {}'.format(e))
                self._attempt_next_job()
                continue

            job.start_time = time.time()
            job.timer = deferLater(self._clock, job.duration,
                    self._on_end_of_duration, job)
            self._active_jobs.push(job)

    def remove_active_job(self, job_id):
        job = self._active_jobs.remove(job_id)
        job.timer.cancel()
        self._turn_off(job)

    def _on_end_of_duration(self, job):
        self._active_jobs.remove(job.job_id)
        self._turn_off(job)

    def _turn_off(self, job):
        try:
            self._sprinkler_ctrl.turn_off(job.sprinkler_id)
        except SprinklerException, e:
            print('deactivating sprinkler failed: {}'.format(e))
        self._attempt_next_job()

    def list_active_jobs(self):
        return self._active_jobs.list_all()


def main():
    gpio_ctrl = gpio.GpioController()
    sprinkler_ctrl = SprinklerController()
    sprinkler_job_queue = SprinklerJobQueue(reactor, sprinkler_ctrl)

    load_test_sprinklers(gpio_ctrl, sprinkler_ctrl)
    load_sprinkler_interceptors(sprinkler_ctrl)

    return sprinkler_job_queue
