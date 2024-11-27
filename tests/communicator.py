import asyncio
from contextlib import asynccontextmanager
from typing import Awaitable

from asgiref.timeout import timeout as async_timeout

from channels.testing import WebsocketCommunicator


class Communicator(WebsocketCommunicator):
    """
    Custom communicator class for WebSocket communication in tests.

    This override resolves an issue where the default ApplicationCommunicator
    cancels the application future unnecessarily when a timeout occurs
    while waiting for output. This behavior disrupts subsequent attempts
    to receive output or reconnect, causing the application to raise
    CancelledError.

    The `receive_output` method is modified to:
    - Avoid cancelling the application future when a timeout occurs.
    - Ensure that the method can be called repeatedly without causing
      failures in subsequent operations.

    This makes the communicator more flexible for tests where output
    availability is uncertain, allowing patterns like:

        outputs = []
        while True:
            try:
                outputs.append(await communicator.receive_output())
            except asyncio.TimeoutError:
                break
    """
    _connected = False

    @property
    def connected(self):
        return self._connected

    async def receive_output(self, timeout=1):
        if self.future.done():
            self.future.result()  # Ensure exceptions are re-raised if future is complete
        try:
            async with async_timeout(timeout):  # Wait for output with a timeout
                return await self.output_queue.get()
        except asyncio.TimeoutError as e:
            if self.future.done():  # Re-check the state of the future after the timeout
                self.future.result()
            raise e  # Propagate the timeout exception

    async def connect(self, timeout=1):
        self._connected, subprotocol = await super().connect(timeout)
        return self._connected, subprotocol

    async def disconnect(self, code=1000, timeout=1):
        await super().disconnect(code, timeout)
        self._connected = False


@asynccontextmanager
async def connected_communicator(consumer, path: str = "/testws/") -> Awaitable[Communicator]:
    """
    Asynchronous context manager for managing WebSocket communicator lifecycle.

    This utility simplifies tests involving WebSocket communication by:
    - Initializing and connecting a Communicator instance for the given consumer and path.
    - Ensuring the connection is properly established, raising an assertion error if not.
    - Guaranteeing cleanup by disconnecting the communicator upon exiting the context.

    Example usage:

        async with connected_communicator(TestConsumer) as communicator:
            await communicator.send_json_to({"key": "value"})
            response = await communicator.receive_json_from()
            assert response == {"key": "value"}
    """
    communicator = Communicator(consumer, path)
    connected, _ = await communicator.connect()
    try:
        assert connected, "Failed to connect to WebSocket"
        yield communicator
    finally:
        if communicator.connected:
            await communicator.disconnect()
