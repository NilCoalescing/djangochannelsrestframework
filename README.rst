==============================
Django Channels Rest Framework
==============================

Django Channels Rest Framework provides a DRF like interface for building channels-v2_ websocket consumers.


This project can be used alongside HyperMediaChannels_ and ChannelsMultiplexer_ to create a Hyper Media Style api over websockets. However Django Channels Rest Framework is also a free standing framework with the goal of providing an api that is familiar to DRF users.

theY4Kman_ has developed a useful Javascript client library dcrf-client_ to use with DCRF.


.. image:: https://travis-ci.org/hishnash/djangochannelsrestframework.svg?branch=master
    :target: https://travis-ci.org/hishnash/djangochannelsrestframework

Thanks to
---------


DCRF is based of a fork of `Channels Api <https://github.com/linuxlewis/channels-api>`_ and of course inspired by `Django Rest Framework <http://www.django-rest-framework.org/>`_.


Install
-------

.. code-block:: bash
  
  pip install djangochannelsrestframework


A Generic Api Consumer
----------------------
In DCRF you can create a ``GenericAsyncAPIConsumer`` that works much like a GenericAPIView_ in DRF: For a more indeph look into Rest Like Websocket consumers read this blog post_.


.. code-block:: python

    from . import models
    from . import serializers
    from djangochannelsrestframework import permissions
    from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
    from djangochannelsrestframework.mixins import (
        ListModelMixin,
        PatchModelMixin,
        UpdateModelMixin,
        CreateModelMixin,
        DeleteModelMixin,
    )

    class LiveConsumer(ListModelMixin, GenericAsyncAPIConsumer):
        queryset = models.Test.objects.all()
        serializer_class = serializers.TestSerializer
        permission_classes = (permissions.IsAuthenticated,)


Because this class uses the ``ListModelMixin``, one has access to the ``list`` action.

One may use the same exact querysets and ``serializer_class`` utilized in their DRF Views, but must omit the DRF permissions. Permissions are to be imported from ``djangochannelsrestframework``, which provides the standard ``AllowAny`` and ``IsAuthenticated`` permissions.

To call an action from the client send a websocket message: ``{action: "list", "request_id": 42}``


There are a selection of mixins that expose the common CURD actions:

* ``ListModelMixin`` - ``list``
* ``PatchModelMixin`` - ``patch``
* ``CreateModelMixin`` - ``create``
* ``RetrieveModelMixin`` - ``retrieve``
* ``UpdateModelMixin`` - ``update``
* ``DeleteModelMixin`` - ``delete``


Observing a Model instance
--------------------------

Consumer that let you subscribe to changes on an instance:

.. code-block:: python

   class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
       queryset = get_user_model().objects.all()
       serializer_class = UserSerializer

this exposes the ``retrieve``, ``subscribe_instance`` and ``unsubscribe_instance`` actions.

To subscribe send:

.. code-block:: python

   {
       "action": "subscribe_instance",
       "pk": 42,  # the id of the instance you are subscribing to
       "request_id": 4  # this id will be used for all resultent updates.
   }


Actions will be sent down out from the server:

.. code-block:: python

  {
    "action": "update",
    "errors": [],
    "response_status": 200,
    "request_id": 4,
    "data": {'email': '42@example.com', 'id': 42, 'username': 'thenewname'},
  }

Adding Custom actions
---------------------


.. code-block:: python

   class UserConsumer(GenericAsyncAPIConsumer):
       queryset = get_user_model().objects.all()
       serializer_class = UserSerializer

       @action()
       async def send_email(self, pk=None, to=None, **kwargs):
           user = await database_sync_to_async(self.get_object)(pk=pk)
           # ... do some stuff
           # remember to wrap all db actions in `database_sync_to_async`
           return {}, 200  # return the contenct and the response code.

       @action()  # if the method is not async it is already wrapped in `database_sync_to_async`
       def publish(self, pk=None, **kwargs):
           user = self.get_object(pk=pk)
           # ...
           return {'pk': pk}, 200

Consumers that are not bound to Models
--------------------------------------

You can also create consumers that are not at all related to any models.

