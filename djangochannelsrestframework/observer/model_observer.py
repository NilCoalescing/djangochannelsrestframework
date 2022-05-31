import warnings
from collections import defaultdict
from copy import deepcopy
from enum import Enum
from functools import partial
from typing import Type, Dict, Any, Set, Optional
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Model
from django.db.models.signals import post_delete, post_save, post_init
from rest_framework.serializers import Serializer

from djangochannelsrestframework.observer.base_observer import BaseObserver


class Action(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class UnsupportedWarning(Warning):
    """ """


class ModelObserverInstanceState:
    # this is set when the instance is created
    current_groups: Set[str] = set()


class ModelObserver(BaseObserver):
    def __init__(self, func, model_cls: Type[Model], partition: str = "*", **kwargs):
        super().__init__(func, partition=partition)
        self._serializer_class = (
            kwargs["kwargs"].get("serializer_class") if "kwargs" in kwargs else None
        )  # type: Optional[Serializer]
        self._serializer = None
        self._model_cls = None
        self.model_cls = model_cls  # type: Type[Model]
        self.id = uuid4()

    @property
    def model_cls(self) -> Type[Model]:
        return self._model_cls

    @model_cls.setter
    def model_cls(self, value: Type[Model]):
        was_none = self._model_cls is None
        self._model_cls = value

        if self._model_cls is not None and was_none:
            self._connect()

    def _connect(self):
        """
        Connect the signal listing.
        """

        # this is used to capture the current state for the model
        post_init.connect(
            self.post_init_receiver, sender=self.model_cls, dispatch_uid=id(self)
        )

        post_save.connect(
            self.post_save_receiver, sender=self.model_cls, dispatch_uid=id(self)
        )

        post_delete.connect(
            self.post_delete_receiver, sender=self.model_cls, dispatch_uid=id(self)
        )

    def post_init_receiver(self, instance: Model, **kwargs):

        if instance.pk is None:
            current_groups = set()
        else:
            current_groups = set(self.group_names_for_signal(instance=instance))

        self.get_observer_state(instance).current_groups = current_groups

    def get_observer_state(self, instance: Model) -> ModelObserverInstanceState:
        # use a thread local dict to be safe...
        if not hasattr(instance._state, "_thread_local_observers"):
            instance._state._thread_local_observers = defaultdict(
                ModelObserverInstanceState
            )

        return instance._state._thread_local_observers[self.id]

    def post_save_receiver(self, instance: Model, created: bool, **kwargs):
        """
        Handle the post save.
        """
        if created:
            self.database_event(instance, Action.CREATE)
        else:
            self.database_event(instance, Action.UPDATE)

    def post_delete_receiver(self, instance: Model, **kwargs):
        self.database_event(instance, Action.DELETE)

    def database_event(self, instance: Model, action: Action):

        connection = transaction.get_connection()

        if connection.in_atomic_block:
            if len(connection.savepoint_ids) > 0:
                warnings.warn(
                    "Model observation with save points is unsupported and will"
                    " result in unexpected beauvoir.",
                    UnsupportedWarning,
                )

        connection.on_commit(partial(self.post_change_receiver, instance, action))

    def post_change_receiver(self, instance: Model, action: Action, **kwargs):
        """
        Triggers the old_binding to possibly send to its group.
        """

        if action == Action.CREATE:
            old_group_names = set()
        else:
            old_group_names = self.get_observer_state(instance).current_groups

        if action == Action.DELETE:
            new_group_names = set()
        else:
            new_group_names = set(self.group_names_for_signal(instance=instance))

        self.get_observer_state(instance).current_groups = new_group_names

        # if post delete, new_group_names should be []

        # Django DDP had used the ordering of DELETE, UPDATE then CREATE for good reasons.
        self.send_messages(
            instance, old_group_names - new_group_names, Action.DELETE, **kwargs
        )
        # the object has been updated so that its groups are not the same.
        self.send_messages(
            instance, old_group_names & new_group_names, Action.UPDATE, **kwargs
        )

        #
        self.send_messages(
            instance, new_group_names - old_group_names, Action.CREATE, **kwargs
        )

    def send_messages(
        self, instance: Model, group_names: Set[str], action: Action, **kwargs
    ):
        if not group_names:
            return
        message = self.serialize(instance, action, **kwargs)
        channel_layer = get_channel_layer()

        for group_name in group_names:
            message_to_send = deepcopy(message)

            # Include the group name in the message being sent
            message_to_send["group"] = group_name

            async_to_sync(channel_layer.group_send)(group_name, message_to_send)

    def group_names(self, *args, **kwargs):
        # one channel for all updates.
        yield "{}-{}-model-{}".format(
            self._stable_observer_id,
            self.func.__name__.replace("_", "."),
            self.model_label,
        )

    def serialize(self, instance, action, **kwargs) -> Dict[str, Any]:
        message_body = {}
        if self._serializer:
            message_body = self._serializer(self, instance, action, **kwargs)
        elif self._serializer_class:
            message_body = self._serializer_class(instance).data
        else:
            message_body["pk"] = instance.pk

        message = dict(
            type=self.func.__name__.replace("_", "."),
            body=message_body,
            action=action.value,
        )

        return message

    @property
    def model_label(self):
        model_label = (
            "{}.{}".format(
                self.model_cls._meta.app_label.lower(),
                self.model_cls._meta.object_name.lower(),
            )
            .lower()
            .replace("_", ".")
        )
        return model_label
