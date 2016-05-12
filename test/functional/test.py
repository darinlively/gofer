
from gofer.messaging.adapter.proton.producer import Sender

url = 'amqp://localhost:5647'
with Sender(url) as sender:
    sender.send('qd.foo', 'hello')
