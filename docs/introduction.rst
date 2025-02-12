Introduction
============

------------------------------
Django Channels Rest Framework
------------------------------

Django Channels Rest Framework provides a DRF like interface for building channels-v4_ websocket consumers.


This project can be used alongside HyperMediaChannels_ and ChannelsMultiplexer_ 
to create a Hyper Media Style API over websockets. However Django Channels Rest Framework
is also a free standing framework with the goal of providing an API that is familiar to DRF users.

Expose Actions Over WebSockets
------------------------------

Django Channels Rest Framework allows exposing methods as callable actions over WebSockets using a decorator.
By applying the :func:`~djangochannelsrestframework.decorators.action` decorator to consumer methods,
these methods become accessible to WebSocket clients, enabling direct invocation with structured request and response handling.
This provides a straightforward way to define and manage WebSocket-based interactions while maintaining a clear and
organized API structure.

.. code-block:: python

    #! consumers.py
    from djangochannelsrestframework.decorators import action
    from djangochannelsrestframework.consumers import AsyncAPIConsumer

    class MyConsumer(AsyncAPIConsumer):

        @action()
        async def delete_user(self, request_id, user_pk, **kwargs):
            ...


CRUD Operations Over WebSockets
-------------------------------

Django Channels Rest Framework provides mixins similar to those in Django REST Framework to handle CRUD operations
over WebSockets. By using the provided :doc:`mixins <mixins>`, a
:class:`~djangochannelsrestframework.generics.GenericAsyncAPIConsumer` can implement standardized WebSocket-based
create, retrieve, list, update, and delete operations for models. These mixins handle serialization, validation,
:doc:`permissions <permissions>` and response serialization.

.. code-block:: python

    #! consumers.py
    from .models import User
    from .serializers import UserSerializer
    from djangochannelsrestframework import permissions
    from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
    from djangochannelsrestframework.mixins import CreateModelMixin

    class LiveConsumer(CreateModelMixin, GenericAsyncAPIConsumer):
        queryset = User.objects.all()
        serializer_class = UserSerializer
        permission_classes = (permissions.AllowAny,)

Model Subscriptions Over WebSockets
-----------------------------------

Django Channels Rest Framework provides the
:class:`~djangochannelsrestframework.observer.generics.ObserverModelInstanceMixin` mixin, which allows consumers to
subscribe to changes in individual model instances.
This enables WebSocket clients to receive real-time updates when a specific model instance is created, updated,
or deleted. For more custom observations, the :func:`~djangochannelsrestframework.observer.model_observer` decorator
can be used to subscribe to changes in collections of models. This allows defining granular event listeners that
broadcast updates to WebSocket clients when changes occur in the database.
Observation tracks all changes made through the django ORM include those made from other api endpoints or even the
django admin, cli etc.

.. code-block:: python

    #! consumers.py
    from .models import User, Comment
    from .serializers import UserSerializer
    from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
    from djangochannelsrestframework.observer import model_observer

    class MyConsumer(GenericAsyncAPIConsumer):
        queryset = User.objects.all()
        serializer_class = UserSerializer

        @model_observer(Comment)
        async def comment_activity(self, message, observer=None, subscribing_request_ids=[], **kwargs):
            for request_id in subscribing_request_ids:
                await self.send_json({"message": message, "request_id": request_id})

        @comment_activity.groups_for_signal
        def comment_activity(self, instance, **kwargs):
            yield f'comment__{instance.user_id}'

        @comment_activity.groups_for_consumer
        def comment_activity(self, user_pk, **kwargs):
            if user_pk:
                yield f'comment__{user_pk}'

        @action()
        async def subscribe_to_comment_activity(self, request_id, user_pk, **kwargs):
            await self.comment_activity.subscribe(request_id=request_id, user_pk=user_pk)


Detached Actions
----------------

Django Channels Rest Framework supports detached actions, allowing consumers to handle long-running tasks asynchronously
without blocking the WebSocket connection.
By using the :func:`~djangochannelsrestframework.decorators.action` with `detached=True` actions are executed in a
separate child task. This ensures that WebSocket clients can send and receive further messages while the action runs,
making it suitable for tasks such as sending emails, processing data, or interacting with external APIs.

.. code-block:: python

    #! consumers.py
    from djangochannelsrestframework.decorators import action
    from djangochannelsrestframework.consumers import AsyncAPIConsumer

    class MyConsumer(AsyncAPIConsumer):

        @action(detached=True)
        async def send_invite_emails(self, request_id, user_pk, **kwargs):
            ...

------------
Installation
------------

.. code-block:: bash

    pip install djangochannelsrestframework

Since this package depends on Django Channels you do need to add `channels` to your projects `INSTALLED_APPS`.

---------
Thanks to
---------


DCRF is based of a fork of `Channels Api <https://github.com/linuxlewis/channels-api>`_ and of course inspired by `Django Rest Framework <http://www.django-rest-framework.org/>`_.



.. _post: https://lostmoa.com/blog/DjangoChannelsRestFramework/
.. _GenericAPIView: https://www.django-rest-framework.org/api-guide/generic-views/
.. _channels-v4: https://channels.readthedocs.io/en/latest/
.. _dcrf-client: https://github.com/theY4Kman/dcrf-client
.. _theY4Kman: https://github.com/theY4Kman
.. _HyperMediaChannels: https://github.com/hishnash/hypermediachannels
.. _ChannelsMultiplexer: https://github.com/hishnash/channelsmultiplexer
