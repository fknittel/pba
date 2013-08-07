# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
import time
import copy
from pba.core.controller import SprinklerException
from pba.core.task_ext import defer_later


class Queue(object):
    def __init__(self):
        self._queue = []

    def push(self, item):
        self._queue.append(item)

    def is_empty(self):
        return len(self._queue) == 0

    def peek(self):
        return self._queue[0]

    def pop(self):
        return self._queue.pop(0)

    def remove(self, search_func):
        for idx, item in enumerate(self._queue):
            if search_func(item):
                del self._queue[idx]
                return item

    def list_all(self):
        return copy.deepcopy(self._queue)

    def find(self, match_func):
        for _, item in enumerate(self._queue):
            if match_func(item):
                return item
        return None


class SprinklerJob(object):
    JOB_WAITING = 'waiting'
    JOB_ACTIVE = 'active'
    JOB_FINISHED = 'finished'
    JOB_CANCELLED = 'cancelled'

    def __init__(self, clock, job_id, sprinkler_id, duration,
            high_priority=False):
        self._clock = clock
        self.job_id = job_id
        self.sprinkler_id = sprinkler_id
        self._duration = duration
        self.high_priority = high_priority

        self.status = self.JOB_WAITING
        self.start_time = None
        self.stop_time = None
        self.timer = None
        self.on_stop = None
        self.on_finished = None

    def __getstate__(self):
        state = dict(self.__dict__)
        del state['_clock']
        return state

    def for_json(self):
        return {
            'job_id': self.job_id,
            'sprinkler_id': self.sprinkler_id,
            'duration': self.duration,
            'high_priority': self.high_priority,
            'start_time': self.start_time,
            'remaining_time': self.remaining_time,
            'stop_time': self.stop_time,
            'status': self.status,
        }

    @property
    def remaining_time(self):
        if self.status != self.JOB_ACTIVE:
            return None
        return (self.start_time + self.duration) - time.time()

    def _get_duration(self):
        return self._duration

    def _set_duration(self, duration):
        self._duration = duration
        if self.timer is not None:
            remaining_time = self.remaining_time
            if remaining_time > 0:
                self.timer.cancel()
                self._start_timer_with_duration(self.remaining_time)
            else:
                self.cancel()

    duration = property(_get_duration, _set_duration)

    def start(self):
        print('starting job {}'.format(self.job_id))
        self.start_time = time.time()
        self.status = self.JOB_ACTIVE
        self._start_timer_with_duration(self.duration)

    def _start_timer_with_duration(self, duration):
        self.timer = defer_later(self._clock, duration,
                lambda _: self._on_finished(), self)

    def _on_finished(self):
        self.status = self.JOB_FINISHED
        self.stop_time = time.time()
        self.timer = None

        self.on_finished()
        self.on_stop()

    def cancel(self):
        self.status = self.JOB_CANCELLED
        self.stop_time = time.time()
        self.timer.cancel()
        self.timer = None

        self.on_stop()


class MaxActiveSprinklerJobPolicy(object):
    def __init__(self, max_total, max_low_priority):
        self._max_total = max_total
        self._max_low_priority = max_low_priority

    def is_job_runnable(self, job, waiting_jobs, active_jobs):
        if self._max_total <= len(active_jobs):
            return False
        if job.high_priority:
            return True

        num_jobs_low_priority = len([job for job in active_jobs \
                if not job.high_priority])
        return self._max_low_priority > num_jobs_low_priority


class JobQueue(object):
    def __init__(self):
        self._queue = Queue()

    def push(self, job):
        self._queue.push(job)

    def is_empty(self):
        return self._queue.is_empty()

    def peek(self):
        return self._queue.peek()

    def pop(self):
        return self._queue.pop()

    def remove(self, job_id):
        job = self._queue.remove(lambda job: job.job_id == job_id)
        if job is None:
            raise ValueError('job with id {} not found'.format(job_id))
        return job

    def list_all(self):
        return self._queue.list_all()

    def __contains__(self, job_id):
        return self.get(job_id) is not None

    def get(self, job_id):
        return self._queue.find(lambda job: job.job_id == job_id)


