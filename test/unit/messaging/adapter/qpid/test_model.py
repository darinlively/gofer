# Copyright (c) 2014 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

from unittest import TestCase

from mock import patch, Mock

from gofer.devel import ipatch

with ipatch('qpid'):
    from gofer.messaging.adapter.qpid import model
    from gofer.messaging.adapter.qpid.model import Error, Method
    from gofer.messaging.adapter.qpid.model import Exchange, BaseExchange
    from gofer.messaging.adapter.qpid.model import Queue, BaseQueue


class TestError(TestCase):

    def test_init(self):
        code = 18
        description = '12345'
        error = Error(description, code)
        self.assertEqual(error.code, code)
        self.assertEqual(error.args[0], description)


class TestMethod(TestCase):

    def test_init(self):
        name = model.CREATE
        arguments = {'a': 1}
        method = Method(name, arguments)
        self.assertEqual(method.name, name)
        self.assertEqual(method.arguments, arguments)

    def test_content(self):
        name = model.CREATE
        arguments = {'a': 1}
        method = Method(name, arguments)
        self.assertEqual(
            method.content,
            {
                '_object_id': model.OBJECT_ID,
                '_method_name': name,
                '_arguments': arguments
            })

    def test_properties(self):
        method = Method(model.CREATE, {})
        self.assertEqual(
            method.properties,
            {
                'qmf.opcode': '_method_request',
                'x-amqp-0-10.app-id': 'qmf2',
                'method': 'request'
            })

    def test_reply_succeeded(self):
        content = ''
        properties = {
            'qmf.opcode': ''
        }
        reply = Mock(content=content, properties=properties)
        method = Method('', {})
        method.on_reply(reply)

    def test_reply_failed(self):
        values = {
            'error_code': 18,
            'error_text': 'just failed'
        }
        content = {'_values': values}
        properties = {
            'qmf.opcode': '_exception'
        }
        reply = Mock(content=content, properties=properties)
        method = Method('', {})
        self.assertRaises(Error, method.on_reply, reply)

    def test_reply_already_exists(self):
        values = {
            'error_code': model.EEXIST,
            'error_text': 'just failed'
        }
        content = {'_values': values}
        properties = {
            'qmf.opcode': '_exception'
        }
        reply = Mock(content=content, properties=properties)
        method = Method('', {})
        method.on_reply(reply)

    @patch('gofer.messaging.adapter.qpid.model.uuid4')
    @patch('gofer.messaging.adapter.qpid.model.Message')
    @patch('gofer.messaging.adapter.qpid.model.Connection')
    def test_call(self, _connection, message, uuid):
        url = 'url-test'
        name = model.CREATE
        arguments = {'a': 1}
        uuid.return_value = '5138'
        reply_to = model.REPLY_TO % uuid.return_value
        connection = Mock()
        _connection.return_value = connection
        session = Mock()
        session.close.side_effect = ValueError
        sender = Mock()
        sender.close.side_effect = ValueError
        receiver = Mock()
        receiver.close.side_effect = ValueError
        session.receiver.return_value = receiver
        session.sender.return_value = sender
        connection.session.return_value = session

        # test
        method = Method(name, arguments)
        method.on_reply = Mock()
        method(url)

        # validation
        _connection.assert_called_once_with(url)
        connection.open.assert_called_once_with()
        connection.session.assert_called_once_with()

        session.sender.assert_called_once_with(model.ADDRESS)
        session.receiver.assert_called_once_with(reply_to)

        message.assert_called_once_with(
            content=method.content,
            reply_to=reply_to,
            properties=method.properties,
            correlation_id=str(uuid.return_value),
            subject=model.SUBJECT
        )

        session.acknowledge.assert_called_once_with()
        sender.send.assert_called_once_with(message.return_value)
        method.on_reply.assert_called_once_with(receiver.fetch.return_value)
        sender.close.assert_called_once_with()
        receiver.close.assert_called_once_with()
        session.close.assert_called_once_with()


class TestExchange(TestCase):

    def test_init(self):
        name = 'test-exchange'
        policy = 'direct'

        # test
        exchange = Exchange(name, policy=policy)

        # validation
        self.assertTrue(isinstance(exchange, BaseExchange))
        self.assertEqual(exchange.name, name)
        self.assertEqual(exchange.policy, policy)

    @patch('gofer.messaging.adapter.qpid.model.Method')
    def test_declare(self, method):
        url = 'test-url'

        # test
        exchange = Exchange('test', policy='direct')
        exchange.durable = 0
        exchange.auto_delete = 1
        exchange.declare(url)

        # validation
        arguments = {
            'strict': True,
            'name': exchange.name,
            'type': 'exchange',
            'exchange-type': exchange.policy,
            'properties': {
                'auto-delete': exchange.auto_delete,
                'durable': exchange.durable
            }
        }
        method.assert_called_once_with(model.CREATE, arguments)
        method.return_value.assert_called_once_with(url)

    @patch('gofer.messaging.adapter.qpid.model.Method')
    def test_delete(self, method):
        url = 'test-url'

        # test
        exchange = Exchange('test')
        exchange.delete(url)

        # validation
        arguments = {
            'strict': True,
            'name': exchange.name,
            'type': 'exchange',
            'properties': {}
        }
        method.assert_called_once_with(model.DELETE, arguments)
        method.return_value.assert_called_once_with(url)

    @patch('gofer.messaging.adapter.qpid.model.Method')
    def test_bind(self, method):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        exchange = Exchange('test')
        exchange.bind(queue, url)

        # validation
        arguments = {
            'strict': True,
            'name': '/'.join((exchange.name, queue.name, queue.name)),
            'type': 'binding',
            'properties': {}
        }
        method.assert_called_once_with(model.CREATE, arguments)
        method.return_value.assert_called_once_with(url)

    @patch('gofer.messaging.adapter.qpid.model.Method')
    def test_unbind(self, method):
        url = 'test-url'
        queue = Queue('test-queue')

        # test
        exchange = Exchange('test')
        exchange.unbind(queue, url)

        # validation
        arguments = {
            'strict': True,
            'name': '/'.join((exchange.name, queue.name, queue.name)),
            'type': 'binding',
            'properties': {}
        }
        method.assert_called_once_with(model.DELETE, arguments)
        method.return_value.assert_called_once_with(url)


class TestQueue(TestCase):

    def test_init(self):
        name = 'test-queue'

        # test
        queue = Queue(name)

        # validation
        self.assertTrue(isinstance(queue, BaseQueue))
        self.assertEqual(queue.name, name)

    @patch('gofer.messaging.adapter.qpid.model.Method')
    def test_declare(self, method):
        url = 'test-url'

        # test
        queue = Queue('test-queue')
        queue.durable = 0
        queue.auto_delete = True
        queue.expiration = 10
        queue.exclusive = 3
        queue.declare(url)

        # validation
        arguments = {
            'strict': True,
            'name': queue.name,
            'type': 'queue',
            'properties': {
                'exclusive': queue.exclusive,
                'auto-delete': queue.auto_delete,
                'durable': queue.durable
            }
        }
        method.assert_called_once_with(model.CREATE, arguments)
        method.return_value.assert_called_once_with(url)

    @patch('gofer.messaging.adapter.qpid.model.Method')
    def test_delete(self, method):
        url = 'test-url'

        # test
        queue = Queue('test-queue')
        queue.delete(url)

        # validation
        arguments = {
            'strict': True,
            'name': queue.name,
            'type': 'queue',
            'properties': {}
        }
        method.assert_called_once_with(model.DELETE, arguments)
        method.return_value.assert_called_once_with(url)
