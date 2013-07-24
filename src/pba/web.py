# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
from twisted.web import static, server, resource
from pba import daemon
import json


class JobsResource(resource.Resource):
    def __init__(self, job_queue):
        resource.Resource.__init__(self)
        self.job_queue = job_queue

        self.putChild('active', ActiveJobsResource(self.job_queue))
        self.putChild('waiting', WaitingJobsResource(self.job_queue))

    def render_POST(self, request):
        new_job = json.loads(request.content.getvalue())
        job_id = self.job_queue.add(new_job['sprinkler_id'],
                new_job['duration'], new_job['high_priority'])
        return json.dumps({'job_id': job_id})


class ActiveJobsResource(resource.Resource):
    isLeaf = True

    def __init__(self, job_queue):
        resource.Resource.__init__(self)
        self._job_queue = job_queue

    def render_GET(self, request):
        return json.dumps([job.for_json() for job \
                in self._job_queue.list_active_jobs()])


class WaitingJobsResource(resource.Resource):
    isLeaf = True

    def __init__(self, job_queue):
        resource.Resource.__init__(self)
        self._job_queue = job_queue

    def render_GET(self, request):
        return json.dumps([job.for_json() for job \
                in self._job_queue.list_waiting_jobs()])


def create_site(config):
    job_queue = daemon.main(config)

    root = static.File('wwwroot')
    root.putChild('jobs', JobsResource(job_queue))

    site = server.Site(root)
    return site
