from hyper import HTTP20Connection
from hyper import tls
from hyper.compat import ssl
from eventlet.green.OpenSSL import SSL, crypto
import sys
import threading

def download_file(c,stream):
  resp = c.get_response(stream)
  
  for push in c.get_pushes(): # all pushes promised before response headers
      print("primer push")
      print(push.path)
      print(push.get_response().read(decode_content=True))
      
  body = resp.read()
  for push in c.get_pushes(): # all other pushes
      print("segundo push")
      print(push.path)
      print(push.get_response().read(decode_content=True))

  file = open('torecvClient_'+str(stream)+'.txt','wb')


  file.write(body)
  file.close()
  # c.close()

def alpn_callback(ssl_sock, server_name):#conn, protos):
    print("callback")
    if b'h2' in protos:
        return b'h2'
    raise RuntimeError("No acceptable protocol offered!")


def npn_advertise_cb(conn, a, b):
    return [b'h2']

# options = (
#     SSL.OP_NO_COMPRESSION |
#     SSL.OP_NO_SSLv2 |
#     SSL.OP_NO_SSLv3 |
#     SSL.OP_NO_TLSv1 |
#     SSL.OP_NO_TLSv1_1
# )
# context = SSL.Context(SSL.SSLv23_METHOD)
# context.set_options(options)
# context.set_verify(SSL.VERIFY_NONE, lambda *args: True)
# context.use_privatekey_file('server.key')
# context.use_certificate_file('server.crt')
# context.set_npn_advertise_callback(npn_advertise_cb)
# context.set_alpn_select_callback(alpn_callback)
# context.set_cipher_list(
#     "ECDHE+AESGCM"
# )

# context.set_tmp_ecdh(crypto.get_elliptic_curve(u'prime256v1'))

ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)#tls.init_context()
ctx.load_cert_chain(certfile='server.crt', keyfile='server.key')
ctx.load_verify_locations(cafile='server.crt')


ctx.options |= ssl.OP_NO_COMPRESSION | SSL.OP_NO_SSLv2 | SSL.OP_NO_SSLv3 | SSL.OP_NO_TLSv1 | SSL.OP_NO_TLSv1_1

c = HTTP20Connection('localhost', 1067, enable_push=True, ssl_context=ctx, force_proto='h2', secure=True)

multiplex = sys.argv[1]
streams = []
threads = []

if multiplex == "-m":
  #Requests
  for file_path in sys.argv[2:]:
    stream = c.request('GET','/'+file_path, headers={'key': 'value'})
    streams.append(stream)

  #Create threads
  for stream in streams:
    thread = threading.Thread(target=download_file, args=(c,stream,))
    threads.append(thread)

  #Start threads
  for thread in threads:
    thread.start()

else:
  file_path = sys.argv[1]
  stream = c.request('GET','/'+file_path, headers={'key': 'value'})
  print(stream)
  download_file(c, stream)
