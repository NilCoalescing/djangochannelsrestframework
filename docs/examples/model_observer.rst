Model observer
==============

=========================================
Subscribing to all instances of a model.
=========================================

Introduction
------------
In this first example, we will create a ``user`` model with a ``comment`` related model, 
create the serializers for each one. And create a ``consumer`` for the ``user`` model, with 
a model observer method for **all comment instances**.

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
observer method for **all instances** of the ``Comment`` 
model.

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
        async def comment_activity(
            self,
            message: CommentSerializer,
            observer=None,
            subscribing_request_ids=[]
            **kwargs
        ):
            await self.send_json(message.data)

        @comment_activity.serializer
        def comment_activity(self, instance: Comment, action, **kwargs) -> CommentSerializer:
            '''This will return the comment serializer'''
            return CommentSerializer(instance)

        @action()
        async def subscribe_to_comment_activity(self, request_id, **kwargs):
            await self.comment_activity.subscribe(request_id=request_id)

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

In the IPython shell we will create some comments for different users and in the browser console we will see the log.

.. warning::
    At this point we should have some users in our database, otherwise create them

We will create a comment using the ``ùser_1`` and we will see the log in the browser console.

.. code-block:: python

    >>> from my_app.models import User, Comment
    >>> user_1 = User.objects.get(pk=1)
    >>> user_2 = User.objects.get(pk=2)
    >>> Comment.objects.create(text="user 1 creates a new comment", user=user_1)

In the console log we will see something like this:

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

In the console log we will see something like this:

.. code-block:: javascript

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

Conclusions
-----------

In this example we subscribed to **all instances** of the comment model, 
in the next section we will see how to filter them.
