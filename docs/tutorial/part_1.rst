Part 1: Basic Setup
====================

In this tutorial we will build a simple chat server. It will have two pages:

* An index view that lets you type the name of a chat room to join.
* A room view that lets you see messages posted in a particular chat room.

The room view will use a WebSocket to communicate with the Django server and
listen for any messages that are posted.

We assume that you are familiar with basic concepts for building a Django site.
If not we recommend you complete the Django tutorial first and then come
back to this tutorial.

We assume that you have Django installed already and the `Channels Tutorial <https://channels.readthedocs.io/en/latest/tutorial/part_1.html>`_ made.

Next, install DCRF into the same environment that was used to setup the Channels Tutorial.

.. code-block:: bash

    pip install djangochannelsrestframework

This will be the directory tree at the end of the Channels Tutorial and we will add the following Python files:
    - ``serializers.py``
    - ``models.py``
    - ``routing.py``

.. code-block:: text


    mysite/
        manage.py
        mysite/
            __init__.py
            asgi.py
            settings.py
            urls.py
            wsgi.py
        chat/
            __init__.py
            consumers.py
            models.py
            serializers.py
            routing.py
            templates/
                chat/
                    index.html
                    room.html
            tests.py
            urls.py
            views.py


Creating the Models
-------------------

We will put the following code in the ``models.py`` file, to handle current rooms, messages, and current users.

.. code-block:: python

    # chat/models.py
    from django.db import models
    from django.contrib.auth.models import AbstractUser


    class User(AbstractUser):
        pass


    class Room(models.Model):
        name = models.CharField(max_length=255, null=False, blank=False, unique=True)
        current_users = models.ManyToManyField(User, related_name="current_rooms", blank=True)

        def __str__(self):
            return f"Room({self.name} {self.host})"


    class Message(models.Model):
        room = models.ForeignKey("chat.Room", on_delete=models.CASCADE, related_name="messages")
        text = models.TextField(max_length=500)
        user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
        created_at = models.DateTimeField(auto_now_add=True)

        def __str__(self):
            return f"Message({self.user} {self.room})"

Update AUTH Settings
--------------------

Add the following to ``mysite/settings.py`` to properly register the new ``User`` ``Model``.

.. code-block:: python

    AUTH_USER_MODEL = 'chat.User'

Creating the Serializers
------------------------

We will put the following code in the ``serializers.py`` file, to handle the serialization of the models created.

.. code-block:: python

    # chat/serializers.py
    from .models import User, Room, Message
    from rest_framework import serializers


    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            exclude = ["password"]


    class MessageSerializer(serializers.ModelSerializer):
        created_at_formatted = serializers.SerializerMethodField()
        user = UserSerializer()

        class Meta:
            model = Message
            exclude = []
            depth = 1

        def get_created_at_formatted(self, obj:Message):
            return obj.created_at.strftime("%d-%m-%Y %H:%M:%S")

    class RoomSerializer(serializers.ModelSerializer):
        last_message = serializers.SerializerMethodField()
        messages = MessageSerializer(many=True, read_only=True)

        class Meta:
            model = Room
            fields = ["pk", "name", "messages", "current_users", "last_message"]
            depth = 1
            read_only_fields = ["messages", "last_message"]
            
        def get_last_message(self, obj:Room):
            return MessageSerializer(obj.messages.order_by('created_at').last()).data

Creating the Consumers
----------------------

In the ``consumers.py`` file, we will create only the room consumer.

.. code-block:: python

    # chat/consumers.py
    import json

    from channels.db import database_sync_to_async
    from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
    from djangochannelsrestframework.observer import model_observer
    from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin, action

    from .models import Message, Room, User
    from .serializers import MessageSerializer, RoomSerializer, UserSerializer


    class RoomConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
        queryset = Room.objects.all()
        serializer_class = RoomSerializer
        lookup_field = "pk"


Routing the Websocket
---------------------

.. code-block:: python

    # chat/routing.py
    from django.urls import re_path
    from . import consumers


    websocket_urlpatterns = [
        re_path(r'ws/chat/room/$', consumers.RoomConsumer.as_asgi()),
    ]

