# Django Channels Rest Framework

Django Channels Rest Framework provides a DRF like interface for building channels-v2 websocket consumers.


[![Build Status](https://travis-ci.org/hishnash/djangochannelsrestframework.svg?branch=master)](https://travis-ci.org/hishnash/djangochannelsrestframework)


## Thanks to


DCRF is based of a fork of [Channels Api](https://github.com/linuxlewis/channels-api) and of course inspired by [Django Rest Framework](http://www.django-rest-framework.org/).


# How to Use



### Observing a Model instance
Consumer that accepts subscribtions to an instance.
```python
class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
```

this exposes the `retrieve` and `subscribe_instance` actions to that instance.

to subscribe send:
```python
{
    "action": "subscribe_instance",
    "pk": 42,  # the id of the instance you are subscribing to
    "request_id": 4  # this id will be used for all resultent updates.
}
```

Actions will be sent down out from the server:
```python
{
    "action": "update",
    "errors": [],
    "response_status": 200,
    "request_id": 4,
    "data": {'email': '42@example.com', 'id': 42, 'username': 'thenewname'},
}
```
