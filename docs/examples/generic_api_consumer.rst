Generic Api Consumer
====================

In DCRF you can create a GenericAsyncAPIConsumer that works much like a GenericAPIView in DRF: 
For a more indeph look into Rest Like Websocket consumers read this blog post.

We have a set of mixins for the consumer, that add diferent accions based on the CRUD
operations.

* ``ListModelMixin`` this mixin add the action ``list``, allows to retrieve all instances of a model class.
* ``RetrieveModelMixin`` this mixin add the action ``retrieve`` allows to retrieve an object based on the pk sent.
* ``PatchModelMixin`` this mixin add the action ``patch``, allows to patch an instance of a model.
* ``UpdateModelMixin`` this mixin add the action ``update``, allows to update a model instance.
* ``CreateModelMixin`` this mixin add the action ``create``, allows to create an instance based on the data sent.
* ``DeleteModelMixin`` this mixin add the action ``delete``, allows to delete an instance based on the pk sent.

Example
-------

This example shows how to create a basic consumer for the django's auth user model. We 
are going to create a serializer class for it, and mixin with the ``GenericAsyncAPIConsumer`` the action mixins.

.. code-block:: python

    # serializers.py
    from rest_framework import serializers
    from django.contrib.auth.models import User
    class UserSerilizer(serailizers.ModelSerializer):
        
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
    from .serializers import UserSerilizer
    from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
    from djangochannelsrestframework.mixins import (
        ListModelMixin,
        RetrieveModelMixin,
        PatchModelMixin,
        UpdateModelMixin,
        CreateModelMixin,
        DeleteModelMixin,
    )

    class UserConsumer(
            ListModelMixin, 
            RetrieveModelMixin,
            PatchModelMixin,
            UpdateModelMixin,
            CreateModelMixin,
            DeleteModelMixin,
            GenericAsyncAPIConsumer,
        ):
        queryset = User.objects.all()
        serializer_class = UserSerilizer

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

1. List action.

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "list",
        request_id: new Date().getTime(),
    }))
    /* The return response will be something like this.
    {
        "action": "list",
        "errors": [],
        "response_status": 200,
        "request_id": 1550050,
        "data": [
            {'email': '1@example.com', 'id': 1, 'username': 'test 1'},
            {'email': '2@example.com', 'id': 2, 'username': 'test 2'},
            {'email': '3@example.com', 'id': 3, 'username': 'test 3'},
        ]
    }
    */

2. Retrieve action.

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "retrieve",
        request_id: new Date().getTime(),
        pk: 2,
    }))
    /* The return response will be something like this.
    {
        "action": "retrieve",
        "errors": [],
        "response_status": 200,
        "request_id": 1550050,
        "data": {'email': '2@example.com', 'id': 2, 'username': 'test 2'},
        }
    */

3. Patch action.

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "patch",
        request_id: new Date().getTime(),
        pk: 2,
        data: {
            email: "edited@example.com",
        }
    }))
    /* The return response will be something like this.
    {
        "action": "patch",
        "errors": [],
        "response_status": 200,
        "request_id": 1550050,
        "data": {'email': 'edited@example.com', 'id': 2, 'username': 'test 2'},
        }
    */


4. Update action.

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "update",
        request_id: new Date().getTime(),
        pk: 2,
        data: {
            username: "user 2",
        }
    }))
    /* The return response will be something like this.
    {
        "action": "update",
        "errors": [],
        "response_status": 200,
        "request_id": 1550050,
        "data": {'email': 'edited@example.com', 'id': 2, 'username': 'user 2'},
        }
    */

5. Create action.

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "create",
        request_id: new Date().getTime(),
        data: {
            username: "new user 4",
            password1: "testpassword123",
            password2: "testpassword123",
            email: "4@example.com",
        }
    }))
    /* The return response will be something like this.
    {
        "action": "create",
        "errors": [],
        "response_status": 201,
        "request_id": 1550050,
        "data": {'email': '4@example.com', 'id': 4, 'username': 'new user 4'},
        }
    */

6. Delete action.

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "delete",
        request_id: new Date().getTime(),
        pk: 4,
    }))
    /* The return response will be something like this.
    {
        "action": "delete",
        "errors": [],
        "response_status": 204,
        "request_id": 1550050,
        "data": null,
        }
    */