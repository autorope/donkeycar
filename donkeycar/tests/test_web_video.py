# -*- coding: utf-8 -*-
"""Tests for the MJPEG stream served by VideoAPI.

The behaviour under test is that each camera frame goes on the wire at
most ONCE. VideoAPI used to poll img_arr at 200Hz and re-send it whether
or not it had changed, which -- because an MJPEG stream in an <img> tag
cannot skip stale frames -- showed up to the user as a laggy camera feed.
"""
import asyncio
import os

import numpy as np
import tornado.testing
import tornado.web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from donkeycar.parts.web_controller import web
from donkeycar.parts.web_controller.web import VideoAPI

BOUNDARY = b'--boundarydonotcross'
STATIC_PATH = os.path.join(
    os.path.dirname(web.__file__), 'templates', 'static')

# Long enough that the 0.01s poll loop would have sent hundreds of copies
# of an unchanged frame under the old implementation, short enough to keep
# the suite quick.
STREAM_SECONDS = 0.5
SETTLE_SECONDS = 0.15


def _frame(value):
    """A small, distinct camera frame. Small keeps JPEG encoding cheap."""
    return np.full((24, 32, 3), value, dtype=np.uint8)


class VideoAPITest(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        app = tornado.web.Application([(r'/video', VideoAPI)])
        # VideoAPI reads both of these off the application, exactly as
        # LocalWebController and WebFpv set them up.
        app.static_file_path = STATIC_PATH
        app.img_arr = None
        return app

    async def _stream(self, script=None):
        """Read the MJPEG stream for STREAM_SECONDS and return the body.

        The stream never ends on its own, so the request timeout is what
        stops it; `script` runs concurrently and may swap img_arr to
        simulate the vehicle loop producing frames.
        """
        chunks = []
        request = HTTPRequest(self.get_url('/video'),
                              streaming_callback=chunks.append,
                              request_timeout=STREAM_SECONDS)
        fetch = AsyncHTTPClient().fetch(request, raise_error=False)
        if script is not None:
            await script()
        try:
            await fetch
        except Exception:
            pass        # timing out is the expected way to end the stream
        # The timeout closed the client end, but the handler is still
        # parked in its poll sleep. Give it one poll to wake up, fail its
        # write and return, so the loop is not torn down mid-coroutine.
        await asyncio.sleep(VideoAPI.POLL_INTERVAL * 3)
        return b''.join(chunks)

    @tornado.testing.gen_test
    async def test_placeholder_sent_once_while_no_camera_frame(self):
        """With no frame from the vehicle, send the placeholder once.

        The old code re-encoded and re-sent it every 5ms forever.
        """
        body = await self._stream()

        assert body.count(BOUNDARY) == 1

    @tornado.testing.gen_test
    async def test_unchanged_frame_is_not_resent(self):
        """The regression test: one camera frame produces one wire frame."""
        self._app.img_arr = _frame(10)

        body = await self._stream()

        assert body.count(BOUNDARY) == 1

    @tornado.testing.gen_test
    async def test_each_new_frame_is_sent(self):
        """A new array from the vehicle loop is streamed promptly."""
        async def produce_frames():
            await asyncio.sleep(SETTLE_SECONDS)
            self._app.img_arr = _frame(10)
            await asyncio.sleep(SETTLE_SECONDS)
            self._app.img_arr = _frame(200)

        body = await self._stream(script=produce_frames)

        # placeholder, then the two camera frames
        assert body.count(BOUNDARY) == 3

    @tornado.testing.gen_test
    async def test_identical_content_in_a_new_array_is_still_sent(self):
        """De-duplication is on array IDENTITY, not pixel equality.

        Two successive captures of a static scene are different frames and
        both must be sent -- comparing contents would stall the stream
        whenever the camera sees something that does not move.
        """
        async def produce_frames():
            await asyncio.sleep(SETTLE_SECONDS)
            self._app.img_arr = _frame(10)
            await asyncio.sleep(SETTLE_SECONDS)
            self._app.img_arr = _frame(10)   # equal, but a new object

        body = await self._stream(script=produce_frames)

        assert body.count(BOUNDARY) == 3
