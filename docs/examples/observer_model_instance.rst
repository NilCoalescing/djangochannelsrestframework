Observer model instance
=======================

This mixin consumer lets you subscribe to all changes of a specific instance, and 
also gives you access to the ``retrieve`` action.

.. code-block:: python

    # serializers.py
    from rest_framework import serializers
    from django.contrib.auth.models import User
    class UserSerializer(serializers.ModelSerializer):
        
        class Meta:
            model = User
            fields = ["id", "username", "email", "password"]
            extra_kwargs = {'password': {'write_only': True}}
        
        def create(self, validated_data):
            user = User(
                email=validated_data['email'],
                username=validated_data['username']
            )
            user.set_password(validated_data['password'])
            user.save()
            return user

.. code-block:: python

    # consumers.py
    from django.contrib.auth.models import User
    from .serializers import UserSerializer
    from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
    from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin

    class UserConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
        queryset = User.objects.all()
        serializer_class = UserSerializer

.. code-block:: python

    # routing.py
    from django.urls import re_path
    from . import consumers

    websocket_urlpatterns = [
        re_path(r"^ws/$", consumers.UserConsumer.as_asgi()),
    ]



How to use it
-------------

First we will create the web socket instance in ``javascript``.

.. code-block:: javascript

    const ws = new WebSocket("ws://localhost:8000/ws/")

    ws.onmessage = function(e){
        console.log(e)
    }

.. note::
    We must have a few users in our database for testing, if not, create them.

Retrieve action.
----------------
.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "retrieve",
        request_id: new Date().getTime(),
        pk: 1,
    }))
    /* The return response will be something like this.
    {
        "action": "list",
        "errors": [],
        "response_status": 200,
        "request_id": 1550050,
        "data": {'email': '1@example.com', 'id': 1, 'username': 'test 1'},
    }
    */


Subscription
------------
1. Subscribe to a specific instance.

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "retrieve",
        request_id: new Date().getTime(),
        pk: 1,
    }))
    /* After subscribing the response will be something like this.
    {
        "action": "subscribe_instance",
        "errors": [],
        "response_status": 201,
        "request_id": 1550050,
        "data": null,
    }
    */

2. Changing the model instance in from the shell will fire the subscription event.

.. code-block:: python

    >>> from django.contrib.auth.models import User
    >>> user = User.objects.get(pk=1)
    >>> user.username = "edited user name"
    >>> user.save()

3. After saving the model instance, in the console, we will see the subscription message.

.. code-block:: json

    {
        "action": "update",
        "errors": [],
        "response_status": 200,
        "request_id": 1550050,
        "data": {'email': '1@example.com', 'id': 1, 'username': 'edited user name'},
    }


Todo
----

* More detail example.
