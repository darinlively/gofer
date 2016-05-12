#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU Lesser General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (LGPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of LGPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt.
#
# Jeff Ortel <jortel@redhat.com>
#

from logging import getLogger, Formatter, LogRecord, INFO
from logging.handlers import SysLogHandler

from gofer import NAME


PREFIX = '%sd:' % NAME
LEVEL = ' [%(levelname)s]'
THREAD = '[%(threadName)s]'
NAME = ' %(name)s'
LINE = ':%(lineno)d'
MSG = ' - %(message)s'

FORMAT = ''.join((PREFIX, LEVEL, THREAD, NAME, LINE, MSG))
FORMATTER = Formatter(FORMAT)


class LogHandler(SysLogHandler):
    """
    Custom syslog handler.
    """

    @staticmethod
    def install():
        """
        Install the handler.
        """
        LogHandler.uninstall()
        handler = LogHandler(address='/dev/log', facility=SysLogHandler.LOG_DAEMON)
        handler.setFormatter(FORMATTER)
        root = getLogger()
        root.setLevel(INFO)
        root.handlers.append(handler)

    @staticmethod
    def uninstall():
        """
        Uninstall the log handler.
        """
        root = getLogger()
        handlers = root.handlers[:]
        for h in handlers:
            if not isinstance(h, LogHandler):
                pass
            handlers.remove(h)
        root.handlers = handlers

    @staticmethod
    def find():
        """
        Find the installed handler.
        :return: The installed handler.
        :rtype: LogHandler
        """
        root = getLogger()
        handlers = root.handlers[:]
        for h in handlers:
            if isinstance(h, LogHandler):
                return h

    @staticmethod
    def clean(message):
        """
        Clean messages to be emitted.
        :param message: A message to be emitted.
        :type message: str
        :return: The cleaned message.
        :rtype: str
        """
        lines = message.split('\n')
        return ' '.join([ln.strip() for ln in lines])

    def split(self, record):
        """
        Split each line in the traceback into separate records.
        :param record: A log record.
        :type record: LogRecord
        :return: A list of records
        :rtype: list
        """
        records = [record]
        if record.exc_info:
            msg = self.formatter.formatException(record.exc_info)
            for line in msg.split('\n'):
                r = LogRecord(
                    name=record.name,
                    level=record.levelno,
                    pathname=record.pathname,
                    lineno=record.lineno,
                    msg=line,
                    args=tuple(),
                    exc_info=None)
                records.append(r)
            record.exc_info = None
        return records

    def emit(self, record):
        """
        Emit the specified log record.
        Provides the following:
        - Replace newlines with spaces per syslog RFCs.
        - Emit stack traces in following log records.
        :param record: A log record.
        :type record: LogRecord
        """
        for r in self.split(record):
            message = r.getMessage()
            r.msg = LogHandler.clean(message)
            r.args = tuple()
            SysLogHandler.emit(self, r)
