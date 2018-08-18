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

