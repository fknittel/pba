#!/usr/bin/python
# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
import httplib2
import json
import sys

BASE_URL = 'http://localhost:8080'


def add_job(sprinkler_id, duration):
    jsondata = json.dumps({
        'sprinkler_id': sprinkler_id,
        'duration': duration,
        'high_priority': False
        })
    h = httplib2.Http()
    resp, content = h.request(BASE_URL + '/jobs',
            'POST', jsondata,
            headers={'Content-Type': 'application/json'})
    if resp['status'] != '200':
        raise RuntimeError('request failed', resp, content)
    job_id = json.loads(content)['job_id']
    print('added job with id {0}'.format(job_id))


cmd = sys.argv[1]
if cmd == 'add-job':
    sprinkler_id = sys.argv[2]
    duration = int(sys.argv[3])
    add_job(sprinkler_id, duration)
else:
    print('error: unknown command {0}'.format(cmd), file=sys.stderr)
    print('usage: {0} add-job SPRINKLER_ID DURATION'.format(sys.argv[0]),
            file=sys.stderr)
    sys.exit(1)
