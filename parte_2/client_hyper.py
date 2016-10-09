from hyper import HTTP20Connection
import sys

file_path = sys.argv[1]

c = HTTP20Connection('localhost:8080')
c.request('GET','/'+file_path, headers={'key': 'value'})

resp = c.get_response()

f = open('torecvClient2.txt','wb')

body = resp.read()

f.write(body)
f.close()
