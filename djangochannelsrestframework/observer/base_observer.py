import hashlib
from typing import Any, Dict, Generator, Callable, Optional
from uuid import uuid4

from djangochannelsrestframework.consumers import AsyncAPIConsumer
from djangochannelsrestframework.observer.utils import ObjPartial
class BaseObserver:
    """Base observer class"""

    def __init__(self, func, partition: str = "*"):
        self.func = func
        self._serializer = None
        self._group_names_for_signal = None
        self._group_names_for_consumer = None

        self._stable_observer_id = f"{partition}-{self.__class__.__name__}-{self.func.__module__}.{self.func.__name__}"

    async def __call__(self, *args, consumer=None, **kwargs):
        return await self.func(consumer, *args, observer=self, **kwargs)

    def __get__(self, parent, objtype):
        if parent is None:
            return self

        return ObjPartial(self, consumer=parent)

    def serialize(self, signal, *args, **kwargs) -> Dict[str, Any]:
        message = {}
        if self._serializer:
            message = self._serializer(self, signal, *args, **kwargs)
        message["type"] = self.func.__name__.replace("_", ".")

        return message

    def serializer(self, func):
        """Adds a Serializer to the model observer return.

        .. note::
            This is meant to use as a decorator.

        Examples:
            TODO path to examples?

            .. code-block:: python
                
                # models.py
                from django.db import models
                from django.contrib.auth.models import AbstractUser

                class User(AbstractUser):
                    pass

                class Comment(models.Model):
                    text = models.TextField()
                    user = models.ForeignKey(User, related_name="comments", on_delete=models.CASCADE)
                    date = models.DatetimeField(auto_now_add=True)

            .. code-block:: python

                # serializers.py
                from rest_framework import serializers
                from .models import User, Comment

                class UserSerializer(serializers.ModelSerializer):
                    class Meta:
                        model = User
                        fields = ["id", "username", "email"]

                class CommentSerializer(serializers.ModelSerializer):
                    class Meta:
                        model = Comment
                        fields = ["id", "text", "user"]

            .. code-block:: python

                # consumers.py

                from djangochannelsrestframework.consumers import GenericAsyncAPIConsumer
                from djangochannelsrestframework.observer import model_observer
                from djangochannelsrestframework.decorators import action

                from .serializers import UserSerializer, CommentSerializer
                from .models import User, Comment

                class MyConsumer(GenericAsyncAPIConsumer):
                    queryset = User.objects.all()
                    serializer_class = UserSerializer
                    
                    @model_observer(Comments)
                    async def comment_activity(self, message, observer=None, **kwargs):
                        await self.send_json(message)

                    @comment_activity.serializer
                    def comment_activity(self, instance: Comment, action, **kwargs):
                        return CommentSerializer(instance).data

                    @action()
                    async def subscribe_to_comment_activity(self, **kwargs):
                        await self.comment_activity.subscribe()

            Now we will have a websocket client in javascript listening to the messages, after subscribing to the comment activity.
            This codeblock can be used it in the browser console.

            .. code-block:: javascript

                const ws = new WebSocket("ws://localhost:8000/ws/my-consumer/")
                const ws.onopen = function(){
                    ws.send(JSON.stringify({
                        action: "subscribe_to_comment_activity",
                        request_id: new Date().getTime(),
                    }))
                }
                const ws.onmessage = function(e){
                    console.log(e)
                }

            In the IPython shell we will create some comments for differnt users and in the browser console we will se the log.
            
            .. note::
                At this point we should have some users in our database, otherwise create them

            >>> from my_app.models import User, Comment
            >>> user_1 = User.objects.get(pk=1)
            >>> user_2 = User.objects.get(pk=2)
            >>> Comment.objects.create(text="user 1 creates a new comment", user=user_1)

            In the consol log we will se something like this:

            .. code-block:: json

                {
                    action: "subscribe_to_comment_activity",
                    errors: [],
                    response_status: 200,
                    request_id: 15606042,
                    data: {
                        id: 1,
                        text: "user 1 creates a new comment",
                        user: 1,
                    },
                }

            Now we will create a comment with the user 2.

            >>> Comment.objects.create(text="user 2 creates a second comment", user=user_2)

            In the consol log we will se something like this:

            .. code-block:: json

                {
                    action: "subscribe_to_comment_activity",
                    errors: [],
                    response_status: 200,
                    request_id: 15606042,
                    data: {
                        id: 2,
                        text: "user 2 creates a second comment",
                        user: 2,
                    },
                }

            As you can see in this example, we are subscribe to **ALL ACTIVITY** of the comment model.
        """
        self._serializer = func
        return self

    async def subscribe(self, consumer: AsyncAPIConsumer, *args, **kwargs):
        for group_name in self.group_names_for_consumer(
            *args, consumer=consumer, **kwargs
        ):
            await consumer.add_group(group_name)

    async def unsubscribe(self, consumer: AsyncAPIConsumer, *args, **kwargs):
        for group_name in self.group_names_for_consumer(
            *args, consumer=consumer, **kwargs
        ):
            await consumer.remove_group(group_name)

    def group_names_for_consumer(
        self, consumer: AsyncAPIConsumer, *args, **kwargs
    ) -> Generator[str, None, None]:
        if self._group_names_for_consumer:
            for group in self._group_names_for_consumer(
                self, *args, consumer=consumer, **kwargs
            ):
                yield self.clean_group_name(
                    "{}-{}".format(self._stable_observer_id, group)
                )
            return
        for group in self.group_names(*args, **kwargs):
            yield self.clean_group_name(group)

    def group_names_for_signal(self, *args, **kwargs) -> Generator[str, None, None]:
        if self._group_names_for_signal:
            for group in self._group_names_for_signal(self, *args, **kwargs):
                yield self.clean_group_name(
                    "{}-{}".format(self._stable_observer_id, group)
                )
            return
        for group in self.group_names(*args, **kwargs):
            yield self.clean_group_name(group)

    def group_names(self, *args, **kwargs):
        raise NotImplementedError()

    def groups_for_consumer(
        self,
        func: Callable[["BaseObserver", AsyncAPIConsumer], Generator[str, None, None]],
    ):
        self._group_names_for_consumer = func
        return self

    def groups_for_signal(self, func: Callable[..., Generator[str, None, None]]):
        self._group_names_for_signal = func
        return self

    def groups(self, func):
        self._group_names_for_consumer = func
        self._group_names_for_signal = func
        return self

    def clean_group_name(self, name):
        # Some chanel layers have a max group name length.
        return f"DCRF-{hashlib.sha256(name.encode()).hexdigest()}"
