Django Channels Rest Framework
------------------------------

Django Channels Rest Framework provides a DRF like interface for building channels-v2 websocket consumers.


[![Build Status](https://travis-ci.org/hishnash/djangochannelsrestframework.svg?branch=master)](https://travis-ci.org/hishnash/djangochannelsrestframework)


Thanks to
---------

DCRF is based of a fork of [Channels Api](https://github.com/linuxlewis/channels-api) and of course inspired by [Django Rest Framework](http://www.django-rest-framework.org/).


Usage
-----

```python
class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

		queryset = get_user_model().objects.all()
		serializer_class = UserSerializer

```
