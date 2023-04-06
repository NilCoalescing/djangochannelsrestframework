Introduction
============

------------------------------
Django Channels Rest Framework
------------------------------

Django Channels Rest Framework provides a DRF like interface for building channels-v3_ websocket consumers.


This project can be used alongside HyperMediaChannels_ and ChannelsMultiplexer_ 
to create a Hyper Media Style API over websockets. However Django Channels Rest Framework
is also a free standing framework with the goal of providing an API that is familiar to DRF users.

theY4Kman_ has developed a useful Javascript client library dcrf-client_ to use with DCRF.

------------
Installation
------------

.. code-block:: bash

    pip install djangochannelsrestframework

---------
Thanks to
---------


DCRF is based of a fork of `Channels Api <https://github.com/linuxlewis/channels-api>`_ and of course inspired by `Django Rest Framework <http://www.django-rest-framework.org/>`_.



.. _post: https://lostmoa.com/blog/DjangoChannelsRestFramework/
.. _GenericAPIView: https://www.django-rest-framework.org/api-guide/generic-views/
.. _channels-v3: https://channels.readthedocs.io/en/latest/
.. _dcrf-client: https://github.com/theY4Kman/dcrf-client
.. _theY4Kman: https://github.com/theY4Kman
.. _HyperMediaChannels: https://github.com/hishnash/hypermediachannels
.. _ChannelsMultiplexer: https://github.com/hishnash/channelsmultiplexer
