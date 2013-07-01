import httplib2
import json


TESTDATA = {
        'sprinkler_id': 'court1',
        'duration': 12,
        'high_priority': False
        }
URL = 'http://localhost:8080/jobs'

jsondata = json.dumps(TESTDATA)
h = httplib2.Http()
resp, content = h.request(URL,
                          'POST',
                          jsondata,
                          headers={'Content-Type': 'application/json'})
print resp
print content
