"""Project-wide pytest fixtures: test infrastructure that isn't any one app's (brief 006).

The network block (criterion 45, D17): no test may reach Zoom, or anything else, over HTTP.
``responses`` patches ``requests``' transport adapter for every test, so any ``requests`` call
to a URL a test hasn't registered raises ``requests.exceptions.ConnectionError`` instead of
leaving the machine. It patches the adapter class, not a thread-local, so calls made from
worker threads (the preview's parallel lookups, the race tests) are blocked too.

It uses ``responses``' default mock, so a test registers replies with either
``responses.add(...)`` or the ``http_mock`` fixture (the same object), and reads
``http_mock.calls``. Don't decorate tests with ``@responses.activate``: leaving it would stop
this block for the rest of the test.
"""

import pytest
import responses


@pytest.fixture(autouse=True)
def http_mock():
    """Block real HTTP for the whole test and hand the mock to tests that register replies.

    ``assert_all_requests_are_fired`` stays False (the default mock's setting): a registered
    reply a test doesn't use is not an error here; tests assert on ``calls`` instead.
    """
    responses.start()
    try:
        yield responses.mock
    finally:
        responses.stop()
        responses.reset()
