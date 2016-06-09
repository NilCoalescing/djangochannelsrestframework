import logging

from channels.generic import websockets


class ApiWebsocketConsumer(websockets.JsonWebsocketConsumer):
    """This consumer class implements the routing scheme for the REST streaming API."""

    strict_ordering = True

    def receive(self, content):

        if "method" in content:
            # reroute to the other consumer
            channel_name = content.pop("method")
            self.message.channel_name = channel_name
            self.message.channel.name = channel_name
            match = self.message.channel_layer.router.match(self.message)

            if match is None:
                logging.error("Could not find match for message %s! Check your routing.", self.message.channel_name)
            else:
                consumer, kwargs = match
                consumer(self.message, **kwargs)
