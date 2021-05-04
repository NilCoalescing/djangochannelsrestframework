import pytest
from django.db import transaction, connection, connections

from djangochannelsrestframework.decorators import action


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_async_action_works_with_atomic_request_on(settings):
    settings.DATABASES["default"]["ATOMIC_REQUESTS"] = True

    @action()
    async def simple_action():
        return True

    result = await simple_action()
    assert result


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_async_action_fails_when_atomic():

    with pytest.raises(ValueError):

        @action(atomic=True)
        async def simple_action():
            return True


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_sync_action_when_atomic():
    @action(atomic=True)
    def simple_action(self):
        return connections["default"].in_atomic_block, None

    result, _ = await simple_action(None)
    assert result


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_sync_action_when_not_atomic():
    @action(atomic=False)
    def simple_action(self):
        return connections["default"].in_atomic_block, None

    result, _ = await simple_action(None)
    assert not result


@pytest.mark.parametrize("atomic", [True, False])
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_sync_action_users_settings(settings, atomic):
    settings.DATABASES["default"]["ATOMIC_REQUESTS"] = atomic

    @action()
    def simple_action(self):
        return connections["default"].in_atomic_block, None

    result, _ = await simple_action(None)
    assert result == atomic


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_action_with_detail_true(settings):
    settings.DATABASES["default"]["ATOMIC_REQUESTS"] = True

    @action(detail=True)
    async def simple_action():
        return True

    assert simple_action.detail == True


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_action_with_detail_false(settings):
    settings.DATABASES["default"]["ATOMIC_REQUESTS"] = True

    @action(detail=False)
    async def simple_action():
        return True

    assert simple_action.detail == False
