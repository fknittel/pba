from twisted.web import server, resource
from twisted.application import internet, service
import daemon
import json


class RootResource(resource.Resource):
    pass


class JobsResource(resource.Resource):
    def __init__(self, job_queue):
        resource.Resource.__init__(self)
        self.putChild('active', ActiveJobsResource(job_queue))
        self.putChild('waiting', WaitingJobsResource(job_queue))

    def render_POST(self, request):
        new_job = json.loads(request.content.getvalue())
        job_queue.add(new_job['sprinkler_id'], new_job['duration'],
                new_job['high_priority'])
        return ''


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


job_queue = daemon.main()

root = RootResource()
root.putChild('jobs', JobsResource(job_queue))

site = server.Site(root)

webService = internet.TCPServer(8080, site)  # @UndefinedVariable
application = service.Application("My Web Service")
webService.setServiceParent(application)
