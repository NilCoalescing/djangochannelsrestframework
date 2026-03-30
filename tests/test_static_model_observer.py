import pytest
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils.text import slugify

from djangochannelsrestframework.consumers import AsyncAPIConsumer
from djangochannelsrestframework.observer import (
    model_observer,
    static_model_observer,
)
from tests.communicator import connected_communicator
from tests.models import DeferredGroupDynamicTestModel, DeferredGroupStaticTestModel


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_static_model_observer_wrapper(settings):
    """Static observers should preserve the usual create/update/delete contract."""

    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_static_observer.subscribe()
            await super().accept()

        @static_model_observer(get_user_model())
        async def user_change_static_observer(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

    async with connected_communicator(TestConsumer()) as communicator:
        user = await database_sync_to_async(get_user_model().objects.create)(
            username="static-test", email="static-test@example.com"
        )

        response = await communicator.receive_json_from()
        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.static.observer",
        } == response

        user.username = "static-test-updated"
        await database_sync_to_async(user.save)()

        response = await communicator.receive_json_from()
        assert {
            "action": "update",
            "body": {"pk": user.pk},
            "type": "user.change.static.observer",
        } == response

        user_pk = user.pk
        await database_sync_to_async(user.delete)()

        response = await communicator.receive_json_from()
        assert {
            "action": "delete",
            "body": {"pk": user_pk},
            "type": "user.change.static.observer",
        } == response


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_static_model_observer_custom_groups_wrapper(settings):
    """Static observers should keep filtered group subscriptions working."""

    class TestConsumer(AsyncAPIConsumer):
        async def accept(self, **kwargs):
            await self.user_change_static_custom_groups.subscribe(username="test")
            await super().accept()

        @static_model_observer(get_user_model())
        async def user_change_static_custom_groups(
            self, message, action, message_type, observer=None, **kwargs
        ):
            await self.send_json(dict(body=message, action=action, type=message_type))

        @user_change_static_custom_groups.groups_for_signal
        def user_change_static_custom_groups(self, instance=None, **kwargs):
            yield "-instance-username-{}-static".format(instance.username)

        @user_change_static_custom_groups.groups_for_consumer
        def user_change_static_custom_groups(self, username=None, **kwargs):
            yield "-instance-username-{}-static".format(slugify(username))

    async with connected_communicator(TestConsumer()) as communicator:
        user = await database_sync_to_async(get_user_model().objects.create)(
            username="test", email="test@example.com"
        )

        response = await communicator.receive_json_from()
        assert {
            "action": "create",
            "body": {"pk": user.pk},
            "type": "user.change.static.custom.groups",
        } == response

        await database_sync_to_async(get_user_model().objects.create)(
            username="test2", email="test2@example.com"
        )

        assert await communicator.receive_nothing(timeout=0.1)


@pytest.mark.django_db(transaction=True)
def test_model_observer_deferred_group_resolution_triggers_extra_queries(settings):
    """Dynamic observers resolve groups during hydration and can force N+1 reads."""

    class TestConsumer(AsyncAPIConsumer):
        @model_observer(DeferredGroupDynamicTestModel)
        async def deferred_group_activity(
            self, message, action, message_type, observer=None, **kwargs
        ):
            return None

        @deferred_group_activity.groups_for_signal
        def deferred_group_activity(self, instance=None, **kwargs):
            yield f"-name-{instance.name}"

    DeferredGroupDynamicTestModel.objects.bulk_create(
        [
            DeferredGroupDynamicTestModel(name="one"),
            DeferredGroupDynamicTestModel(name="two"),
            DeferredGroupDynamicTestModel(name="three"),
        ]
    )

    with CaptureQueriesContext(connection) as queries:
        list(DeferredGroupDynamicTestModel.objects.only("id").order_by("id"))

    assert len(queries) == 4


@pytest.mark.django_db(transaction=True)
def test_static_model_observer_avoids_deferred_group_resolution_queries(settings):
    """Static observers should not add queries when hydrating deferred rows."""

    class TestConsumer(AsyncAPIConsumer):
        @static_model_observer(DeferredGroupStaticTestModel)
        async def deferred_group_activity(
            self, message, action, message_type, observer=None, **kwargs
        ):
            return None

        @deferred_group_activity.groups_for_signal
        def deferred_group_activity(self, instance=None, **kwargs):
            yield f"-name-{instance.name}"

    DeferredGroupStaticTestModel.objects.bulk_create(
        [
            DeferredGroupStaticTestModel(name="one"),
            DeferredGroupStaticTestModel(name="two"),
            DeferredGroupStaticTestModel(name="three"),
        ]
    )

    with CaptureQueriesContext(connection) as queries:
        list(DeferredGroupStaticTestModel.objects.only("id").order_by("id"))

    assert len(queries) == 1
