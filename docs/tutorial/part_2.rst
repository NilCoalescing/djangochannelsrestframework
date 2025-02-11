Part 2: Adding Chat Actions
===========================

With our basic `RoomConsumer` created we can add all the methods needed to join a room, listen to messages and send new
messages.

The :class:`~djangochannelsrestframework.observer.generics.ObserverModelInstanceMixin` mixin here allows us to directly subscribe to changes in any room model. We will use
this in a moment to detect if a room is deleted.

The first thing we need is a way for users to create a new chat room. To do this, we can add the :class:`~djangochannelsrestframework.mixins.CreateModelMixin`.

.. code-block:: python

    from djangochannelsrestframework.mixins import CreateModelMixin

    class RoomConsumer(CreateModelMixin, ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
        # ....

This exposes a new ``create`` action, that can be used to create a new room.
However, we would like to automatically subscribe to the room after it is created, so we will override this action.


.. code-block:: python

    from djangochannelsrestframework.mixins import CreateModelMixin

    class RoomConsumer(CreateModelMixin, ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
        @action()
        async def create(self, data: dict, request_id: str, **kwargs):
            response, status = await super().create(data, **kwargs)
            room_pk = response["pk"]
            await self.subscribe_instance(request_id=request_id, pk=room_pk)
            return response, status

Now, when we send `{action: "create", request_id: 1, data: {"name": "Lobby"}}` over the WebSocket, this will create a
new chat room called "Lobby" and subscribe the current consumer to it and changes in the room model.


Adding room joining actions
---------------------------

Next, we need to allow users to join a room. To do this, we will create a custom action that adds a user to the many-to-many list
of users in a room. We will also add another action that lets users leave a room.

.. code-block:: python

    from djangochannelsrestframework.mixins import CreateModelMixin

    class RoomConsumer(CreateModelMixin, ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
        #...

        @action()
        async def create(self, data: dict, request_id: str, **kwargs):
            response, status = await super().create(data, **kwargs)
            room_pk = response["pk"]
            await self.join_room(request_id=request_id, pk=room_pk)
            return response, status

        @action()
        async def join_room(self, pk, request_id, **kwargs):
            room = await database_sync_to_async(self.get_object)(pk=pk)
            await self.subscribe_instance(request_id=request_id, pk=room.pk)
            await self.add_user_to_room(room)

        @action()
        async def leave_room(self, pk, **kwargs):
            room = await database_sync_to_async(self.get_object)(pk=pk)
            await self.remove_user_from_room(room)
            await self.unsubscribe_instance(pk=room.pk)

        @database_sync_to_async
        def add_user_to_room(self, room: Room):
            user: User = self.scope["user"]
            room.current_users.add(user)

        @database_sync_to_async
        def remove_user_from_room(self, room: Room):
            user: User = self.scope["user"]
            room.current_users.remove(user)

Now clients can send `{action: "join_room", pk: 42}` to join a room and subscribe to updates.
We have also updated the `create` action to automatically join users to the room they create.

Sending message action
----------------------

Now, we need to be able to send a message. To do this, we will define a new action.

.. code-block:: python

    from djangochannelsrestframework.mixins import CreateModelMixin

    class RoomConsumer(CreateModelMixin, ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        # ...
        @action()
        async def create_message(self, message, room, **kwargs):
            room: Room = await database_sync_to_async(self.get_object)(pk=room)
            await database_sync_to_async(Message.objects.create)(
                room=room,
                user=self.scope["user"],
                text=message
            )

This will create a new message when sending `{action: "create_message", message: "Hello Alice!", room: 42}`.

Subscribing to all messages within a room
-----------------------------------------

Now, we need to create a way for other room members to be notified when a message is sent. To do this, we will add a
model observer to observe all messages sent to a room.

.. code-block:: python

    from djangochannelsrestframework.mixins import CreateModelMixin

    class RoomConsumer(CreateModelMixin, ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        # ...
        @model_observer(Message)
        async def message_activity(
            self,
            message,
            observer=None,
            subscribing_request_ids=[],
            **kwargs
        ):
            """
            This is evaluated once for each subscribed consumer.
            The result of `@message_activity.serializer` is provided here as the message.
            """
            # Since we provide the request_id when subscribing, we can just loop over them here.
            for request_id in subscribing_request_ids:
                message_body = dict(request_id=request_id)
                message_body.update(message)
                await self.send_json(message_body)

        @message_activity.groups_for_signal
        def message_activity(self, instance: Message, **kwargs):
            yield f'room__{instance.room_id}'

        @message_activity.groups_for_consumer
        def message_activity(self, room=None, **kwargs):
            if room is not None:
                yield f'room__{room}'

        @message_activity.serializer
        def message_activity(self, instance: Message, action, **kwargs):
            """
            This is evaluated before the update is sent
            out to all the subscribing consumers.
            """
            return dict(
                data=MessageSerializer(instance).data,
                action=action.value,
                pk=instance.pk
            )

Here, we create a new custom `message_activity` observer that groups all changes to messages by room ID.
The `groups_for_signal` and `groups_for_consumer` methods are used to group these events.
We also provide a custom `serializer` to ensure we only serialize the message once, even if we have hundreds of subscribers.

With this observer created, we now need to subscribe to it when we join a room.

.. code-block:: python

    from djangochannelsrestframework.mixins import CreateModelMixin

    class RoomConsumer(CreateModelMixin, ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        # ...
        @action()
        async def join_room(self, pk, request_id, **kwargs):
            room = await database_sync_to_async(self.get_object)(pk=pk)
            await self.subscribe_instance(request_id=request_id, pk=room.pk)
            await self.message_activity.subscribe(room=pk, request_id=request_id)
            await self.add_user_to_room(room)

        @action()
        async def leave_room(self, pk, **kwargs):
            room = await database_sync_to_async(self.get_object)(pk=pk)
            await self.unsubscribe_instance(pk=room.pk)
            await self.message_activity.unsubscribe(room=room.pk)
            await self.remove_user_from_room(room)


Now, when you join a room, you will not only subscribe to changes in the room model but also to all messages sent in that room.

It is worth noting that in this example we do not track if a user goes offline dropping the connection while still in a room.
