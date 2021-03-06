from logging import getLogger
from time import sleep

from gofer.decorators import remote
from gofer.rmi.model import FORK
from gofer.agent.plugin import Plugin
from gofer.agent.rmi import Context


plugin = Plugin.find(__name__)
log = getLogger(__name__)


class Panther(object):

    @remote(model=FORK)
    def test(self):
        return 'done'

    @remote(model=FORK)
    def sleep(self, n=90):
        while n > 0:
            log.info('sleeping')
            sleep(1)
            n -= 1
        return 'done'

    @remote(model=FORK)
    def test_progress(self):
        total = 30
        context = Context.current()
        context.progress.total = total
        context.progress.report()
        for n in range(total):
            context.progress.completed = n
            context.progress.report()
        return 'done'

    @remote(model=FORK)
    def test_exceptions(self):
        raise ValueError('That was bad')