class PriorityJobQueue(object):
    def __init__(self):
        self._queues = []

    def _get_queue_for(self, job):
        priority = 1 if job.high_priority else 0

        last_position = 0
        for queue_priority, queue in self._queues:
            if queue_priority == priority:
                return queue
            if queue_priority < priority:
                break
            last_position += 1

        new_queue = JobQueue()
        self._queues.insert(last_position, (priority, new_queue))
        return new_queue

    def push(self, job):
        self._get_queue_for(job).push(job)

    def _get_first_nonempty_queue(self, default=JobQueue()):
        for _, queue in self._queues:
            if not queue.is_empty():
                return queue
        return default

    def is_empty(self):
        return self._get_first_nonempty_queue().is_empty()

    def peek(self):
        return self._get_first_nonempty_queue().peek()

    def pop(self):
        return self._get_first_nonempty_queue().pop()

    def remove(self, job_id):
        for _, queue in self._queues:
            job = queue.remove(job_id)
            if job is not None:
                return job
        raise ValueError('job with id {} not found'.format(job_id))

    def list_all(self):
        return reduce(lambda jobs, queue: jobs + queue[1].list_all(),
                self._queues, [])

    def __contains__(self, job_id):
        for _, queue in self._queues:
            if job_id in queue:
                return True
        return False

    def get(self, job_id):
        for _, queue in self._queues:
            job = queue.get(job_id)
            if job is not None:
                return job

class SprinklerJobQueue(object):
    def __init__(self, clock, sprinkler_ctrl, queue_policy):
        self._clock = clock
        self._sprinkler_ctrl = sprinkler_ctrl
        self._queue_policy = queue_policy
        self._last_job_id = 0
        self._waiting_jobs = PriorityJobQueue()
        self._active_jobs = JobQueue()

    def add(self, sprinkler_id, duration, high_priority=False):
        if not self._sprinkler_ctrl.is_valid(sprinkler_id):
            raise RuntimeError('Invalid sprinkler id {}'.format(sprinkler_id))
        if duration is None or duration <= 0:
            raise RuntimeError('Invalid duration "{}", ' \
                    'needs to be greater than 0'.format(duration))

        job_id = self._get_next_job_id()
        job = SprinklerJob(self._clock, job_id, sprinkler_id, duration,
                high_priority)
        job.on_stop = lambda: self._turn_off(job)
        job.on_finished = lambda: self._on_end_of_duration(job)
        self._waiting_jobs.push(job)
        self._attempt_next_job()
        return job_id

    def _get_next_job_id(self):
        self._last_job_id += 1
        return self._last_job_id

    def remove_waiting_job(self, job_id):
        return self._waiting_jobs.remove(job_id)

    def list_waiting_jobs(self):
        return self._waiting_jobs.list_all()

    def _attempt_next_job(self):
        while not self._waiting_jobs.is_empty():
            job = self._waiting_jobs.peek()
            if not self._queue_policy.is_job_runnable(job,
                    waiting_jobs=self.list_waiting_jobs(),
                    active_jobs=self.list_active_jobs()):
                break
            self._waiting_jobs.pop()
            try:
                self._sprinkler_ctrl.turn_on(job.sprinkler_id)
            except SprinklerException as e:
                print('activating sprinkler failed: {}'.format(e))
                self._attempt_next_job()
                continue

            job.start()
            self._active_jobs.push(job)

    def remove_active_job(self, job_id):
        job = self._active_jobs.remove(job_id)
        job.cancel()
        return job

    def _on_end_of_duration(self, job):
        self._active_jobs.remove(job.job_id)

    def _turn_off(self, job):
        try:
            self._sprinkler_ctrl.turn_off(job.sprinkler_id)
        except SprinklerException as e:
            print('deactivating sprinkler failed: {}'.format(e))
        self._attempt_next_job()

    def list_active_jobs(self):
        return self._active_jobs.list_all()

    def is_job_active(self, job_id):
        return job_id in self._active_jobs

    def is_job_waiting(self, job_id):
        return job_id in self._waiting_jobs

    def get_waiting_job(self, job_id):
        return self._waiting_jobs.get(job_id)

    def get_active_job(self, job_id):
        return self._active_jobs.get(job_id)

    def get_job(self, job_id):
        job = self.get_active_jobs(job_id)
        if job is not None:
            return job
        return self.get_waiting_jobs(job_id)

    def list_jobs(self):
        return self.list_active_jobs() + self.list_waiting_jobs()
