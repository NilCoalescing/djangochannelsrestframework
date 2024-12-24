from contextlib import AsyncExitStack

import pytest
from django.contrib.auth.models import Group
from channels import DEFAULT_CHANNEL_LAYER
from channels.db import database_sync_to_async
from channels.layers import channel_layers
from django.db import transaction

from tests.communicator import connected_communicator
from django.contrib.auth import get_user_model
from rest_framework import serializers

from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer
from djangochannelsrestframework.observer.generics import ObserverModelInstanceMixin
from tests.models import TestModel


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "email",
            "groups",
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_observer_model_instance_mixin(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {
                "expiry": 100500,
            },
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    async with connected_communicator(TestConsumer()) as communicator:

        await communicator.send_json_to({"action": "retrieve", "pk": 100, "request_id": 1})

        response = await communicator.receive_json_from()

        assert response == {
            "action": "retrieve",
            "errors": ["Not found"],
            "response_status": 404,
            "request_id": 1,
            "data": None,
        }

        u1 = await database_sync_to_async(get_user_model().objects.create)(
            username="test1", email="42@example.com"
        )
        u2 = await database_sync_to_async(get_user_model().objects.create)(
            username="test2", email="45@example.com"
        )

        # lookup a pk that is not there
        await communicator.send_json_to(
            {"action": "retrieve", "pk": u1.id - 1, "request_id": 1}
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "retrieve",
            "errors": ["Not found"],
            "response_status": 404,
            "request_id": 1,
            "data": None,
        }

        # lookup up u1
        await communicator.send_json_to(
            {"action": "retrieve", "pk": u1.id, "request_id": 1}
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "retrieve",
            "errors": [],
            "response_status": 200,
            "request_id": 1,
            "data": {"email": "42@example.com", "id": u1.id, "username": "test1", "groups": []},
        }

        # lookup up u1
        await communicator.send_json_to(
            {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "subscribe_instance",
            "errors": [],
            "response_status": 201,
            "request_id": 4,
            "data": None,
        }

        u3 = await database_sync_to_async(get_user_model().objects.create)(
            username="test3", email="46@example.com"
        )

        # lookup up u1
        await communicator.send_json_to(
            {
                "action": "update_username",
                "pk": u1.id,
                "username": "thenewname",
                "request_id": 5,
            }
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update_username",
            "errors": [],
            "response_status": 200,
            "request_id": 5,
            "data": {"pk": u1.id},
        }

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {"email": "42@example.com", "id": u1.id, "username": "thenewname", "groups": []},
        }

        u1_pk = u1.pk

        await database_sync_to_async(u1.delete)()

        response = await communicator.receive_json_from()

        assert response == {
            "action": "delete",
            "errors": [],
            "response_status": 204,
            "request_id": 4,
            "data": {"pk": u1_pk},
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_two_observer_model_instance_mixins(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {
                "expiry": 100500,
            },
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestUserConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    class TestOtherConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = TestModel.objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, name=None, **kwargs):
            tm = await database_sync_to_async(self.get_object)(pk=pk)
            tm.name = name
            await database_sync_to_async(tm.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    async with AsyncExitStack() as stack:
        communicator1 = await stack.enter_async_context(connected_communicator(TestOtherConsumer()))
        communicator2 = await stack.enter_async_context(connected_communicator(TestUserConsumer()))

        u1 = await database_sync_to_async(get_user_model().objects.create)(
            username="test1", email="42@example.com"
        )
        t1 = await database_sync_to_async(TestModel.objects.create)(name="test2")

        await communicator1.send_json_to(
            {"action": "subscribe_instance", "pk": t1.id, "request_id": 4}
        )

        response = await communicator1.receive_json_from()

        assert response == {
            "action": "subscribe_instance",
            "errors": [],
            "response_status": 201,
            "request_id": 4,
            "data": None,
        }

        await communicator2.send_json_to(
            {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
        )

        response = await communicator2.receive_json_from()

        assert response == {
            "action": "subscribe_instance",
            "errors": [],
            "response_status": 201,
            "request_id": 4,
            "data": None,
        }

        # update the user

        u1.username = "no not a value"

        await database_sync_to_async(u1.save)()

        # user is updated
        assert await communicator2.receive_json_from()

        # test model is not
        assert await communicator1.receive_nothing()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_unsubscribe_observer_model_instance_mixin(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {
                "expiry": 100500,
            },
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumerUnsubscribe(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    async with connected_communicator(TestConsumerUnsubscribe()) as communicator:

        u1 = await database_sync_to_async(get_user_model().objects.create)(
            username="test1", email="42@example.com"
        )

        # lookup up u1
        await communicator.send_json_to(
            {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
        )

        response = await communicator.receive_json_from()
        assert await communicator.receive_nothing()

        assert response == {
            "action": "subscribe_instance",
            "errors": [],
            "response_status": 201,
            "request_id": 4,
            "data": None,
        }

        await communicator.send_json_to(
            {
                "action": "update_username",
                "pk": u1.id,
                "username": "thenewname",
                "request_id": 5,
            }
        )

        a = await communicator.receive_json_from()

        b = await communicator.receive_json_from()

        assert {
            "action": "update_username",
            "errors": [],
            "response_status": 200,
            "request_id": 5,
            "data": {"pk": u1.id},
        } in [a, b]

        assert {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {"email": "42@example.com", "id": u1.pk, "username": "thenewname", "groups": []},
        } in [a, b]

        # unsubscribe
        # lookup up u1

        await communicator.send_json_to(
            {"action": "unsubscribe_instance", "pk": u1.id, "request_id": 4}
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "unsubscribe_instance",
            "errors": [],
            "response_status": 204,
            "request_id": 4,
            "data": None,
        }
        assert await communicator.receive_nothing()

        await communicator.send_json_to(
            {
                "action": "update_username",
                "pk": u1.id,
                "username": "thenewname",
                "request_id": 5,
            }
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update_username",
            "errors": [],
            "response_status": 200,
            "request_id": 5,
            "data": {"pk": u1.id},
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_observer_model_instance_mixin_with_many_subs(settings):
    """
    This tests when there are 2 instances subscribed to on the same consumer.
    """

    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumerMultipleSubs(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    async with connected_communicator(TestConsumerMultipleSubs()) as communicator:

        u1 = await database_sync_to_async(get_user_model().objects.create)(
            username="test1", email="42@example.com"
        )

        u2 = await database_sync_to_async(get_user_model().objects.create)(
            username="test2", email="45@example.com"
        )

        # Subscribe to instance user 1
        await communicator.send_json_to(
            {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "subscribe_instance",
            "errors": [],
            "response_status": 201,
            "request_id": 4,
            "data": None,
        }

        # Subscribe to instance user 2
        await communicator.send_json_to(
            {"action": "subscribe_instance", "pk": u2.id, "request_id": 5}
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "subscribe_instance",
            "errors": [],
            "response_status": 201,
            "request_id": 5,
            "data": None,
        }

        # lookup up u1
        await communicator.send_json_to(
            {
                "action": "update_username",
                "pk": u1.id,
                "username": "new name",
                "request_id": 10,
            }
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update_username",
            "errors": [],
            "response_status": 200,
            "request_id": 10,
            "data": {"pk": u1.id},
        }

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {"email": "42@example.com", "id": u1.id, "username": "new name", "groups": []},
        }

        assert await communicator.receive_nothing()

        # Update U2
        await communicator.send_json_to(
            {
                "action": "update_username",
                "pk": u2.id,
                "username": "the new name 2",
                "request_id": 11,
            }
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update_username",
            "errors": [],
            "response_status": 200,
            "request_id": 11,
            "data": {"pk": u2.id},
        }

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 5,
            "data": {"email": "45@example.com", "id": u2.id, "username": "the new name 2", "groups": []},
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_m2m_observer(settings):
    """
    This tests
    """

    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumerMultipleSubs(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    # Test a normal connection
    async with connected_communicator(TestConsumerMultipleSubs()) as communicator:

        u1 = await database_sync_to_async(get_user_model().objects.create)(
            username="test1", email="42@example.com"
        )

        u2 = await database_sync_to_async(get_user_model().objects.create)(
            username="test2", email="45@example.com"
        )

        # Subscribe to instance user 1
        await communicator.send_json_to(
            {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "subscribe_instance",
            "errors": [],
            "response_status": 201,
            "request_id": 4,
            "data": None,
        }

        g1 = await database_sync_to_async(Group.objects.create)(name="group1")
        g2 = await database_sync_to_async(Group.objects.create)(name="group2")
        g3 = await database_sync_to_async(Group.objects.create)(name="group3")
        g4 = await database_sync_to_async(Group.objects.create)(name="group4")

        await database_sync_to_async(u1.groups.add)(g1, g2)

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {
                "email": "42@example.com",
                "id": u1.id,
                "username": "test1",
                "groups": [g1.id, g2.id]
            },
        }

        await database_sync_to_async(u2.groups.add)(g4)

        await communicator.receive_nothing()

        await database_sync_to_async(g1.user_set.add)(u2)

        await communicator.receive_nothing()

        await database_sync_to_async(g3.user_set.add)(u1, u2)

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {
                "email": "42@example.com",
                "id": u1.id,
                "username": "test1",
                "groups": [g1.id, g2.id, g3.id]
            },
        }

        await database_sync_to_async(g1.user_set.remove)(u1)

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {
                "email": "42@example.com",
                "id": u1.id,
                "username": "test1",
                "groups": [g2.id, g3.id]
            },
        }

        await database_sync_to_async(u1.groups.clear)()

        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {
                "email": "42@example.com",
                "id": u1.id,
                "username": "test1",
                "groups": []
            },
        }

        await database_sync_to_async(u2.groups.clear)()

        await communicator.receive_nothing()

        await database_sync_to_async(u1.groups.set)([g1, g4])

        response = await communicator.receive_json_from()
        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {
                "email": "42@example.com",
                "id": u1.id,
                "username": "test1",
                "groups": [g1.id, g4.id]
            },
        }

        await database_sync_to_async(u2.groups.set)([g1, g4])

        await communicator.receive_nothing()
        
        await database_sync_to_async(u1.groups.set)([g1, g2, g3, g4])
        
        response = await communicator.receive_json_from()
        
        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {
                "email": "42@example.com",
                "id": u1.id,
                "username": "test1",
                "groups": [g1.id, g2.id, g3.id, g4.id]
            },
        }
        
        await database_sync_to_async(g4.user_set.clear)()
        
        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {
                "email": "42@example.com",
                "id": u1.id,
                "username": "test1",
                "groups": [g1.id, g2.id, g3.id]
            },
        }

        await database_sync_to_async(g3.user_set.remove)(u1)
        
        response = await communicator.receive_json_from()

        assert response == {
            "action": "update",
            "errors": [],
            "response_status": 200,
            "request_id": 4,
            "data": {
                "email": "42@example.com",
                "id": u1.id,
                "username": "test1",
                "groups": [g1.id, g2.id]
            },
        }


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_current_groups_updated_on_commit(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    consumer = TestConsumer()

    async with connected_communicator(consumer) as communicator:

        u1 = await database_sync_to_async(get_user_model().objects.create)(
            username="test1", email="42@example.com"
        )

        def get_current_groups():
            return consumer.handle_instance_change.get_observer_state(u1).current_groups

        async def aget_current_groups():
            return await database_sync_to_async(get_current_groups)()

        await communicator.send_json_to(
            {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "subscribe_instance",
            "errors": [],
            "response_status": 201,
            "request_id": 4,
            "data": None,
        }

        current_groups = await aget_current_groups()

        # Check that current_groups is updated only on commit
        @database_sync_to_async
        def check_group_names_in_tx():
            with transaction.atomic():
                u1.delete()
                assert get_current_groups() == current_groups
            assert get_current_groups() != current_groups

        await check_group_names_in_tx()


@pytest.mark.django_db(transaction=False)
@pytest.mark.asyncio
async def test_multiple_changes_within_transaction(settings):
    settings.CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
            "TEST_CONFIG": {"expiry": 100500},
        },
    }

    layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)

    class TestConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):

        queryset = get_user_model().objects.all()
        serializer_class = UserSerializer

        async def accept(self, subprotocol=None):
            await super().accept()

        @action()
        async def update_username(self, pk=None, username=None, **kwargs):
            user = await database_sync_to_async(self.get_object)(pk=pk)
            user.username = username
            await database_sync_to_async(user.save)()
            return {"pk": pk}, 200

    assert not await database_sync_to_async(get_user_model().objects.all().exists)()

    async with connected_communicator(TestConsumer()) as communicator:
        u1 = await database_sync_to_async(get_user_model().objects.create)(
            username="test1", email="42@example.com"
        )

        try:
            await communicator.send_json_to(
                {"action": "subscribe_instance", "pk": u1.id, "request_id": 4}
            )

            response = await communicator.receive_json_from()

            assert response == {
                "action": "subscribe_instance",
                "errors": [],
                "response_status": 201,
                "request_id": 4,
                "data": None,
            }

            await communicator.receive_many_json_from()

            @database_sync_to_async
            def change_username_in_tx():
                with transaction.atomic():
                    u1.username = "thenewname"
                    u1.save()
                    u1.username = "thenewname2"
                    u1.save()
                    u1.username = "thenewname3"
                    u1.save()

            await change_username_in_tx()

            response = await communicator.receive_many_json_from()

            assert response == [{
                "action": "update",
                "errors": [],
                "response_status": 200,
                "request_id": 4,
                "data": {"email": "42@example.com", "id": u1.id, "username": "thenewname3"},
            }]
        finally:
            await database_sync_to_async(u1.delete)()
