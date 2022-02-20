Generic Api Consumer
====================

In DCRF you can create a GenericAsyncAPIConsumer that works much like a GenericAPIView in DRF.

There are set of mixins for the consumer, that add different actions based on the CRUD
operations.

* ``ListModelMixin`` this mixin adds the action ``list``, allows to retrieve all instances of a model class.
* ``RetrieveModelMixin`` this mixin adds the action ``retrieve`` allows to retrieve an object based on the pk sent.
* ``PatchModelMixin`` this mixin adds the action ``patch``, allows to patch an instance of a model.
* ``UpdateModelMixin`` this mixin adds the action ``update``, allows to update a model instance.
* ``CreateModelMixin`` this mixin adds the action ``create``, allows to create an instance based on the data sent.
* ``DeleteModelMixin`` this mixin adds the action ``delete``, allows to delete an instance based on the pk sent.

Example
-------

This example shows how to create a basic consumer for the django's auth user model. We 
are going to create a serializer class for it, and mixin with the ``GenericAsyncAPIConsumer`` the action mixins.

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

1. :doc:`List action<../mixins>`.

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "list",
        request_id: new Date().getTime()
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

2. :doc:`Retrieve action.<../mixins>`

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "retrieve",
        request_id: new Date().getTime(),
        pk: 2
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

3. :doc:`Patch action.<../mixins>`

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "patch",
        request_id: new Date().getTime(),
        pk: 2,
        data: {
            email: "edited@example.com"
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


4. :doc:`Update action.<../mixins>`

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "update",
        request_id: new Date().getTime(),
        pk: 2,
        data: {
            username: "user 2"
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

5. :doc:`Create action.<../mixins>`

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "create",
        request_id: new Date().getTime(),
        data: {
            username: "new user 4",
            password: "testpassword123",
            email: "4@example.com"
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

6. :doc:`Delete action.<../mixins>`

.. code-block:: javascript

    ws.send(JSON.stringify({
        action: "delete",
        request_id: new Date().getTime(),
        pk: 4
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


Full example
-------------

.. code-block:: text


    mysite/
        manage.py
        mysite/
            __init__.py
            asgi.py
            settings.py
            urls.py
            wsgi.py
        example/
            __init__.py
            consumers.py
            models.py
            serializers.py
            routing.py
            templates/
                example/
                    index.html
            tests.py
            urls.py
            views.py

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
        serializer_class = UserSerializer

.. code-block:: python

    # routing.py
    from django.urls import re_path
    from . import consumers

    websocket_urlpatterns = [
        re_path(r"^ws/$", consumers.UserConsumer.as_asgi()),
    ]


.. code-block:: python

    from django.shortcuts import render, reverse


    def index(request):
        return render(request, 'example/index.html')


.. code-block:: html

    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Generic Api Consumer</title>
    </head>
    <body>

    <button id="list">List</button>
    <button id="retrieve">Retrieve</button>
    <button id="create">Create</button>
    <button id="patch">Patch</button>
    <button id="update">Update</button>
    <button id="delete">Delete</button>

    <pre id="response"></pre>

    <script>
        const ws = new WebSocket("ws://localhost:8000/ws/")

        ws.onmessage = function (e) {
            document.getElementById("response").textContent = JSON.stringify(JSON.parse(e.data), undefined, 2);
            console.log(e.data)
        }

        document.querySelector('#list').onclick = function (e) {
            ws.send(JSON.stringify({
                action: "list",
                request_id: new Date().getTime()
            }))
        };

        document.querySelector('#retrieve').onclick = function (e) {
            ws.send(JSON.stringify({
                action: "retrieve",
                request_id: new Date().getTime(),
                pk: 2
            }))
        }

        document.querySelector('#create').onclick = function (e) {
            ws.send(JSON.stringify({
                action: "create",
                request_id: new Date().getTime(),
                data: {
                    username: "newuser4",
                    password: "testpassword123",
                    email: "4@example.com"
                }
            }))
        }

        document.querySelector('#patch').onclick = function (e) {
            ws.send(JSON.stringify({
                action: "patch",
                request_id: new Date().getTime(),
                pk: 2,
                data: {
                    email: "edited@example.com"
                }
            }))
        }

        document.querySelector('#update').onclick = function (e) {
            ws.send(JSON.stringify({
                action: "update",
                request_id: new Date().getTime(),
                pk: 2,
                data: {
                    username: "user 2"
                }
            }))
        }

        document.querySelector('#delete').onclick = function (e) {
            ws.send(JSON.stringify({
                action: "delete",
                request_id: new Date().getTime(),
                pk: 2
            }))
        }
    </script>
    </body>
    </html>
