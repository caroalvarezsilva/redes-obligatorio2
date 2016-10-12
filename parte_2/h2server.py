import json
import socket
import functools
import mimetypes
import os
import os.path
import sys
import ssl
import thread
import time
import h2

from datetime import datetime
from OpenSSL import SSL
from eventlet.green.OpenSSL import crypto
import h2.connection
from h2.events import (
  RequestReceived, DataReceived, WindowUpdated
)

def alpn_callback(conn, protos):
    if b'h2' in protos:
        return b'h2'

    raise RuntimeError("No acceptable protocol offered!")


def npn_advertise_cb(conn):
    return [b'h2']

def sslCallback(socket, serverName, ctxSSL):
    socket.context = ctxSSL

def close_file(file, d):
  file.close()

READ_CHUNK_SIZE = 8192

def handle(sock):
  print("handle")
  conn = h2.connection.H2Connection(client_side=False)
  conn.initiate_connection() #Send preamble
  sock.sendall(conn.data_to_send())
  while True:
    data = sock.recv(16383)
    if not data:
        break 
    events = conn.receive_data(data)
    for event in events:
      print(event)
      if isinstance(event, RequestReceived):
          send_response(conn, event, sock)

    data_to_send = conn.data_to_send()
    if data_to_send:
        sock.sendall(data_to_send)


def send_response(conn, event, sock):
  stream_id = event.stream_id
  full_path = root

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
      
    newStream = conn.get_next_available_stream_id()
    push_headers = [
            (':authority', 'localhost'),
            (':path', '/pushInfo'),
            (':scheme', 'https'),
            (':method', 'GET'),
    ]
    conn.push_stream(
                    stream_id=stream_id,
                    promised_stream_id=newStream,
                    request_headers=push_headers
    )
    sendFile(conn, full_path, stream_id, sock)
    
    currentDate = datetime.now()
    date_send = (str(currentDate.hour) + ":" + str(currentDate.minute)).encode("utf8")
    print ("send push info = " + date_send)
    push_response_headers = (
        (':status', '200'),
        ('content-length', len(date_send)),
        ('content-type', 'text/plain'),
        ('server', 'basic-h2-server/1.0'),
    )

    conn.send_headers(newStream, push_response_headers)
    conn.send_data(newStream, date_send, end_stream=True)
    sock.sendall(conn.data_to_send())
  

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
  file = open(file_path, 'rb')

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

# Let's set up SSL. This is a lot of work in PyOpenSSL.
options = (
    SSL.OP_NO_COMPRESSION |
    SSL.OP_NO_SSLv2 |
    SSL.OP_NO_SSLv3 |
    SSL.OP_NO_TLSv1 |
    SSL.OP_NO_TLSv1_1
)
context = SSL.Context(SSL.SSLv23_METHOD)
#ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
# context.options |= (
#         ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_COMPRESSION
# )

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

server.bind(('0.0.0.0', 1067))
server.listen(3) 

while True:
    new_sock, _ = server.accept()
    handle(new_sock)
server.close()    