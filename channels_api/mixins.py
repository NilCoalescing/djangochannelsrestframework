from channels import Group
from django.core.paginator import Paginator
from rest_framework.exceptions import ValidationError

from .settings import api_settings

class CreateModelMixin(object):
    """Mixin class that handles the creation of an object using a DRF serializer."""

    def create(self, data, **kwargs):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return serializer.data, 201

    def perform_create(self, serializer):
        serializer.save()

class RetrieveModelMixin(object):

    def retrieve(self, pk, **kwargs):
        instance = self.get_object_or_404(pk)
        serializer = self.get_serializer(instance)
        return serializer.data, 200


class ListModelMixin(object):

    def list(self, data, **kwargs):
        if not data:
            data = {}
        queryset = self.filter_queryset(self.get_queryset())
        paginator = Paginator(queryset, api_settings.DEFAULT_PAGE_SIZE)
        data = paginator.page(data.get('page', 1))
        serializer = self.get_serializer(data, many=True)
        return serializer.data, 200


class UpdateModelMixin(object):

    def update(self, pk, data, **kwargs):
        instance = self.get_object_or_404(pk)
        serializer = self.get_serializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return serializer.data, 200

    def perform_update(self, serializer):
        serializer.save()


class DeleteModelMixin(object):

    def delete(self, pk, **kwargs):
        instance = self.get_object_or_404(pk)
        self.perform_delete(instance)
        return dict(), 200

    def perform_delete(self, instance):
        instance.delete()

class SubscribeModelMixin(object):

    def subscribe(self, pk, data, **kwargs):
        if 'action' not in data:
            raise ValidationError('action required')
        group_name = self._group_name(data['action'], id=pk)
        Group(group_name).add(self.message.reply_channel)
        return {}, 200


class SerializerMixin(object):
    """Mixin class that handles the loading of the serializer class, context and object."""

    serializer_class = None

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
            % self.__class__.__name__
        )
        return self.serializer_class

    def get_serializer_context(self):
        return {
        }

    def serialize_data(self, instance):
        return self.get_serializer(instance).data
