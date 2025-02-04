import asyncio
from contextlib import AsyncExitStack

import pytest
from asgiref.sync import async_to_sync
from channels import DEFAULT_CHANNEL_LAYER
from channels.db import database_sync_to_async
from channels.layers import channel_layers
from tests.communicator import connected_communicator
from django.contrib.auth import user_logged_in, get_user_model
from django.db import transaction
from django.utils.text import slugify

from djangochannelsrestframework.decorators import action
from djangochannelsrestframework.consumers import AsyncAPIConsumer
from djangochannelsrestframework.observer import observer, model_observer

from rest_framework import serializers


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_observer_wrapper(settings):
    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.handle_user_logged_in.subscribe()
            await super().accept()

        @observer(user_logged_in)
        async def handle_user_logged_in(self, message, observer=None, **kwargs):
            await self.send_json({"message": message, "observer": observer is not None})

    async with connected_communicator(TestConsumer()) as communicator:

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="test", email="test@example.com"
        )

        await database_sync_to_async(user_logged_in.send)(
            sender=user.__class__, request=None, user=user
        )

        response = await communicator.receive_json_from()

        assert {"message": {}, "observer": True} == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_wrapper(settings):
    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_observer_wrapper.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_observer_wrapper(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

    async with connected_communicator(TestConsumer()) as communicator:

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="test", email="test@example.com"
        )

        response = await communicator.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.observer.wrapper",
        } == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_wrapper_in_transaction(settings):
    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await TestConsumer.user_change_wrapper_in_transaction.subscribe(self)
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_wrapper_in_transaction(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

    async with connected_communicator(TestConsumer()) as communicator:

        @database_sync_to_async
        def create_user_and_wait():

            with transaction.atomic():
                user = get_user_model().objects.create(
                    username="test", email="test@example.com"
                )
                assert async_to_sync(communicator.receive_nothing)(timeout=0.1)
                user.username = "mike"
                user.save()
                assert async_to_sync(communicator.receive_nothing)(timeout=0.1)
                return user

        user = await create_user_and_wait()

        response = await communicator.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.wrapper.in.transaction",
        } == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_delete_wrapper(settings):
    class TestConsumerObserverDelete(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_observer_delete.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_observer_delete(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

    async with connected_communicator(TestConsumerObserverDelete()) as communicator:
        await communicator.receive_nothing()

        user = await database_sync_to_async(get_user_model())(
            username="test", email="test@example.com"
        )
        await database_sync_to_async(user.save)()

        response = await communicator.receive_json_from()
        await communicator.receive_nothing()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.observer.delete",
        } == response
        pk = user.pk

        await database_sync_to_async(user.delete)()

        response = await communicator.receive_json_from()

        await communicator.receive_nothing()

        assert {
            "action": "delete",
            "body": {"pk": pk},
            "type": "user.change.observer.delete",
        } == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_many_connections_wrapper(settings):
    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_many_connections_wrapper.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_many_connections_wrapper(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

    async with AsyncExitStack() as stack:
        communicator1 = await stack.enter_async_context(
            connected_communicator(TestConsumer())
        )
        communicator2 = await stack.enter_async_context(
            connected_communicator(TestConsumer())
        )
        user = await database_sync_to_async(get_user_model().objects.create)(
            username="test", email="test@example.com"
        )

        response = await communicator1.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.many.connections.wrapper",
        } == response

        await communicator1.disconnect()

        response = await communicator2.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.many.connections.wrapper",
        } == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_many_consumers_wrapper(settings):
    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_many_consumers_wrapper_1.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_many_consumers_wrapper_1(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

    class TestConsumer2(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_many_consumers_wrapper_2.subscribe()
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_many_consumers_wrapper_2(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

    async with AsyncExitStack() as stack:
        communicator1 = await stack.enter_async_context(
            connected_communicator(TestConsumer())
        )
        communicator2 = await stack.enter_async_context(
            connected_communicator(TestConsumer2())
        )

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="test", email="test@example.com"
        )

        response = await communicator1.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.many.consumers.wrapper.1",
        } == response

        await communicator1.disconnect()

        response = await communicator2.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.many.consumers.wrapper.2",
        } == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_custom_groups_wrapper(settings):
    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_custom_groups_wrapper.subscribe(username="test")
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_custom_groups_wrapper(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

        @user_change_custom_groups_wrapper.groups
        def user_change_custom_groups_wrapper(
            self, instance=None, username=None, **kwargs
        ):
            if username:
                yield "-instance-username-{}-1".format(slugify(username))
            else:
                yield "-instance-username-{}-1".format(instance.username)

    async with connected_communicator(TestConsumer()) as communicator:

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="test", email="test@example.com"
        )

        response = await communicator.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.custom.groups.wrapper",
        } == response

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test2", email="test@example.com"
    )

    # no event since this is only subscribed to 'test'
    with pytest.raises(asyncio.TimeoutError):
        await communicator.receive_json_from()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_with_class_serializer(settings):
    class UserSerializer(serializers.ModelSerializer):
        class Meta:
            model = get_user_model()
            fields = ["id", "username"]

    class TestConsumerObserverUsers(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.users_changes.subscribe()
            await super().accept()

        @model_observer(get_user_model(), serializer_class=UserSerializer)
        async def users_changes(self, message, action, **kwargs):
            await self.reply(data=message, action=action)

    async with connected_communicator(TestConsumerObserverUsers()) as communicator:

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="test", email="test@example.com"
        )

        response = await communicator.receive_json_from()

        assert {
            "action": "create",
            "response_status": 200,
            "request_id": None,
            "errors": [],
            "data": {
                "id": user.pk,
                "username": user.username,
            },
        } == response

        user.username = "test updated"
        await database_sync_to_async(user.save)()

        response = await communicator.receive_json_from()

        assert {
            "action": "update",
            "response_status": 200,
            "request_id": None,
            "errors": [],
            "data": {
                "id": user.pk,
                "username": user.username,
            },
        } == response

        pk = user.pk
        await database_sync_to_async(user.delete)()

        response = await communicator.receive_json_from()

        assert {
            "action": "delete",
            "response_status": 200,
            "request_id": None,
            "errors": [],
            "data": {
                "id": pk,
                "username": user.username,
            },
        } == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_custom_groups_wrapper_with_split_function_api(settings):
    class TestConsumerObserverCustomGroups(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_custom_groups.subscribe(username="test")
            await super().accept()

        @model_observer(get_user_model())
        async def user_change_custom_groups(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

        @user_change_custom_groups.groups_for_signal
        def user_change_custom_groups(self, instance=None, **kwargs):
            yield "-instance-username-{}-2".format(instance.username)

        @user_change_custom_groups.groups_for_consumer
        def user_change_custom_groups(self, username=None, **kwargs):
            yield "-instance-username-{}-2".format(slugify(username))

    async with connected_communicator(
        TestConsumerObserverCustomGroups()
    ) as communicator:

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="test", email="test@example.com"
        )

        response = await communicator.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.custom.groups",
        } == response

    user = await database_sync_to_async(get_user_model().objects.create)(
        username="test2", email="test@example.com"
    )

    # no event since this is only subscribed to 'test'
    with pytest.raises(asyncio.TimeoutError):
        await communicator.receive_json_from()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_model_observer_with_request_id(settings):
    class TestConsumerObserverCustomGroups(AsyncAPIConsumer):
        @action()
        async def subscribe(self, username, request_id, **kwargs):
            await self.user_change_custom_groups.subscribe(
                username=username, request_id=request_id
            )
            await self.send_json(
                dict(
                    request_id=request_id,
                    action="subscribed",
                )
            )

        @model_observer(get_user_model())
        async def user_change_custom_groups(
            self,
            message,
            action,
            message_type,
            observer=None,
            subscribing_request_ids=None,
            **kwargs
        ):
            await self.send_json(
                dict(
                    body=message,
                    action=action,
                    type=message_type,
                    subscribing_request_ids=subscribing_request_ids,
                )
            )

        @user_change_custom_groups.groups_for_signal
        def user_change_custom_groups(self, instance=None, **kwargs):
            yield "-instance-username-{}-3".format(instance.username)

        @user_change_custom_groups.groups_for_consumer
        def user_change_custom_groups(self, username=None, **kwargs):
            yield "-instance-username-{}-3".format(slugify(username))

    async with connected_communicator(
        TestConsumerObserverCustomGroups()
    ) as communicator:

        await communicator.send_json_to(
            {
                "action": "subscribe",
                "username": "thenewname",
                "request_id": 5,
            }
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "subscribed",
            "request_id": 5,
        }

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="thenewname", email="test@example.com"
        )

        response = await communicator.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.custom.groups",
            "subscribing_request_ids": [5],
        } == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_observer_unsubscribe_behavior_with_custom_groups(settings):
    class TestConsumerObserverCustomGroups(AsyncAPIConsumer):
        @action()
        async def subscribe(self, username, request_id, **kwargs):
            await self.user_change_custom_groups.subscribe(
                username=username, request_id=request_id
            )
            await self.send_json(
                dict(
                    request_id=request_id,
                    action="subscribed",
                )
            )

        @action()
        async def unsubscribe(self, username, request_id, **kwargs):
            await self.user_change_custom_groups.unsubscribe(
                username=username, request_id=request_id
            )
            await self.send_json(
                dict(
                    request_id=request_id,
                    action="unsubscribed",
                )
            )

        @model_observer(get_user_model())
        async def user_change_custom_groups(
            self,
            message,
            action,
            message_type,
            observer=None,
            subscribing_request_ids=None,
            **kwargs
        ):
            await self.send_json(
                dict(
                    body=message,
                    action=action,
                    type=message_type,
                    subscribing_request_ids=subscribing_request_ids,
                )
            )

        @user_change_custom_groups.groups_for_signal
        def user_change_custom_groups(self, instance=None, **kwargs):
            yield "-instance-username-{}-4".format(instance.username)

        @user_change_custom_groups.groups_for_consumer
        def user_change_custom_groups(self, username=None, **kwargs):
            yield "-instance-username-{}-4".format(slugify(username))

    async with connected_communicator(
        TestConsumerObserverCustomGroups()
    ) as communicator:

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="thenewname", email="test@example.com"
        )

        assert await communicator.receive_nothing(timeout=0.5)

        await database_sync_to_async(user.delete)()

        assert await communicator.receive_nothing(timeout=0.5)

        await communicator.send_json_to(
            {
                "action": "subscribe",
                "username": "thenewname",
                "request_id": 5,
            }
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "subscribed",
            "request_id": 5,
        }

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="thenewname", email="test@example.com"
        )

        response = await communicator.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.custom.groups",
            "subscribing_request_ids": [5],
        } == response

        await communicator.send_json_to(
            {
                "action": "unsubscribe",
                "username": "thenewname",
                "request_id": 5,
            }
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "unsubscribed",
            "request_id": 5,
        }

        await communicator.send_json_to(
            {
                "action": "subscribe",
                "username": "thenewname2",
                "request_id": 6,
            }
        )

        response = await communicator.receive_json_from()

        assert response == {
            "action": "subscribed",
            "request_id": 6,
        }

        await database_sync_to_async(user.delete)()

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="thenewname", email="test@example.com"
        )

        assert await communicator.receive_nothing()

        user = await database_sync_to_async(get_user_model().objects.create)(
            username="thenewname2", email="test2@example.com"
        )

        response = await communicator.receive_json_from()

        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.custom.groups",
            "subscribing_request_ids": [6],
        } == response
