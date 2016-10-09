import socket
from h2.connection import H2Connection
from h2.events import (
    ResponseReceived, DataReceived, RemoteSettingsChanged, StreamEnded,
    StreamReset, SettingsAcknowledged,
)
from eventlet.green.OpenSSL import SSL, crypto
from OpenSSL import SSL


def alpn_callback(conn, protos):
    if b'h2' in protos:
        return b'h2'
    raise RuntimeError("No acceptable protocol offered!")


def npn_advertise_cb(conn):
    return [b'h2']


AUTHORITY = u'localhost'
PATH = '/'
SIZE = 4096

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
sock = SSL.Connection(context, socket.socket(socket.AF_INET, socket.SOCK_STREAM))
sock.connect(('localhost', 1067))

conn = H2Connection()
conn.initiate_connection() #Send preamble
sock.sendall(conn.data_to_send())

request_headers = [
    (':method', 'GET'),
    (':authority', AUTHORITY),
    (':scheme', 'https'),
    (':path', PATH),
    ('user-agent', 'hyper-h2/1.0.0')
]

conn.send_headers(1, request_headers, end_stream=True)
sock.sendall(conn.data_to_send())

f = open('torecv.txt','wb')

data = sock.recv(65535)
while data:
  if not data:
    print("no data")
    break

  f.write(data)
  events = conn.receive_data(data)
  print events
  for event in events:
    print(event)
    if isinstance(event, ResponseReceived):
      print("siii")

  data = sock.recv(65535)

sock.shutdown()