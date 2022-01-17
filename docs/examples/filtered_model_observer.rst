Filtered model observer
=======================

=========================================
Subscribing to a filtered list of models.
=========================================

Introduction
------------
In this first example, we will create a ``user`` model with a ``comment`` related model, 
create the serializers for each one. And create a ``consumer`` for the ``user`` model, with 
a model observer method for watching all changes of the current user.

Creating models.
----------------

.. include:: ./extras/models.rst

Creating the serializers.
-------------------------

.. include:: ./extras/serializers.rst

Creating the consumers.
-----------------------

Now in the ``consumers.py`` file, we will create or 
websocket consumer for the users, with a model 
observer method for the ``Comment`` 
model, filtered for the current user.

These are the important methods of the class.

* 
    A method, called ``comment_activity`` decorated with the ``model_observer`` decorator and 
    as argument we will add the ``Comment`` model.
*
    A ``subscribe_to_comment_activity`` ``action`` to subscribe the ``model_observer`` method.

*
    A method (it can be named the same as the ``model_observer`` method) 
    decorated with the ``@comment_activity.serializer``, this will return the
    serializer based on the instance.

.. warning::
    The user must be logged to subscribe this method, because we will access the ``self.scope["user"]``

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
        async def comment_activity(self, message: CommentSerializer, observer=None, **kwargs):
            await self.send_json(message.data)

        @comment_activity.serializer
        def comment_activity(self, instance: Comment, action, **kwargs) -> CommentSerializer:
            '''This will return the comment serializer'''
            return CommentSerializer(instance)

        @comment_activity.groups_for_signal
        def comment_activity(self, instance: Comment, **kwargs):
            # this block of code is called very often *DO NOT make DB QUERIES HERE*
            yield f'-user__{instance.user_id}'  #! the string **user** is the ``Comment's`` user field.

        @comment_activity.groups_for_consumer
        def comment_activity(self, school=None, classroom=None, **kwargs):
            # This is called when you subscribe/unsubscribe
            yield f'-user__{self.scope["user"].pk}'

        @action()
        async def subscribe_to_comment_activity(self, **kwargs):
            # We will check if the user is authenticated for subscribing.
            if "user" in self.scope and self.scope["user"].is_authenticated:
                await self.comment_activity.subscribe()

.. note::
    Without logging in we will have to access the ``user`` using the pk or any other unique field.
    Example:
        .. code-block:: python

            ...
            class MyConsumer(GenericAsyncAPIConsumer):
                ...
            
                @action()
                async def subscribe_to_comment_activity(self, user_pk, **kwargs):
                    # We will check if the user is authenticated for subscribing.
                    user = await database_sync_to_async(User.objects.get)(pk=user_pk)
                    await self.comment_activity.subscribe(user=user)


Manual testing the output.
--------------------------

Now we will have a websocket client in javascript listening to the messages, after subscribing to the comment activity.
This code block can be used in the browser console.

.. note::
    In production the ``ws:`` is ``wss:``, we can check it with the following code:
        .. code-block:: javascript
            
            const ws_schema = window.location.protocol === "http:" ? "ws:" : "wss:";

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

.. note::
    The subscribe method doesn't require being logged:
        .. code-block:: javascript
            
            const ws = new WebSocket("ws://localhost:8000/ws/my-consumer/")
            const ws.onopen = function(){
                ws.send(JSON.stringify({
                    action: "subscribe_to_comment_activity",
                    request_id: new Date().getTime(),
                    user_pk: 1, // This field is the argument in the 
                                // subscribe method, and the pk correspond to the user.
                }))
            }
            const ws.onmessage = function(e){
                console.log(e)
            }

In the IPython shell we will create some comments for different users and in the browser console we will see the log.

.. warning::
    At this point we should have some users in our database, otherwise create them

We will create a comment using the ``user_1`` and we will see the log in the browser console.

.. code-block:: python

    >>> from my_app.models import User, Comment
    >>> user_1 = User.objects.get(pk=1)
    >>> user_2 = User.objects.get(pk=2)
    >>> Comment.objects.create(text="user 1 creates a new comment", user=user_1)

In the console log we will se something like this:

.. code-block:: javascript

    {
        action: "subscribe_to_comment_activity",
        errors: [],
        response_status: 200,
        request_id: 15606042,
        data: {
            id: 1,
            text: "user 1 creates a new comment",
            user: 1
        }
    }

Now we will create a comment with the ``user 2``.

.. code-block:: python

    >>> Comment.objects.create(text="user 2 creates a second comment", user=user_2)

In the console log we will see **nothing**, because this comment was created by the ``user_2``.

Conclusions
-----------

In this example we subscribe to the filtered instances of the comment model.
