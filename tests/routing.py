from channels import route_class
from channels.generic.websockets import WebsocketDemultiplexer
from .test_bindings import TestModelResourceBinding


class TestDemultiplexer(WebsocketDemultiplexer):
    http_user_and_session = True

    consumers = {
        'testmodel': TestModelResourceBinding.consumer
    }

channel_routing = [
    route_class(TestDemultiplexer)
]