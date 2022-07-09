from typing import Dict
import asyncio

import pytest
from channels import DEFAULT_CHANNEL_LAYER
from channels.db import database_sync_to_async
from channels.layers import channel_layers
from channels.testing import WebsocketCommunicator
from rest_framework import serializers

from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer import model_observer
from tests.models import TestModelWithCustomPK


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_subscription_create_notification(settings):

    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {
                "expiry": 100500,
            },
        },
    }

    class TestSerializer(serializers.ModelSerializer):
        class Meta:
            model = TestModelWithCustomPK
            fields = ("name",)

    class TestConsumer(GenericAsyncAPIConsumer):

        queryset = TestModelWithCustomPK.objects.all()
        serializer_class = TestSerializer

        @model_observer(TestModelWithCustomPK)
        async def model_change(
            self, message: Dict, observer=None, subscribing_request_ids=[], **kwargs
        ):
            for request_id in subscribing_request_ids:
                await self.send_json(dict(request_id=request_id, **message))

        @model_change.serializer
        def model_change(
            self, instance: TestModelWithCustomPK, action, **kwargs
        ) -> Dict:
            return dict(action=action.value, data=TestSerializer(instance).data)

        @action()
        async def subscribe_to_all_changes(self, request_id, **kwargs):
            await self.model_change.subscribe(request_id=request_id)

    # connect
    communicator = WebsocketCommunicator(TestConsumer(), "/testws/")
    connected, _ = await communicator.connect()
    assert connected

    # subscribe
    subscription_id = 1
    await communicator.send_json_to(
        {"action": "subscribe_to_all_changes", "request_id": subscription_id}
    )

    # create an instance
    created_instance = await database_sync_to_async(
        TestModelWithCustomPK.objects.create
    )(name="some_unique_name")

    # check the response
    response = await communicator.receive_json_from()
    assert response == {
        "action": "create",
        "request_id": subscription_id,
        "data": TestSerializer(created_instance).data,
    }
