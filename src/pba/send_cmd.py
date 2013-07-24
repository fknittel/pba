#!/usr/bin/python
# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
import urllib2
import json
import sys

BASE_URL = 'http://localhost:8080'


def add_job(sprinkler_id, duration):
    jsondata = json.dumps({
        'sprinkler_id': sprinkler_id,
        'duration': duration,
        'high_priority': False
        })
    url = BASE_URL + '/jobs'
    req = urllib2.Request(url, jsondata, {'Content-Type': 'application/json'})
    f = urllib2.urlopen(req)
    response = f.read()
    f.close()
    job_id = json.loads(response)['job_id']
    print('added job with id {0}'.format(job_id))


def show_usage():
    print('usage: {0} add-job SPRINKLER_ID DURATION'.format(sys.argv[0]),
            file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 4:
        show_usage()
    cmd = sys.argv[1]
    if cmd == 'add-job':
        sprinkler_id = sys.argv[2]
        duration = int(sys.argv[3])
        add_job(sprinkler_id, duration)
    else:
        print('error: unknown command {0}'.format(cmd), file=sys.stderr)
        show_usage()


if __name__ == '__main__':
    main()
