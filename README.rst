Channels API
------------

Channels API exposes a REST-like Streaming API over WebSockets using
channels. It provides a ``ModelConsumer`` which is comparable to Django
Rest Framework's ``ModelViewSet``. It is based on DRF serializer
classes.

It requires Python 3, Django 1.8, and Django Rest Framework 3.0

Table of Contents
-----------------

-  `Getting Started <#getting-started>`__
-  `Custom Method <#custom-method>`__
-  `Response Format <#response-format>`__
-  `Roadmap <#roadmap>`__

How does it work?
-----------------

The API works by having the WebSocket client send a ``method``
parameter. This follows the format of ``resource.method``. So
``POST /user`` would have a message payload that looks like the
following:

.. code:: javascript

    {method: "user.create", email: "test@test.com", password: "1Password" }

Why?
----

You're already using Django Rest Framework and want to expose the same
logic over WebSockets. WebSockets has lower overhead and provides other
functionality then HTTP.

Getting Started
---------------

This tutorial assumes you're familiar with channels and have completed
the `Getting
Started <https://channels.readthedocs.io/en/latest/getting-started.html>`__

-  Add ``channels_api`` to requirements.txt

-  Add ``channels_api`` to ``INSTALLED_APPS``

.. code:: python


    INSTALLED_APPS = (
        'rest_framework',
        'channels',
        'channels_api'
    )

-  Add API consumer to route websockets to API channels

.. code:: python

    # proj/routing.py

    from channels.routing import include

    channel_routing = [
        include('channels_api.routing.channel_routing'),
    ]

-  Add your first model consumer

.. code:: python


    # polls/consumers.py

    from .models import Question
    from .serializers import QuestionSerializer

    class QuestionConsumer(ModelConsumer):

        model = Question
        serializer_class = QuestionSerializer
        queryset = Question.objects.all()

    # proj/routing.py

    from channels.routing import include, route_class

    from polls.consumers import QuestionConsumer

    channel_routing = [
        include('channels_api.routing.channel_routing'),
        route_class(QuestionConsumer, path='/')
    ]

That's it. You can now make REST WebSocket requests to the server.

.. code:: javascript

    var ws = new WebSocket("ws://" + window.location.host + "/")

    ws.onmessage = function(e){
        console.log(e.data)
    }
    ws.send(JSON.stringify({method: "question.create", question_text: "What is your favorite python package?"}))
    //"{"question_text":"What is your favorite python package?","id":1}"


-  Add the channels debugger page (Optional)

This page is helpful to debug API requests from the browser and see the
response. It is only designed to be used when ``DEBUG=TRUE``.

.. code:: python

    # proj/urls.py

    from django.conf.urls import include

        urlpatterns = [
            url(r'^channels-api/', include('channels_api.urls'))
        ]

ModelConsumer
-------------

By default the ModelConsumer implements the following REST methods:
``create``, ``retrieve``, ``update``, ``list``, ``delete``

They will be mapped to ``modelname.method`` respectively.

Custom Method
-------------

To add a custom method just define the method on the consumer class and
add the method name to the variable ``available_methods``

.. code:: python


    class UserConsumer(ModelConsumer):

        model = User
        serializer_class = UserSerializer
        queryset = User.objects.all()

        available_methods = ModelConsumer.available_methods + ('invite', )

        def invite(self, message, **kwargs):
            content = self.get_content()
            # email.send(content["email"])
            return content

This will be automatically mapped to the ``user.invite`` channel.

Response Format
---------------

To implement a custom format override the ``format_response`` method on
ModelConsumerBase

Roadmap
-------

-  0.2
    -  pagination for list
    -  formatter classes for response formatting
-  0.3
    -  permissions
    -  testproject
