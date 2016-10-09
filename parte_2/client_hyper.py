from hyper import HTTP20Connection
import sys
import threading

def download_file(c,stream):
  resp = c.get_response(stream)

  file = open('torecvClient_'+str(stream)+'.txt','wb')

  body = resp.read()

  file.write(body)
  file.close()


server_ip = sys.argv[1]
multiplex = sys.argv[2]
streams = []
threads = []

c = HTTP20Connection(server_ip +':8080')

if multiplex == "-m":
  #Requests
  for file_path in sys.argv[3:]:
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
  file_path = sys.argv[2]
  stream = c.request('GET','/'+file_path, headers={'key': 'value'})
  download_file(c, stream)
