
import socket
import functools
import mimetypes
import os
import os.path
import sys
import threading
import time

import h2.connection
from h2.events import (
  RequestReceived, DataReceived, WindowUpdated
)

def close_file(file, d):
  file.close()

READ_CHUNK_SIZE = 8192

flag = False
mutex_chunk = True
lock = threading.Lock()
semaphore = threading.BoundedSemaphore()

def handle(sock, root):
  global flag
  conn = h2.connection.H2Connection(client_side=False)
  conn.initiate_connection() #Send preamble
  sock.sendall(conn.data_to_send())
  #sock.settimeout(10)

  while True:
    print "before data"
    data = sock.recv(65535)
    print "after data"
    if not data:
      break

    events = conn.receive_data(data)
    for event in events:
      print(event)
      if isinstance(event, RequestReceived):
        thread = threading.Thread(target=send_response, args=(conn,event,sock,root,))
        thread.start()
        print "start thread........."
      # elif isinstance(event, WindowUpdated):
      #   if event.stream_id != 0:
      #     while True:
      #       if conn.local_flow_control_window(event.stream_id) > 8093:
      #         flag = True
      #         print "flagTrue"
      #         break

        #send_response(conn, event, sock, root)

def send_response(conn, event, sock, root):
  stream_id = event.stream_id
  path = event.headers[3][1].lstrip('/')
  print event.headers
  full_path = root + path
  print "send response " + str(stream_id)

  if not os.path.exists(full_path):
    response_headers = (
      (':status', '404'),
      ('content-length', '0'),
      ('server', 'basic-h2-server/1.0'),
    )
    conn.send_headers(
      stream_id, response_headers, end_stream=True
    )
    sock.sendall(conn.data_to_send())

  else:
    sendFile(conn, full_path, stream_id, sock)

  return

def wait(conn,sock,stream_id):
  global flag
  print "enter wait stream" + str(stream_id)
  while True:
    if flag:
      print "flag"
      flag = False
      break

def sendFile(conn, file_path, stream_id, sock):
  global mutex_chunk, mutex_file_chunk
  print "send file " + str(stream_id)

  filesize = os.stat(file_path).st_size
  content_type, content_encoding = mimetypes.guess_type(file_path)
  response_headers = [
    (':status', '200'),
    ('content-length', str(filesize)),
    ('server', 'basic-h2-server/1.0'),
  ]
  if content_type:
    response_headers.append(('content-type', content_type))
  if content_encoding:
    response_headers.append(('content-encoding', content_encoding))

  conn.send_headers(stream_id, response_headers)
  sock.sendall(conn.data_to_send())

  file = open(file_path, 'rb')

  keep_reading = True
  while keep_reading:
    semaphore.acquire()
    print "***ENTRA A SEMAFORO STREAM: " + str(stream_id)
    # if conn.local_flow_control_window(stream_id) == 0:
    #   wait(conn,sock,stream_id)

    chunk_size = min(
      conn.local_flow_control_window(stream_id), READ_CHUNK_SIZE
    )

    data = file.read(chunk_size)
    if len(data) != 0:
      print "LOCAL FLOW CONTROL WINDOW: " + str(conn.local_flow_control_window(stream_id))
      print "ENVIO " +  str(len(data)) + " POR STREAM "+ str(stream_id)
      filesize = filesize - len(data)
      print "BYTES que faltan del archivo "+ str(filesize)
      keep_reading = len(data) == chunk_size
      local_flow = conn.local_flow_control_window(stream_id)
      conn.send_data(stream_id, data, not keep_reading)

      sock.sendall(conn.data_to_send())

      while True:
        print "while true nuevoooooo"
        if local_flow != conn.local_flow_control_window(stream_id):
          break
    else:
      print "len data"
      keep_reading = False
      conn.send_data(stream_id, data)
      sock.sendall(conn.data_to_send())
      semaphore.release()
      break
    print "while true " + str(stream_id) + "  y  " + str(conn.local_flow_control_window(stream_id))
    while True:
      if conn.local_flow_control_window(stream_id) != 0:
        #semaphore.release()
        break
    print "SALE DE SEMAFORO STREAM: " + str(stream_id)
    print " "
    semaphore.release()

  file.close()
  print "file close stream " + str(stream_id)
  print "ENNDD stream " + str(stream_id)


root = sys.argv[1]

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('localhost', 8080))
sock.listen(5)

while True:
  handle(sock.accept()[0], root)
