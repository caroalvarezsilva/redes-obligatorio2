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

READ_CHUNK_SIZE = 8091

flag = False
mutex = True
mutex_chunk = True

def handle(sock, root):
  global flag
  conn = h2.connection.H2Connection(client_side=False)
  conn.initiate_connection() #Send preamble
  sock.sendall(conn.data_to_send())

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
      elif isinstance(event, WindowUpdated):
        if event.stream_id != 0:
          while True:
            if conn.local_flow_control_window(event.stream_id) > 8093:
              flag = True
              print "flagTrue"
              break

        #send_response(conn, event, sock, root)

def send_response(conn, event, sock, root):
  stream_id = event.stream_id
  path = event.headers[3][1].lstrip('/')
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
  out = False
  print "enter wait stream" + str(stream_id)
  while True:
    #print "wait"
    if flag:
      print "flag"
      flag = False
      break
    # data = sock.recv(65535)

    # #if len(data) == 0:
    # #    self.sock.close()
    # #    break
    # if data:
    #   for event in conn.receive_data(data):
    #     if isinstance(event, WindowUpdated):
    #       if event.stream_id != 0:
    #         #time.sleep(5)
    #         if conn.local_flow_control_window(stream_id) > 8093:
    #           out = True
    #           print "out stream "+ str(stream_id)
    #           break
    #   if out:
    #     break

    # #print "waiting" + str(stream_id)

def sendFile(conn, file_path, stream_id, sock):
  global mutex, mutex_chunk
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

    print "local flow for stream " + str(stream_id) + "  "+ str(conn.local_flow_control_window(stream_id))
    print "mutex 1" + str(mutex)
    if mutex_chunk:
      mutex_chunk = (conn.local_flow_control_window(stream_id) >= 8091*2)
      if mutex:
        if conn.local_flow_control_window(stream_id) == 0:
          mutex = False
          print "mutex 2" + str(mutex)
          wait(conn,sock,stream_id)
        #chunk_size = 8192
        chunk_size = min(
          conn.local_flow_control_window(stream_id), READ_CHUNK_SIZE
        )
        print "envio stream " + str(stream_id) + "  "+ str(conn.local_flow_control_window(stream_id))
        data = file.read(chunk_size)
        keep_reading = len(data) == chunk_size
        conn.send_data(stream_id, data, not keep_reading)
        sock.sendall(conn.data_to_send())
        mutex = True
      mutex_chunk = True

    if not keep_reading:
      break
    if len(data) == 0:
      break

  file.close()

  data_to_send = conn.data_to_send()
  if data_to_send:
    sock.sendall(data_to_send)


root = sys.argv[1]

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('localhost', 8080))
sock.listen(5)

while True:
  handle(sock.accept()[0], root)
