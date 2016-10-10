from hyper import HTTP20Connection
from hyper.http20.window import BaseFlowControlManager, FlowControlManager
import sys
import os
import threading

def download_file(c,stream,base):
  resp = c.get_response(stream)

  headers = resp.headers
  content_length = list(headers)[0][1]

  file = open(base,'wb')

  keep_reading = True
  while keep_reading:
    print ("paso3")
    body = resp.read(8091)
    keep_reading = len(body) == 8091
    file.write(body)

    if not keep_reading:
      break

  file.close()


server_ip = sys.argv[1]
multiplex = sys.argv[2]
streams = []
threads = []

#crear un BaseFlowControlManager
#initial window size
b = BaseFlowControlManager(16383)

c = HTTP20Connection(server_ip +':8080')

if multiplex == "-m":
  #Requests
  for file_path in sys.argv[3:]:
    stream = c.request('GET','/'+file_path, headers={'key': 'value'})
    base = os.path.basename(file_path)
    print (base)
    streams.append((stream,base))

  #Create threads
  for stream in streams:
    thread = threading.Thread(target=download_file, args=(c,stream[0],stream[1],))
    threads.append(thread)

  #Start threads
  for thread in threads:
    thread.start()

else:
  file_path = sys.argv[2]
  base = os.path.basename(file_path)
  stream = c.request('GET','/'+file_path, headers={'key': 'value'})
  download_file(c, stream, base)
