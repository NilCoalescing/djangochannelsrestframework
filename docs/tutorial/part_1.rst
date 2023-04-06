Tutorial Part 1: Basic Setup
============================

In this tutorial we will build a simple chat server. It will have two pages:

* An index view that lets you type the name of a chat room to join.
* A room view that lets you see messages posted in a particular chat room.

The room view will use a WebSocket to communicate with the Django server and
listen for any messages that are posted.

We assume that you are familiar with basic concepts for building a Django site.
If not we recommend you complete the Django tutorial first and then come
back to this tutorial.

We assume that you have Django installed already and the Channels Tutorial made.

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
---------------------

We will put the following code in the ``models.py`` file, to handle current rooms, messages, and current users.

.. code-block:: python

    from django.db import models
    from django.contrib.auth.models import AbstractUser


    class User(AbstractUser):
        pass


    class Room(models.Model):
        name = models.CharField(max_length=255, null=False, blank=False, unique=True)
        host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rooms")
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
        
Creating the Serializers
------------------------

We will put the following code in the ``serializers.py`` file, to handle the serialization of the models created.

.. code-block:: python

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
            fields = ["pk", "name", "host", "messages", "current_users", "last_message"]
            depth = 1
            read_only_fields = ["messages", "last_message"]
            
        def get_last_message(self, obj:Room):
            return MessageSerializer(obj.messages.order_by('created_at').last()).data


Creating the Consumers
----------------------

In the ``consumers.py`` file we will create only the room consumer for:
    * Joining and leaving a room.
    * Observing messages in that room.
    * Observing the current users in the room.

.. code-block:: python

    import json
    from django.shortcuts import get_object_or_404
    from channels.generic.websocket import AsyncWebsocketConsumer
    from channels.db import database_sync_to_async
    from django.utils.timezone import now
    from django.conf import settings
    from typing import Generator
    from djangochannelsrestframework.generics import GenericAsyncAPIConsumer, AsyncAPIConsumer
    from djangochannelsrestframework.observer.generics import (ObserverModelInstanceMixin, action)
    from djangochannelsrestframework.observer import model_observer

    from .models import Room, Message, User
    from .serializers import MessageSerializer, RoomSerializer, UserSerializer


    class RoomConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
        queryset = Room.objects.all()
        serializer_class = RoomSerializer
        lookup_field = "pk"

        async def disconnect(self, code):
            if hasattr(self, "room_subscribe"):
                await self.remove_user_from_room(self.room_subscribe)
                await self.notify_users()
            await super().disconnect(code)

        @action()
        async def join_room(self, pk, **kwargs):
            self.room_subscribe = pk
            await self.add_user_to_room(pk)
            await self.notify_users()

        @action()
        async def leave_room(self, pk, **kwargs):
            await self.remove_user_from_room(pk)

        @action()
        async def create_message(self, message, **kwargs):
            room: Room = await self.get_room(pk=self.room_subscribe)
            await database_sync_to_async(Message.objects.create)(
                room=room, 
                user=self.scope["user"],
                text=message
            )

        @action()
        async def subscribe_to_messages_in_room(self, pk, request_id, **kwargs):
            await self.message_activity.subscribe(room=pk, request_id=request_id)

        @model_observer(Message)
        async def message_activity(
            self,
            message,
            observer=None,
            subscribing_request_ids = [],
            **kwargs
        ):
            """
            This is evaluated once for each subscribed consumer.
            The result of `@message_activity.serializer` is provided here as the message.
            """
            # since we provide the request_id when subscribing we can just loop over them here.
            for request_id in subscribing_request_ids:
                message_body = dict(request_id=request_id)
                message_body.update(message)
                await self.send_json(message_body)

        @message_activity.groups_for_signal
        def message_activity(self, instance: Message, **kwargs):
            yield 'room__{instance.room_id}'
            yield f'pk__{instance.pk}'

        @message_activity.groups_for_consumer
        def message_activity(self, room=None, **kwargs):
            if room is not None:
                yield f'room__{room}'

        @message_activity.serializer
        def message_activity(self, instance:Message, action, **kwargs):
            """
            This is evaluated before the update is sent
            out to all the subscribing consumers.
            """
            return dict(data=MessageSerializer(instance).data, action=action.value, pk=instance.pk)

        async def notify_users(self):
            room: Room = await self.get_room(self.room_subscribe)
            for group in self.groups:
                await self.channel_layer.group_send(
                    group,
                    {
                        'type':'update_users',
                        'usuarios':await self.current_users(room)
                    }
                )

        async def update_users(self, event: dict):
            await self.send(text_data=json.dumps({'usuarios': event["usuarios"]}))
    
        @database_sync_to_async
        def get_room(self, pk: int) -> Room:
            return Room.objects.get(pk=pk)

        @database_sync_to_async
        def current_users(self, room: Room):
            return [UserSerializer(user).data for user in room.current_users.all()]

        @database_sync_to_async
        def remove_user_from_room(self, room):
            user:User = self.scope["user"]
            user.current_rooms.remove(room)

        @database_sync_to_async
        def add_user_to_room(self, pk):
            user:User = self.scope["user"]
            if not user.current_rooms.filter(pk=self.room_subscribe).exists():
                user.current_rooms.add(Room.objects.get(pk=pk))


Routing the Websocket
-----------------------

.. code-block:: python

    from django.urls import re_path
    from . import consumers


    websocket_urlpatterns = [
        re_path(r'ws/chat/room/$', consumers.RoomConsumer.as_asgi()),
    ]

