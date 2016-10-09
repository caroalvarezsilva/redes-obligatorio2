from hyper import HTTP20Connection

c = HTTP20Connection('localhost:8080')
c.request('GET','/', headers={'key': 'value'})

resp = c.get_response()

f = open('torecvClient2.txt','wb')

body = resp.read()

f.write(body)
f.close()
