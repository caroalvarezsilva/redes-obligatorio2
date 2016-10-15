import json
import socket
import functools
import mimetypes
import os
import os.path
import sys
import threading
import ssl
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

READ_CHUNK_SIZE = 8091

flag = False
mutex = True
mutex_chunk = True
lock = threading.Lock()

def handle(sock, root):
  global flag
  conn = h2.connection.H2Connection(client_side=False)
  conn.initiate_connection() #Send preamble
  sock.sendall(conn.data_to_send())

  while True:
    print ("before data")
    data = sock.recv(65535)
    print ("after data")
    if not data:
      break

    events = conn.receive_data(data)
    for event in events:
      print(event)
      if isinstance(event, RequestReceived):
        thread = threading.Thread(target=send_response, args=(conn,event,sock,root,))
        thread.start()
        print ("start thread.........")
      elif isinstance(event, WindowUpdated):
        if event.stream_id != 0:
          while True:
            if conn.local_flow_control_window(event.stream_id) > 8093:
              flag = True
              print ("flagTrue")
              break

        #send_response(conn, event, sock, root)

def send_response(conn, event, sock, root):
  stream_id = event.stream_id
  path = event.headers[3][1].lstrip('/')
  full_path = root + path
  print ("send response " + str(stream_id))
  
  global pushActive
  
  if pushActive:
      newStream = conn.get_next_available_stream_id()
      push_headers = [
              (':authority', 'localhost:8080'),
              (':path', '/pushInfo'),
              (':scheme', 'https'),
              (':method', 'GET'),
      ]
      conn.push_stream(
                      stream_id=stream_id,
                      promised_stream_id=newStream,
                      request_headers=push_headers
      )
  
      currentDate = datetime.now()
      date_send = datetime.now().strftime("%H:%M").encode("utf8")
      print ("send push info = " + str(date_send))
      push_response_headers = (
          (':status', '200'),
          ('content-length', len(date_send)),
          ('content-type', 'text/plain'),
          ('server', 'basic-h2-server/1.0'),
      )

      conn.send_headers(newStream, push_response_headers)
      conn.send_data(newStream, date_send, end_stream=True)
      sock.sendall(conn.data_to_send())

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
  print ("enter wait stream" + str(stream_id))
  while True:
    #print "wait"
    if flag:
      print ("flag")
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
  print ("send file " + str(stream_id))
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
    mutex_chunk = (conn.local_flow_control_window(stream_id) >= 8091*2)
    print ("local flow for stream " + str(stream_id) + "  "+ str(conn.local_flow_control_window(stream_id)))
    print ("mutex 1" + str(mutex))
    if mutex_chunk:
      mutex_chunk = (conn.local_flow_control_window(stream_id) >= 8091*2)
      with lock:
        if conn.local_flow_control_window(stream_id) == 0:
          print ("mutex 2" + str(mutex))
          wait(conn,sock,stream_id)
        #chunk_size = 8192
        chunk_size = min(
          conn.local_flow_control_window(stream_id), READ_CHUNK_SIZE
        )
        print ("envio stream " + str(stream_id) + "  "+ str(conn.local_flow_control_window(stream_id)))
        data = file.read(chunk_size)
        keep_reading = len(data) == chunk_size
        conn.send_data(stream_id, data, not keep_reading)
        sock.sendall(conn.data_to_send())
        mutex_chunk = True

      if not keep_reading:
        break
      if len(data) == 0:
        break

  file.close()

  data_to_send = conn.data_to_send()
  if data_to_send:
    sock.sendall(data_to_send)
    
    
def pushThread():
    global pushActive
    while True:
        pushActive = not pushActive
        time.sleep(60)



root = sys.argv[1]
pushActive = False
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


#hilo para el push
# PushThread = threading.Thread(target=pushThread)
# PushThread.start()


while True:
    new_sock, _ = server.accept()
    handle(new_sock, root)
server.close()

# Sin certificado 

# sock = socket.socket()
# sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# sock.bind(('localhost', 8080))
# sock.listen(5)



# while True:
#     handle(sock.accept()[0], root)
