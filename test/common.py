'''A base class for all of our common tests'''

import atexit
import os
import redis
import unittest

# Qless stuff
import qless
import logging

from testcontainers.redis import RedisContainer

REDIS_URL = os.environ.get('REDIS_URL')
if not REDIS_URL:
    _CONTAINER = RedisContainer('redis:7-alpine')
    _CONTAINER.start()
    atexit.register(_CONTAINER.stop)
    REDIS_URL = 'redis://%s:%s' % (
        _CONTAINER.get_container_host_ip(), _CONTAINER.get_exposed_port(_CONTAINER.port))


class TestQless(unittest.TestCase):
    '''Base class for all of our tests'''
    @classmethod
    def setUpClass(cls):
        qless.logger.setLevel(logging.CRITICAL)
        cls.redis = redis.Redis.from_url(REDIS_URL)
        # Clear the script cache, and nuke everything
        cls.redis.execute_command('script', 'flush')

    def setUp(self):
        assert(len(self.redis.keys('*')) == 0)
        # The qless client we're using
        self.client = qless.Client(REDIS_URL)
        self.worker = qless.Client(REDIS_URL)
        self.worker.worker_name = 'worker'

    def tearDown(self):
        # Ensure that we leave no keys behind, and that we've unfrozen time
        self.redis.flushdb()
