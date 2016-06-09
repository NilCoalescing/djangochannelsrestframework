from channels.routing import route_class

from .consumers import ApiWebsocketConsumer

channel_routing = [
    route_class(ApiWebsocketConsumer, path='/')
]
