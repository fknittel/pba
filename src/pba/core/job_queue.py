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


class SprinklerJob(object):
    def __init__(self, job_id, sprinkler_id, duration, high_priority=False):
        self.job_id = job_id
        self.sprinkler_id = sprinkler_id
        self.duration = duration
        self.high_priority = high_priority

        self.start_time = None
        self.timer = None

    def for_json(self):
        return {
            'job_id': self.job_id,
            'sprinkler_id': self.sprinkler_id,
            'duration': self.duration,
            'high_priority': self.high_priority,
            'start_time': self.start_time,
        }


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
        job = self._queue.remove(lambda x: x.job_id == job_id)
        if job is None:
            raise ValueError('job with id {} not found'.format(job_id))
        return job

    def list_all(self):
        return self._queue.list_all()


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

        job_id = self._get_next_job_id()
        job = SprinklerJob(job_id, sprinkler_id, duration, high_priority)
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

            job.start_time = time.time()
            job.timer = defer_later(self._clock, job.duration,
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
        except SprinklerException as e:
            print('deactivating sprinkler failed: {}'.format(e))
        self._attempt_next_job()

    def list_active_jobs(self):
        return self._active_jobs.list_all()
