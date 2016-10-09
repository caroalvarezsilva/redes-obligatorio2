from hyper import HTTP20Connection
import sys
import threading

def download_file(c,stream):
  resp = c.get_response(stream)

  file = open('torecvClient_'+str(stream)+'.txt','wb')

  body = resp.read()

  file.write(body)
  file.close()


c = HTTP20Connection('localhost:8080')

multiplex = sys.argv[1]
streams = []
threads = []

if multiplex == "-m":
  #Requests
  for file_path in sys.argv[2:]:
    stream = c.request('GET','/'+file_path, headers={'key': 'value'})
    streams.append(stream)

  #Create threads
  for stream in streams:
    thread = threading.Thread(target=download_file, args=(c,stream,))
    threads.append(thread)

  #Start threads
  for thread in threads:
    thread.start()

else:
  file_path = sys.argv[1]
  stream = c.request('GET','/'+file_path, headers={'key': 'value'})
  download_file(c, stream)
