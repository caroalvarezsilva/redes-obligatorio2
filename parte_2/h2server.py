
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

semaphore = threading.BoundedSemaphore()

def handle(sock, root):
  conn = h2.connection.H2Connection(client_side=False)
  conn.initiate_connection() #Send preamble
  sock.sendall(conn.data_to_send())

  while True:
    data = sock.recv(65535)
    if not data:
      break

    events = conn.receive_data(data)
    for event in events:
      if isinstance(event, RequestReceived):
        thread = threading.Thread(target=send_response, args=(conn,event,sock,root,))
        thread.start()
        print "start thread........."

def send_response(conn, event, sock, root):
  stream_id = event.stream_id
  path = event.headers[3][1].lstrip('/')
  full_path = root + path

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

def sendFile(conn, file_path, stream_id, sock):
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

    chunk_size = min(
      conn.local_flow_control_window(stream_id), READ_CHUNK_SIZE
    )

    data = file.read(chunk_size)
    keep_reading = len(data) == chunk_size
    local_flow = conn.local_flow_control_window(stream_id)
    conn.send_data(stream_id, data, not keep_reading)

    sock.sendall(conn.data_to_send())

    while True:
      if local_flow != conn.local_flow_control_window(stream_id):
        break
    while True:
      if conn.local_flow_control_window(stream_id) != 0:
        break
    semaphore.release()

  file.close()

root = sys.argv[1]

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('localhost', 8080))
sock.listen(5)

while True:
  handle(sock.accept()[0], root)
