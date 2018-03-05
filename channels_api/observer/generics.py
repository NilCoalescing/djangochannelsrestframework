from channels.db import database_sync_to_async

from rest_framework import status

from channels_api.decorators import action
from channels_api.observer import model_observer, ModelObserver


class ObserverModelMixin:

    @action()
    async def subscribe_instance(self, **kwargs):
        # subscribe!
        instance = await database_sync_to_async(self.get_object)(**kwargs)
        await self.handle_event.subscribe(instance=instance)
        return None, status.HTTP_201_CREATED

    @model_observer(None)  # todo metaclass should inject model!
    async def handle_event(self, message):
        pass

    @handle_event.groups
    def handle_event(self: ModelObserver, instance, *args, **kwargs):
        model_label = '{}.{}'.format(
            self.model_cls._meta.app_label.lower(),
            self.model_cls._meta.object_name.lower()
        ).lower().replace('_', '.')

        # one channel for all updates.
        yield '{}-model-{}-pk-{}'.format(
            self.func.__name__.replace('_', '.'),
            model_label,
            instance.pk
        )