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
# Jeff Ortel (jortel@redhat.com)

from time import sleep
from logging import getLogger

from proton import ConnectionException, Delivery
from proton.utils import SendException, LinkDetached

from gofer.common import Thread, utf8
from gofer.messaging.adapter.model import NotFound
from gofer.messaging.adapter.reliability import DAY


log = getLogger(__name__)


# reliable settings
DELAY = 10   # seconds

# resend settings
RESEND_DELAY = 10  # seconds
MAX_RESEND = DAY / RESEND_DELAY

# amqp conditions
NOT_FOUND = 'amqp:not-found'


def reliable(fn):
    def _fn(messenger, *args, **kwargs):
        repair = lambda: None
        while not Thread.aborted():
            try:
                repair()
                return fn(messenger, *args, **kwargs)
            except LinkDetached, le:
                if le.condition != NOT_FOUND:
                    log.error(utf8(le))
                    repair = messenger.repair
                    sleep(DELAY)
                else:
                    raise NotFound(*le.args)
            except ConnectionException, pe:
                log.error(utf8(pe))
                repair = messenger.repair
                sleep(DELAY)
    return _fn


def resend(fn):
    @reliable
    def _fn(sender, *args, **kwargs):
        retry = MAX_RESEND
        delay = RESEND_DELAY
        while retry > 0:
            try:
                return fn(sender, *args, **kwargs)
            except SendException, le:
                log.error(utf8(le))
                if le.state == Delivery.RELEASED:
                    sleep(delay)
                    retry -= 1
                else:
                    raise
    return _fn
