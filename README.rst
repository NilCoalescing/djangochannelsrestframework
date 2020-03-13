==============================
Django Channels Rest Framework
==============================

Django Channels Rest Framework provides a DRF like interface for building channels-v2 websocket consumers.


This project can be used alongside HyperMediaChannels_ and ChannelsMultiplexer_ to create a Hyper Media Style api over websockets. However Django Channels Rest Framework is also a free standing framwork with the goal of providing an api that is familiar to DRF users. 

.. _HyperMediaChannels: https://github.com/hishnash/hypermediachannels
.. _ChannelsMultiplexer: https://github.com/hishnash/channelsmultiplexer

.. image:: https://travis-ci.org/hishnash/djangochannelsrestframework.svg?branch=master
    :target: https://travis-ci.org/hishnash/djangochannelsrestframework

Thanks to
---------


DCRF is based of a fork of `Channels Api <https://github.com/linuxlewis/channels-api>`_ and of course inspired by `Django Rest Framework <http://www.django-rest-framework.org/>`_.


Install
-------

.. code-block:: bash
  
  pip install djangochannelsrestframework


How to Use
==========



Observing a Model instance
--------------------------

Consumer that accepts subscribtions to an instance.

.. code-block:: python

   class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
       queryset = get_user_model().objects.all()
       serializer_class = UserSerializer

this exposes the `retrieve` and `subscribe_instance` actions to that instance.

to subscribe send:


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

You can also use any of:

*  ``CreateModelMixin``
*  ``ListModelMixin``
*  ``RetrieveModelMixin``
*  ``UpdateModelMixin``
*  ``PatchModelMixin``
*  ``DeleteModelMixin``

just as you would in DRF.

.. code-block:: python

  from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
  from djangochannelsrestframework.mixins import (
      RetrieveModelMixin,
      UpdateModelMixin
  )

  class UserConsumer(RetrieveModelMixin, UpdateModelMixin, GenericAsyncAPIConsumer):
      queryset = get_user_model().objects.all()
      serializer_class = UserSerializer


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


Creating fully-functional custom Consumers
------------------------------------------

This package offers Django Rest Framework capabilities via mixins. To utilize these mixins, one must inherit from the GenericAsyncAPIConsumer. One may use the same exact querysets and serializer_classes utilized in their DRF Views. However, one must import djangochannelsrestframework's permissions, which provides the standard AllowAny and IsAuthenticated permissions.

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

    extracted_data, extracted_status = await self.list()

This class utilizes the ListModelMixin to return all instances of the model to `extracted_data`, and the status of the extraction to `extracted_status`.


Subscribing to all instances of a model
---------------------------------------

One can subscribe to all instances of a model by utilizing the model_observer.

from djangochannelsrestframework.observer import model_observer

    @model_observer(models.Test)
    async def model_activity(self, message, observer=None, **kwargs):
        # send activity to your frontend
        await self.send_json(message)

This function will send messages to the client on all CRUD operations made via Django Rest Framework.


Creating consumer actions
-------------------------

To create consumer operations, one must choose between using the traditional receive/receive_json functions utilized in typical consumers or djangochannelsrestframework actions. Utilizing receive/receive_json will prevent the usage of all actions. Actions are created by adding the action <decorator> to a function.

from djangochannelsrestframework.decorators import action

    @action()
    async def subscribe_to_model(self, pk=None, to=None, **kwargs):
        await LiveConsumer.model_activity.subscribe(self)

This action makes use of the model_activity function in the LiveConsumer class, referred to above, subscribing to all CRUD operations of the model specified in the @model_observer.


Initiating operations on consumer connects
------------------------------------------

One may initiate operations on consumer connects by overriding the `websocket_connect` function.

    async def websocket_connect(self, message):
        try:
            await self.accept()
            await type(self).model_activity.subscribe(self)

        except Exception as e:
            await self.close()

This function utilizes the previosly mentioned model_activity function to subscribe to all instances of the current Consumer's model. Notice the use of type(self), rather than `LiveConsumer`. This is a more dynamic approach, most likely used in a custom Consumer mixin, allowing one to subscribe to the current consumer rather than a specific one.

