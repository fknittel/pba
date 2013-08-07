# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
from twisted.web import static, server, resource
from pba.core import daemon
import json


def json_response(request, raw_response):
        request.setHeader(b'Content-Type',
                b'application/json')
        return json.dumps(raw_response)


class JobsResource(resource.Resource):
    def __init__(self, job_queue):
        resource.Resource.__init__(self)
        self._job_queue = job_queue

        self.putChild('active', ActiveJobsResource(self._job_queue))
        self.putChild('waiting', WaitingJobsResource(self._job_queue))

    def render_POST(self, request):
        new_job = json.loads(request.content.getvalue())
        job_id = self._job_queue.add(new_job['sprinkler_id'],
                new_job['duration'], new_job['high_priority'])
        return json_response(request, {'job_id': job_id})

    def render_GET(self, request):
        return json_response(request, [job.for_json() for job \
                in self._job_queue.list_jobs()])

    def getChild(self, path, request): 
        job_id = int(path)
        if self._job_queue.is_job_active(job_id):
            return ActiveJobResource(job_queue=self._job_queue,
                    job_id=job_id)
        return WaitingJobResource(job_queue=self._job_queue, job_id=job_id)


def court_status_from_jobs(sprinkler_id, jobs):
    for job in jobs:
        if job.sprinkler_id == sprinkler_id:
            return job.for_json()
    return {'sprinkler_id': sprinkler_id,
            'status': 'inactive',
            }


class CourtsResource(resource.Resource):
    def __init__(self, sprinkler_ctrl, job_queue):
        resource.Resource.__init__(self)
        self._sprinkler_ctrl = sprinkler_ctrl
        self._job_queue = job_queue

    def render_GET(self, request):
        jobs = self._job_queue.list_jobs()
        courts = []
        for sprinkler_id in sorted(self._sprinkler_ctrl.sprinkler_ids):
            courts.append(court_status_from_jobs(sprinkler_id, jobs))
        return json_response(request, courts)

    def getChild(self, court_id, request): 
        return CourtResource(court_id, self._job_queue)


class CourtResource(resource.Resource):
    def __init__(self, court_id, job_queue):
        resource.Resource.__init__(self)
        self._court_id = court_id
        self._job_queue = job_queue

    def render_GET(self, request):
        jobs = self._job_queue.list_jobs()
        return json_response(request, court_status_from_jobs(self._court_id,
            jobs))


class ActiveJobsResource(resource.Resource):
    def __init__(self, job_queue):
        resource.Resource.__init__(self)
        self._job_queue = job_queue

    def render_GET(self, request):
        return json_response(request, [job.for_json() for job \
                in self._job_queue.list_active_jobs()])

    def getChild(self, path, request): 
        return ActiveJobResource(job_queue=self._job_queue, job_id=int(path))


class ActiveJobResource(resource.Resource):
    def __init__(self, job_queue, job_id):
        resource.Resource.__init__(self)
        self._job_queue = job_queue
        self._job_id = job_id

    def render_GET(self, request):
        job = self._job_queue.get_active_job(self._job_id)
        return json_response(request, job.for_json())

    def render_DELETE(self, request):
        self._job_queue.remove_active_job(self._job_id)
        return b''

    def render_POST(self, request):
        modified_job = json.loads(request.content.getvalue())

        job = self._job_queue.get_active_job(self._job_id)
        job.duration = modified_job['duration']
        return json_response(request, job.for_json())


class WaitingJobsResource(resource.Resource):
    def __init__(self, job_queue):
        resource.Resource.__init__(self)
        self._job_queue = job_queue

    def render_GET(self, request):
        return json_response(request, [job.for_json() for job \
                in self._job_queue.list_waiting_jobs()])

    def getChild(self, path, request): 
        return WaitingJobResource(job_queue=self._job_queue, job_id=int(path))


class WaitingJobResource(resource.Resource):
    def __init__(self, job_queue, job_id):
        resource.Resource.__init__(self)
        self._job_queue = job_queue
        self._job_id = job_id

    def render_GET(self, request):
        job = self._job_queue.get_waiting_job(self._job_id)
        return json_response(request, job.for_json())

    def render_DELETE(self, request):
        self._job_queue.remove_waiting_job(self._job_id)
        return b''

    def render_POST(self, request):
        modified_job = json.loads(request.content.getvalue())

        job = self._job_queue.get_waiting_job(self._job_id)
        job.duration = modified_job['duration']
        return json_response(request, job.for_json())


def create_site(config):
    job_queue, sprinkler_ctrl = daemon.main(config)

    root = static.File('wwwroot')
    root.putChild('jobs', JobsResource(job_queue))
    root.putChild('courts', CourtsResource(sprinkler_ctrl, job_queue))

    site = server.Site(root)
    return site