.. code-block:: python

  from djangochannelsrestframework.decorators import action
  from djangochannelsrestframework.consumers import AsyncAPIConsumer

  class MyConsumer(AsyncAPIConsumer):

      @action()
      async def an_async_action(self, some=None, **kwargs):
          # do something async
          return {'response with': 'some message'}, 200
      
      @action()
      def a_sync_action(self, pk=None, **kwargs):
          # do something sync
          return {'response with': 'some message'}, 200

Using your normal views over a websocket connection
---------------------------------------------------

.. code-block:: python
  
  from djangochannelsrestframework.consumers import view_as_consumer

  application = ProtocolTypeRouter({
      "websocket": AuthMiddlewareStack(
          URLRouter([
              url(r"^front(end)/$", view_as_consumer(YourDjangoView)),
          ])
      ),
   })



Subscribing to all instances of a model
---------------------------------------

One can subscribe to all instances of a model by utilizing the ``model_observer``.

.. code-block:: python

    from djangochannelsrestframework.observer import model_observer

    @model_observer(models.Test)
    async def model_activity(self, message, observer=None, **kwargs):
        # send activity to your frontend
        await self.send_json(message)

This method will send messages to the client on all CRUD operations made through the Django ORM.

Note: These notifications do not include bulk updates, such as ``models.Test.objects.filter(name="abc").update(name="newname")``


    **WARNING**
    When using this to decorate a method to avoid the method firing multiple
    times you should ensure that if there are multiple `@model_observer`
    wrapped methods for the same model type within a single file that each
    method has a different name.


Subscribing to a `model_observer`
=================================

You can do this in a few placed, a common example is in the ``websocket_connect`` method.

.. code-block:: python

    async def websocket_connect(self, message):

        # Super Save
        await super().websocket_connect(message)

        # Initialized operation
        await self.activities_change.subscribe()


This method utilizes the previously mentioned ``model_activity`` method to subscribe to all instances of the current Consumer's model. 

One can also subscribe by creating a custom action

Another way is override ``AsyncAPIConsumer.accept(self, **kwargs)``

.. code-block:: python

    class ModelConsumerObserver(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await super().accept(** kwargs)
            await self.model_change.subscribe()
        

        @model_observer(models.Test)
        async def model_change(self, message, action=None, **kwargs):
            await self.send_json(message)
        
        ''' If you want the data serializeded instead of pk '''
        @model_change.serializer
        def model_serialize(self, instance, action, **kwargs):
            return TestSerializer(instance).data

Subscribing to a filtered list of models
========================================

In most situations you want to filter the set of models that you subscribe to.

To do this we need to split the model updates into `groups` and then in the consumer subscribe to the groups that we want/have permission to see.


.. code-block:: python

  class MyConsumer(AsyncAPIConsumer):

    @model_observer(models.Classroom)
    async def classroom_change_handler(self, message, observer=None, **kwargs):
        # due to not being able to make DB QUERIES when selecting a group
        # maybe do an extra check here to be sure the user has permission
        # send activity to your frontend
        await self.send_json(message)

    @classroom_change_handler.groups_for_signal
    def classroom_change_handler(self, instance: models.Classroom, **kwargs):
        # this block of code is called very often *DO NOT make DB QUERIES HERE*
        yield f'-school__{instance.school_id}'
        yield f'-pk__{instance.pk}'

    @classroom_change_handler.groups_for_consumer
    def classroom_change_handler(self, school=None, classroom=None, **kwargs):
        # This is called when you subscribe/unsubscribe
        if school is not None:
            yield f'-school__{school.pk}'
        if classroom is not None:
            yield f'-pk__{classroom.pk}'

    @action()
    async def subscribe_to_classrooms_in_school(self, school_pk, **kwargs):
        # check user has permission to do this
        await self.classroom_change_handler.subscribe(school=school)

    @action()
    async def subscribe_to_classroom(self, classroom_pk, **kwargs):
        # check user has permission to do this
        await self.classroom_change_handler.subscribe(classroom=classroom)


.. _post: https://lostmoa.com/blog/DjangoChannelsRestFramework/
.. _GenericAPIView: https://www.django-rest-framework.org/api-guide/generic-views/
.. _channels-v2: https://channels.readthedocs.io/en/latest/
.. _dcrf-client: https://github.com/theY4Kman/dcrf-client
.. _theY4Kman: https://github.com/theY4Kman
.. _HyperMediaChannels: https://github.com/hishnash/hypermediachannels
.. _ChannelsMultiplexer: https://github.com/hishnash/channelsmultiplexer
