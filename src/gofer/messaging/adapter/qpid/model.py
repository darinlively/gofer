# Copyright (c) 2013 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from uuid import uuid4
from logging import getLogger

from qpid.messaging import Message

from gofer.messaging.adapter.model import BaseExchange, BaseQueue
from gofer.messaging.adapter.qpid.connection import Connection


log = getLogger(__name__)


SUBJECT = 'broker'
ADDRESS = 'qmf.default.direct/broker'
REPLY_TO = 'qmf.default.direct/%s;{node:{type:topic},link:{x-declare:{auto-delete:True,exclusive:True}}}'

EEXIST = 7

CREATE = 'create'
DELETE = 'delete'

OBJECT_ID = {
    '_object_name': 'org.apache.qpid.broker:broker:amqp-broker'
}


class Error(Exception):
    """
    General Error.
    :ivar code: The qpid error code.
    :type code: int
    """

    def __init__(self, description, code):
        """
        :param description: Error description.
        :type description: str
        :param code: The qpid error code.
        :type code: int
        """
        super(Error, self).__init__(description)
        self.code = code


class Method(object):
    """
    QMF method.
    :ivar name: The method name.
    :type name: str
    :ivar arguments: The method arguments.
    :type arguments: dict
    """

    def __init__(self, name, arguments):
        """
        :param name: The method name.
        :type name: str
        :param arguments: The method arguments.
        :type arguments: dict
        """
        self.name = name
        self.arguments = arguments

    @property
    def content(self):
        return {
            '_object_id': OBJECT_ID,
            '_method_name': self.name,
            '_arguments': self.arguments
        }

    @property
    def properties(self):
        return {
            'qmf.opcode': '_method_request',
            'x-amqp-0-10.app-id': 'qmf2',
            'method': 'request'
        }

    def on_reply(self, reply):
        """
        Process the QMF reply.
        :param reply: The reply.
        :type reply: Message
        :raise: Error on failures.
        """
        opcode = reply.properties['qmf.opcode']
        if opcode != '_exception':
            # succeeded
            return
        body = reply.content
        values = body['_values']
        code = values['error_code']
        description = values['error_text']
        if code == EEXIST:
            return
        raise Error(description, code)

    def __call__(self, url):
        """
        Invoke the method.
        :param url: The broker url.
        :type url: str
        :raise: Error on failure.
        """
        reply_to = REPLY_TO % uuid4()
        connection = Connection(url)
        connection.open()
        session = connection.session()
        sender = session.sender(ADDRESS)
        receiver = session.receiver(reply_to)

        try:
            request = Message(
                content=self.content,
                reply_to=reply_to,
                properties=self.properties,
                correlation_id=str(uuid4()),
                subject=SUBJECT)
            sender.send(request)
            reply = receiver.fetch()
            session.acknowledge()
            self.on_reply(reply)
        finally:
            try:
                receiver.close()
            except Exception:
                pass
            try:
                sender.close()
            except Exception:
                pass
            try:
                session.close()
            except Exception:
                pass


class Exchange(BaseExchange):

    def declare(self, url):
        """
        Declare the exchange.
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': self.name,
            'type': 'exchange',
            'exchange-type': self.policy,
            'properties': {
                'auto-delete': self.auto_delete,
                'durable': self.durable
            }
        }
        method = Method(CREATE, arguments)
        method(url)

    def delete(self, url):
        """
        Delete the exchange.
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': self.name,
            'type': 'exchange',
            'properties': {}
        }
        method = Method(DELETE, arguments)
        method(url)

    def bind(self, queue, url):
        """
        Bind the specified queue.
        :param queue: The queue to bind.
        :type queue: BaseQueue
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': '/'.join((self.name, queue.name, queue.name)),
            'type': 'binding',
            'properties': {}
        }
        method = Method(CREATE, arguments)
        method(url)

    def unbind(self, queue, url):
        """
        Unbind the specified queue.
        :param queue: The queue to unbind.
        :type queue: BaseQueue
        :raise Error
        """
        arguments = {
            'strict': True,
            'name': '/'.join((self.name, queue.name, queue.name)),
            'type': 'binding',
            'properties': {}
        }
        method = Method(DELETE, arguments)
        method(url)


class Queue(BaseQueue):

    def declare(self, url):
        """
        Declare the queue.
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': self.name,
            'type': 'queue',
            'properties': {
                'exclusive': self.exclusive,
                'auto-delete': self.auto_delete,
                'durable': self.durable
            }
        }
        method = Method(CREATE, arguments)
        method(url)

    def delete(self, url):
        """
        Delete the queue.
        :param url: The broker URL.
        :type url: str
        :raise: Error
        """
        arguments = {
            'strict': True,
            'name': self.name,
            'type': 'queue',
            'properties': {}
        }
        method = Method(DELETE, arguments)
        method(url)
