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

READ_CHUNK_SIZE = 8091

def handle(sock, root):
  print("handle")
  #_flow_control_deferreds = {}
  conn = h2.connection.H2Connection(client_side=False)
  conn.initiate_connection() #Send preamble
  sock.sendall(conn.data_to_send())

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
      elif isinstance(event, DataReceived):
          conn.reset_stream(event.stream_id)
          print ("dataReceived *****")
      elif isinstance(event, WindowUpdated):
        #self.windowUpdated(event)
        print ("window updated****")


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
    )
    sock.sendall(conn.data_to_send())

  else:
    sendFile(conn, full_path, stream_id, sock)

  print("send_response F")
  return

def wait(conn,sock,stream_id):
        while True:

            data = sock.recv(65535)

            #if len(data) == 0:
            #    self.sock.close()
            #    break

            for event in conn.receive_data(data):
                print("EVENT IN WAIT:")
                print(event)
            print("size in wait:" + str(conn.local_flow_control_window(stream_id)))  
            if conn.local_flow_control_window(stream_id) > 0:
                break

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
    print("imprimo el remote flow:" + str(conn.local_flow_control_window(stream_id)))
    if conn.local_flow_control_window(stream_id) == 0:
      print("entro en el if")
      wait(conn,sock,stream_id)
    #chunk_size = 8192
    print (conn.local_flow_control_window(stream_id))
    chunk_size = min(
      conn.local_flow_control_window(stream_id), READ_CHUNK_SIZE
    )
    print ("chunk " + str(chunk_size))
    data = file.read(chunk_size)
    keep_reading = len(data) == chunk_size
    conn.send_data(stream_id, data, not keep_reading)
    sock.sendall(conn.data_to_send())

    # increment = 65535
    # conn.increment_flow_control_window(increment, stream_id)
    if not keep_reading:
      break
    if len(data) == 0:
      break

  file.close()

root = sys.argv[1]

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('localhost', 8080))
sock.listen(5)

while True:
  handle(sock.accept()[0], root)
