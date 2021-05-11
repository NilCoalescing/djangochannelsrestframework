View as consumer
================


Introduction
------------
Suppose we already have a functional API that uses Django Rest Framework, and we 
want to add some websocket functionality. We can use the ``view_as_consumer`` 
decorator for accessing the same ``REST`` methods.




Creating the serializers.
-------------------------

.. code-block:: python

    # serializers.py
    from django.contrib.auth.models import User
    from rest_framework import serializers

    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ["id", "username", "email"]

Creating the view sets.
-----------------------

.. code-block:: python

    # views.py
    from rest_framework.viewsets import ModelViewSet
    from django.contrib.auth.models import User
    from .serializers import UserSerializer

    class UserViewSet(ModelViewSet):
        queryset = User.objects.all()
        serializer_class = UserSerializer

Routing the consumer
--------------------

Using the same ``UserViewSet`` we can map some basic websocket actions 
to the REST methods. The mapped actions are:

* ``create`` - ``PUT``
* ``update`` - ``PATCH``
* ``list`` - ``GET``
* ``retrieve`` - ``GET``

.. code-block:: python

    # routing.py
    from django.urls import re_path
    from djangochannelsrestframework.consumers import view_as_consumer
    from .views import UserViewSet

    websocket_urlpatterns = [
        re_path(r"^user/$", view_as_consumer(UserViewSet.as_view()))
    ]


Manual testing the output.
--------------------------

Now we will have a websocket client in javascript listening to the messages, after subscribing to the comment activity.
This codeblock can be used it in the browser console.

.. note::
    In producction the ``ws:`` is ``wss:``, we can check it with the following code:
        .. code-block:: javascript
            
            const ws_schema = window.location.protocol === "http:" ? "ws:" : "wss:";

.. code-block:: javascript

    const ws = new WebSocket("ws://localhost:8000/user/")
    const ws.onopen = function(){
        ws.send(JSON.stringify({
            action: "list",
            request_id: new Date().getTime(),
        }))
    }
    const ws.onmessage = function(e){
        console.log(e)
    }


.. warning::
    At this point we should have some users in our database, otherwise create them

In the console we will have the following response assuming that we have some 
users in our database.

.. code-block:: javascript

    {
        error: [],
        data: [
            {username: "user 1", id: 1, email: "1@example.com"},
            {username: "user 2", id: 2, email: "2@example.com"},
        ],
        action: "list",
        response_status: 200,
        request_id: 15050500
    }