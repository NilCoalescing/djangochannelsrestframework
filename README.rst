Channels API
------------

.. image:: https://travis-ci.org/linuxlewis/channels-api.svg?branch=master
    :target: https://travis-ci.org/linuxlewis/channels-api

Channels API exposes a RESTful Streaming API over WebSockets using
channels. It provides a ``ResourceBinding`` which is comparable to Django
Rest Framework's ``ModelViewSet``. It is based on DRF serializer
classes.

It requires Python 3, Django 1.8, and Django Rest Framework 3.0

Table of Contents
-----------------

-  `Getting Started <#getting-started>`__
-  `ResourceBinding <#resource-binding>`__
-  `Subscriptions <#subscriptions>`__
-  `Errors <#errors>`__
-  `Roadmap <#roadmap>`__


How does it work?
-----------------

The API builds on top of channels' ``WebsocketBinding`` class. It works by having
the client send a ``stream`` and ``payload`` parameters. This allows
us to route messages to different streams (or resources) for a particular
action. So ``POST /user`` would have a message that looks like the following

.. code:: javascript

    var msg = {
      stream: "users",
      payload: {
        action: "create",
        data: {
          email: "test@example.com",
          password: "password",
        }
      }
    }

    ws.send(JSON.stringify(msg))

Why?
----

You're already using Django Rest Framework and want to expose similar
logic over WebSockets.

WebSockets can publish updates to clients without a request. This is
helpful when a resource can be edited by multiple users across many platforms.

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

-  Add a ``WebsocketDemultiplexer`` to your ``channel_routing``

.. code:: python

    # proj/routing.py


    from channels.generic.websockets import WebsocketDemultiplexer
    from channels.routing import route_class

    class APIDemultiplexer(WebsocketDemultiplexer):

        mapping = {
          'questions': 'questions_channel'
        }

    channel_routing = [
        route_class(APIDemultiplexer)
    ]

-  Add your first resource binding

.. code:: python


    # polls/bindings.py

    from channels_api.bindings import ResourceBinding

    from .models import Question
    from .serializers import QuestionSerializer

    class QuestionBinding(ResourceBinding):

        model = Question
        stream = "questions"
        serializer_class = QuestionSerializer
        queryset = Question.objects.all()


    # proj/routing.py

    from channels.routing import route_class, route

    from polls.bindings import QuestionBinding

    channel_routing = [
      route_class(APIDemultiplexer),
      route("question_channel", QuestionBinding.consumer)
    ]

That's it. You can now make REST WebSocket requests to the server.

.. code:: javascript

    var ws = new WebSocket("ws://" + window.location.host + "/")

    ws.onmessage = function(e){
        console.log(e.data)
    }

    var msg = {
      stream: "questions",
      payload: {
        action: "create",
        data: {
          question_text: "What is your favorite python package?"
        },
        request_id: "some-guid"
      }
    }
    ws.send(JSON.stringify(msg))
    // response
    {
      stream: "questions",
      payload: {
        action: "create",
        data: {
          id: "1",
          question_text: "What is your favorite python package"
        }
        errors: [],
        response_status: 200
        request_id: "some-guid"
      }
    }

-  Add the channels debugger page (Optional)

This page is helpful to debug API requests from the browser and see the
response. It is only designed to be used when ``DEBUG=TRUE``.

.. code:: python

    # proj/urls.py

    from django.conf.urls import include

        urlpatterns = [
            url(r'^channels-api/', include('channels_api.urls'))
        ]

ResourceBinding
---------------

By default the ``ResourceBinding`` implements the following REST methods:

- ``create``
- ``retrieve``
- ``update``
- ``list``
- ``delete``
- ``subscribe``

See the test suite for usage examples for each method.


List Pagination
---------------

Pagination is handled by `django.core.paginator.Paginator`

You can configure the ``DEFAULT_PAGE_SIZE`` by overriding the settings.


.. code:: python

  # settings.py

  CHANNELS_API = {
    'DEFAULT_PAGE_SIZE': 25
  }


Subscriptions
-------------

Subscriptions are a way to programmatically receive updates
from the server whenever a resource is created, updated, or deleted

By default channels-api has implemented the following subscriptions

- create a Resource
- update any Resource
- update this Resource
- delete any Resource
- delete this Resource

To subscribe to a particular event just use the subscribe action
with the parameters to filter

.. code:: javascript

  // get an event when any question is updated

  var msg = {
    stream: "questions",
    payload: {
      action: "subscribe",
      data: {
        action: "update"
      }
    }
  }

  // get an event when question(1) is updated
  var msg = {
    stream: "questions",
    payload: {
      action: "subscribe"
      data: {
        action: "update",
        pk: "1"
      }
    }
  }

Roadmap
-------

-  0.3
    -  Permissions
    -  Custom Methods
    -  Test Project
