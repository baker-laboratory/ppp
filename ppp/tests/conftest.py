import collections
import pytest
import tempfile
import contextlib
from typing import Generator
from typing import Any

from fastapi.testclient import TestClient

import ipd
import ppp

@contextlib.contextmanager
def ppp_test_stuff() -> Generator[ipd.Bunch[Any], None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        server, backend, client = ppp.server.run(
            port=12346,
            dburl=f'sqlite:////{tmpdir}/test.db',
            workers=1,
            loglevel='warning',
        )
        ppp.server.ensure_init_db(backend)
        testclient = TestClient(backend.app)
        try:
            yield ipd.Bunch(backend=backend, server=server, client=client, testclient=testclient)
        finally:
            server.stop()

@pytest.fixture(scope='module')
def ppp_per_module():
    with ppp_test_stuff() as stuff:
        yield stuff

@pytest.fixture(scope='function')
def ppp_per_func(ppp_per_module):
    ppp_per_module.backend._clear_all_data_for_testing_only()
    ppp.server.add_defaults()
    return ppp_per_module

@pytest.fixture(scope='function')
def backend(ppp_per_func):
    return ppp_per_func.backend

@pytest.fixture(scope='function')
def server(ppp_per_func):
    return ppp_per_func.server

@pytest.fixture(scope='function')
def client(ppp_per_func):
    return ppp_per_func.client

@pytest.fixture(scope='function')
def testclient(ppp_per_func):
    return ppp_per_func.testclient
