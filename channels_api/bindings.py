from channels.binding import websockets

from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.exceptions import APIException, NotFound

from .mixins import SerializerMixin, SubscribeModelMixin, CreateModelMixin, UpdateModelMixin, \
    RetrieveModelMixin, ListModelMixin, DeleteModelMixin


class ResourceBindingBase(SerializerMixin, websockets.WebsocketBinding):

    available_actions = ('create', 'retrieve', 'list', 'update', 'delete', 'subscribe')
    fields = []  # hack to pass cls.register() without ValueError
    queryset = None
    # mark as abstract
    model = None
    serializer_class = None
    lookup_field = 'pk'

    def deserialize(self, message):
        self.request_id = message.get('request_id', None)
        return super().deserialize(message)

    def group_names(self, instance, action):
        groups = [self._group_name(action)]
        if instance.id:
            groups.append(self._group_name(action, id=instance.id))
        return groups

    def _group_name(self, action, id=None):
        """Formatting helper for group names."""
        if id:
            return "{}-{}-{}".format(self.model_label, action, id)
        else:
            return "{}-{}".format(self.model_label, action)

    def has_permission(self, action, pk, data):
        return True

    def filter_queryset(self, queryset):
        return queryset

    def _format_errors(self, errors):
        if isinstance(errors, list):
            return errors
        elif isinstance(errors, str):
            return [errors]
        elif isinstance(errors, dict):
            return [errors]

    def get_object(self, pk):
        queryset = self.filter_queryset(self.get_queryset())
        return queryset.get(**{self.lookup_field: pk})

    def get_object_or_404(self, pk):
        try:
            return self.get_object(pk)
        except ObjectDoesNotExist:
            raise NotFound

    def get_queryset(self):
        assert self.queryset is not None, (
            "'%s' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
            % self.__class__.__name__
        )
        return self.queryset.all()

    def run_action(self, action, pk, data):
        try:
            if not self.has_permission(self.user, action, pk):
                self.reply(action, errors=['Permission Denied'], status=401)
            if not action in self.available_actions:
                self.reply(action, errors=['Invalid Action'], status=400)
            elif action in ('create', 'list'):
                data, status = getattr(self, action)(data)
            elif action in ('retrieve', 'delete'):
                data, status = getattr(self, action)(pk)
            elif action in ('update', 'subscribe'):
                data, status = getattr(self, action)(pk, data)
            self.reply(action, data=data, status=status, request_id=self.request_id)
        except APIException as ex:
            self.reply(action, errors=self._format_errors(ex.detail), status=ex.status_code, request_id=self.request_id)

    def reply(self, action, data=None, errors=[], status=200, request_id=None):
        """
        Helper method to send a encoded response to the message's reply_channel.
        """
        payload = {
            'errors': errors,
            'data': data,
            'action': action,
            'response_status': status,
            'request_id': request_id
        }
        return self.message.reply_channel.send(self.encode(self.stream, payload))

class ResourceBinding(CreateModelMixin, RetrieveModelMixin, ListModelMixin,
    UpdateModelMixin, DeleteModelMixin, SubscribeModelMixin, ResourceBindingBase):

    # mark as abstract
    model = None

class ReadOnlyResourceBinding(RetrieveModelMixin, ListModelMixin,
    ResourceBindingBase):

    # mark as abstract
    model = None
