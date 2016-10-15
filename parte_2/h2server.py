
import socket
import functools
import mimetypes
import os
import os.path
import sys
import threading
import time
from OpenSSL import SSL
from eventlet.green.OpenSSL import crypto
import h2.connection
from h2.events import (
  RequestReceived, DataReceived, WindowUpdated
)
from datetime import datetime


def alpn_callback(conn, protos):
    if b'h2' in protos:
        return b'h2'

    raise RuntimeError("No acceptable protocol offered!")


def npn_advertise_cb(conn):
    return [b'h2']

def close_file(file, d):
  file.close()

READ_CHUNK_SIZE = 8192

semaphore = threading.BoundedSemaphore()

def handle(sock, root):
  print("hand le enter")
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
  global push_active
  stream_id = event.stream_id

  if push_active:
    new_stream = conn.get_next_available_stream_id()
    push_headers = [
      (':authority', 'localhost:8080'),
      (':path', '/pushInfo'),
      (':scheme', 'https'),
      (':method', 'GET'),
    ]
    conn.push_stream(
      stream_id=stream_id,
      promised_stream_id=new_stream,
      request_headers=push_headers
    )

    currentDate = datetime.now()
    date_send = datetime.now().strftime("%H:%M").encode("utf8")
    print ("send push info = " + date_send)
    push_response_headers = (
      (':status', '200'),
      ('content-length', len(date_send)),
      ('content-type', 'text/plain'),
      ('server', 'basic-h2-server/1.0'),
    )

    conn.send_headers(new_stream, push_response_headers)
    conn.send_data(new_stream, date_send, end_stream=True)
    sock.sendall(conn.data_to_send())

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

def push():
  global push_active
  while True:
    push_active = not push_active
    time.sleep(60)

root = sys.argv[1]

#sock = socket.socket()
#sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#sock.bind(('localhost', 8080))
#sock.listen(5)

push_active = False
push_thread = threading.Thread(target=push)
push_thread.start()



options = (
    SSL.OP_NO_COMPRESSION |
    SSL.OP_NO_SSLv2 |
    SSL.OP_NO_SSLv3 |
    SSL.OP_NO_TLSv1 |
    SSL.OP_NO_TLSv1_1
)
context = SSL.Context(SSL.SSLv23_METHOD)
context.set_options(options)
context.set_verify(SSL.VERIFY_NONE, lambda *args: True)
context.use_privatekey_file('server.key')
context.use_certificate_file('server.crt')
context.set_npn_advertise_callback(npn_advertise_cb)
context.set_alpn_select_callback(alpn_callback)
context.set_cipher_list(
    "ECDHE+AESGCM"
)
context.set_tmp_ecdh(crypto.get_elliptic_curve(u'prime256v1'))
server = SSL.Connection(context, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
server.bind(('0.0.0.0', 443))
server.listen(3)



while True:
  new_sock, _ = server.accept()
  handle(new_sock, root)
