import json
import socket
import functools
import mimetypes
import os
import os.path
import sys

import h2.connection
from h2.events import (
  RequestReceived, DataReceived, WindowUpdated
)

def close_file(file, d):
  file.close()

READ_CHUNK_SIZE = 8192

def handle(sock, root):
  print("handle")
  conn = h2.connection.H2Connection(client_side=False)
  conn.initiate_connection() #Send preamble
  sock.sendall(conn.data_to_send())
  print("handle2")
  while True:
    data = sock.recv(65535)
    if not data:
      print("no data")
      break

    events = conn.receive_data(data)
    for event in events:
      print(event)
      if isinstance(event, RequestReceived):
        print("siii")
        send_response(conn, event, sock, root)

    data_to_send = conn.data_to_send()
    if data_to_send:
      sock.sendall(data_to_send)


def send_response(conn, event, sock, root):
  print("send response")
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
    ) #H2Connection: envio de headers
    sock.sendall(conn.data_to_send())
  else:
    sendFile(conn, full_path, stream_id, sock)

  print("send_response F")
  return

def sendFile(conn, file_path, stream_id, sock):
  print("sendFile I")
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

  print(file_path)
  file = open(file_path, 'rb')
  #d.addErrback(functools.partial(close_file, f))

  keep_reading = True
  while keep_reading:
    chunk_size = 8192
    data = file.read(chunk_size)
    keep_reading = len(data) == chunk_size
    conn.send_data(stream_id, data, not keep_reading)
    sock.sendall(conn.data_to_send())

    if not keep_reading:
      break

  file.close()


root = sys.argv[1]

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 8080))
sock.listen(5)

while True:
  handle(sock.accept()[0], root)
