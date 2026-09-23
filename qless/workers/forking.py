"""A worker that forks child processes"""

import errno
import os
import signal
import sys

import psutil

from qless import _reloadLogger, logger, util

# Internal imports
from . import Worker
from .serial import SerialWorker


class ForkingWorker(Worker):
    """A worker that forks child processes"""

    def __init__(self, *args, **kwargs):
        Worker.__init__(self, *args, **kwargs)
        # Worker class to use
        self.klass = self.kwargs.pop('klass', SerialWorker)
        # How many children to launch
        self.count = self.kwargs.pop('workers', 0) or psutil.cpu_count()
        # A dictionary of child pids to information about them
        self.sandboxes = {}
        # Whether or not we're supposed to shutdown
        self.shutdown = False

    def stop(self, sig=signal.SIGINT):
        """Stop all the workers, and then wait for them"""
        for cpid in list(self.sandboxes.keys()):
            logger.warning(f'Stopping {cpid}...')
            os.kill(cpid, sig)

        # While we still have children running, wait for them
        for cpid in list(self.sandboxes.keys()):
            try:
                logger.info(f'Waiting for {cpid}...')
                pid, status = os.waitpid(cpid, 0)
                logger.warning(f'{pid} stopped with status {status >> 8}')
            except OSError:  # pragma: no cover
                logger.exception(f'Error waiting for {cpid}...')
            finally:
                self.sandboxes.pop(pid, None)

    def spawn(self, **kwargs):
        """Return a new worker for a child process"""
        copy = dict(self.kwargs)
        copy.update(kwargs)
        # Apparently there's an issue with importing gevent in the parent
        # process and then using it in the child. This is meant to relieve that
        # problem by allowing `klass` to be specified as a string.
        if isinstance(self.klass, str):
            self.klass = util.import_class(self.klass)
        return self.klass(self.queues, self.client, **copy)

    def run(self):
        """Run this worker"""
        self.signals(('TERM', 'INT', 'QUIT', 'HUP'))
        # Divide up the jobs that we have to divvy up between the workers. This
        # produces evenly-sized groups of jobs
        resume = self.divide(self.resume, self.count)
        for index in range(self.count):
            # The sandbox for the child worker
            sandbox = os.path.join(os.getcwd(), 'qless-py-workers', f'sandbox-{index}')
            cpid = os.fork()
            if cpid:
                logger.info(f'Spawned worker {cpid}')
                self.sandboxes[cpid] = sandbox
            else:  # pragma: no cover
                # Move to the sandbox as the current working directory
                with Worker.sandbox(sandbox):
                    os.chdir(sandbox)
                    self.spawn(resume=resume[index], sandbox=sandbox).run()
                    sys.exit(0)

        try:
            while not self.shutdown:
                try:
                    pid, status = os.wait()
                    logger.warning(f'Worker {pid} died with status {status >> 8} from signal {status & 0xFF}')
                    sandbox = self.sandboxes.pop(pid)
                    cpid = os.fork()
                    if cpid:
                        logger.info(f'Spawned replacement worker {cpid}')
                        self.sandboxes[cpid] = sandbox
                    else:  # pragma: no cover
                        with Worker.sandbox(sandbox):
                            os.chdir(sandbox)
                            self.spawn(sandbox=sandbox).run()
                            sys.exit(0)
                except OSError as e:
                    if e.errno == errno.EINTR:
                        continue
                    else:
                        raise
        finally:
            self.stop(signal.SIGKILL)

    def handler(self, signum, frame):  # pragma: no cover
        """Signal handler for this process"""
        if signum in (signal.SIGTERM, signal.SIGINT, signal.SIGQUIT, signal.SIGHUP):
            for cpid in list(self.sandboxes.keys()):
                os.kill(cpid, signum)
            if signum == signal.SIGHUP:
                # HUP - reload logging configuration
                _reloadLogger()
            else:
                sys.exit(0)
