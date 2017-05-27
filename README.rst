Channels API
------------

.. image:: https://travis-ci.org/linuxlewis/channels-api.svg?branch=master
    :target: https://travis-ci.org/linuxlewis/channels-api

Channels API exposes a RESTful Streaming API over WebSockets using
channels. It provides a ``ResourceBinding`` which is comparable to Django
Rest Framework's ``ModelViewSet``. It is based on DRF serializer
classes.

It requires Python 3, Channels >0.17.3, Django >1.8, and Django Rest Framework 3.0

Table of Contents
-----------------

-  `Getting Started <#getting-started>`__
-  `ResourceBinding <#resourcebinding>`__
-  `Subscriptions <#subscriptions>`__
-  `Custom Actions <#custom-actions>`__
-  `Permissions <#permissions>`__


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

.. code:: bash

  pip install channels_api

-  Add ``channels_api`` to ``INSTALLED_APPS``

.. code:: python


    INSTALLED_APPS = (
        'rest_framework',
        'channels',
        'channels_api'
    )

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

-  Add a ``WebsocketDemultiplexer`` to your ``channel_routing``

.. code:: python

    # proj/routing.py


    from channels.generic.websockets import WebsocketDemultiplexer
    from channels.routing import route_class

    from polls.bindings import QuestionBinding

    class APIDemultiplexer(WebsocketDemultiplexer):

        consumers = {
          'questions': QuestionBinding.consumer
        }

    channel_routing = [
        route_class(APIDemultiplexer)
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


Custom Actions
--------------

To add your own custom actions, use the ``detail_action`` or ``list_action``
decorators.


.. code:: python

    from channels_api.bindings import ResourceBinding
    from channels_api.decorators import detail_action, list_action

    from .models import Question
    from .serializers import QuestionSerializer

    class QuestionBinding(ResourceBinding):

        model = Question
        stream = "questions"
        serializer_class = QuestionSerializer
        queryset = Question.objects.all()

        @detail_action()
        def publish(self, pk, data=None, **kwargs):
            instance = self.get_object(pk)
            result = instance.publish()
            return result, 200

        @list_action()
        def report(self, data=None, **kwargs):
            report = self.get_queryset().build_report()
            return report, 200

Then pass the method name as "action" in your message

.. code:: javascript

  // run the publish() custom action on Question 1
  var msg = {
    stream: "questions",
    payload: {
      action: "publish",
      data: {
        pk: "1"
      }
    }
  }

  // run the report() custom action on all Questions
  var msg = {
    stream: "questions",
    payload: {
      action: "report"
    }
  }

Permissions
-----------

Channels API offers a simple permission class system inspired by rest_framework.
There are two provided permission classes: ``AllowAny`` and ``IsAuthenticated``.

To configure permissions globally use the setting ``DEFAULT_PERMISSION_CLASSES`` like so

.. code:: python

    # settings.py

    CHANNELS_API = {
        'DEFAULT_PERMISSION_CLASSES': ('channels_api.permissions.AllowAny',)

    }

You can also configure the permission classes on a ``ResourceBinding`` itself like so

.. code:: python

    from channels_api.permissions import IsAuthenticated

    class MyBinding(ResourceBinding):
        permission_classes = (IsAuthenticated,)


Lastly, to implement your own permission class, override the ``has_permission`` of ``BasePermission``.

.. code:: python

    from channels_api.permissions import BasePermission

    class MyPermission(BasePermission):

        def has_permission(self, user, action, pk):

            if action == "CREATE":
                return True
            return False
