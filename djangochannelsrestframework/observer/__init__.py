from functools import partial
from typing import Type, Callable

from django.db.models import Model
from django.dispatch import Signal

from djangochannelsrestframework.observer.observer import Observer
from djangochannelsrestframework.observer.model_observer import ModelObserver


def observer(signal: Signal, **kwargs):
    """
    .. note::
        Should be used as a method decorator eg: `@observer(user_logged_in)`

    The wrapped method will be called once for each consumer that has subscribed.

    .. code-block:: python

       class AdminPortalLoginConsumer(AsyncAPIConsumer):
            async def accept(self, **kwargs):
                await self.handle_user_logged_in.subscribe()
                await super().accept()

            @observer(user_logged_in)
            async def handle_user_logged_in(self, message, observer=None, **kwargs):
                await self.send_json(message)

    If the signal you are using supports filtering with `args` or `kwargs` these can be passed
    to the `@observer(signal, args..)`.

    """
    return partial(Observer, signal=signal, kwargs=kwargs)


def model_observer(model: Type[Model], **kwargs):
    """
    .. note::
        Should be used as a method decorator eg: `@model_observer(BlogPost)`

    The resulted wrapped method body becomes the handler that is called on each subscribed consumer.
    The method itself is replaced with an instance of :class:`~djangochannelsrestframework.observer.model_observer.ModelObserver`

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

            @model_observer(Comment)
            async def comment_activity(self, message, observer=None, subscribing_request_ids=[], **kwargs):
                for request_id in subscribing_request_ids:
                    await self.send_json({"message": message, "request_id": request_id})

            @comment_activity.serializer
            def comment_activity(self, instance: Comment, action, **kwargs):
                return CommentSerializer(instance).data

            @action()
            async def subscribe_to_comment_activity(self, request_id, **kwargs):
                await self.comment_activity.subscribe(request_id=request_id)


    If you only need to use a regular Django Rest Framework Serializer class then there is a shorthand:

    .. code-block:: python

        class MyConsumer(GenericAsyncAPIConsumer):
            queryset = User.objects.all()
            serializer_class = UserSerializer

            @model_observer(Comment, serializer_class=CommentSerializer)
            async def comment_activity(self, message, action, subscribing_request_ids=[], **kwargs):
                for request_id in subscribing_request_ids:
                    await self.reply(data=message, action=action, request_id=request_id)

            @action()
            async def subscribe_to_comment_activity(self, request_id, **kwargs):
                await self.comment_activity.subscribe(request_id=request_id)

    You can also use ``@model_observer`` to subscribe to a collection of models by configuring the group names used.

    .. code-block:: python

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


    Here the ``groups_for_signal`` method is called whenever a comment is updated/created/deleted to figure out which
    groups to send a message to.

    The ```groups_for_consumer``` method is used when subscribing to determine the groups to subscribe to.
    """
    return partial(ModelObserver, model_cls=model, kwargs=kwargs)
