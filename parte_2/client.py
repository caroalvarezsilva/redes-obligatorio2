import socket
from h2.connection import H2Connection
from h2.events import (
    ResponseReceived, DataReceived, RemoteSettingsChanged, StreamEnded,
    StreamReset, SettingsAcknowledged,
)

AUTHORITY = u'localhost'
PATH = '/'
SIZE = 4096

#abrir socket localhost 8080
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 8080))

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

while True:
  data = sock.recv(65535)
  if not data:
    print("no data")
    break

  events = conn.receive_data(data)
  for event in events:
    print(event)
    if isinstance(event, ResponseReceived):
      print("siii")
