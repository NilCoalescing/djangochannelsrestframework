import warnings
from collections import defaultdict
from copy import deepcopy
from enum import Enum
from functools import partial
from typing import Type, Dict, Any, Set, Optional, List
from uuid import uuid4
import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Model
from django.db.models.signals import post_delete, post_save, post_init, m2m_changed
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
    pending_messages: List[Dict] = []


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

        for field in self.model_cls._meta.many_to_many:
            m2m_changed.connect(
                self.m2m_changed_receiver,
                sender=field.remote_field.through,
                dispatch_uid=f"{id(self)}-{field.name}"
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

    def get_observer_state(
        self, instance: Model, *args, **kwargs
    ) -> ModelObserverInstanceState:
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

    def m2m_changed_receiver(self, action: str, instance: Model, reverse: bool, model: Type[Model], pk_set: Set[Any], **kwargs):
        """
        Handle many-to-many changes.
        """
        if action not in {"post_add",  "post_remove", "post_clear"}:
            return

        target_instances = []
        if not reverse:
            target_instances.append(instance)
        else:
            for pk in pk_set:
                target_instances.append(model.objects.get(pk=pk))

        for target_instance in target_instances:
            self.database_event(target_instance, Action.UPDATE)

    def post_delete_receiver(self, instance: Model, **kwargs):
        self.database_event(instance, Action.DELETE)

    def database_event(self, instance: Model, action: Action):
        """
        Handles database events and prepares messages for sending on commit.
        """

        self.get_observer_state(instance).pending_messages = list(
            self.prepare_messages(instance, action)
        )

        connection = transaction.get_connection()

        if connection.in_atomic_block:
            if len(connection.savepoint_ids) > 0:
                warnings.warn(
                    "Model observation with save points is unsupported and will"
                    " result in unexpected behavior.",
                    UnsupportedWarning,
                )

        connection.on_commit(partial(self.send_prepared_messages, instance))

    def prepare_messages(self, instance: Model, action: Action, **kwargs):
        """
        Prepares messages for sending based on the given action and instance.
        """
        if action == Action.CREATE:
            old_group_names = set()
        else:
            old_group_names = self.get_observer_state(instance).current_groups

        if action == Action.DELETE:
            new_group_names = set()
        else:
            new_group_names = set(self.group_names_for_signal(instance=instance))

        transaction.on_commit(
            partial(self._update_current_groups, instance, new_group_names)
        )

        yield from self.generate_messages(
            instance, old_group_names, new_group_names, action, **kwargs
        )

    def _update_current_groups(self, instance, new_group_names):
        self.get_observer_state(instance).current_groups = new_group_names

    def generate_messages(
        self,
        instance: Model,
        old_group_names: Set[str],
        new_group_names: Set[str],
        action: Action,
        **kwargs
    ):
        """
        Generates messages for the given group names and action.
        """
        delete_group_names = old_group_names - new_group_names
        if delete_group_names:
            message_body = self.serialize(instance, Action.DELETE, **kwargs)
            for group_name in delete_group_names:
                yield {**message_body, "group": group_name}

        update_group_names = old_group_names & new_group_names
        if update_group_names:
            message_body = self.serialize(instance, Action.UPDATE, **kwargs)
            for group_name in update_group_names:
                yield {**message_body, "group": group_name}

        create_group_names = new_group_names - old_group_names
        if create_group_names:
            message_body = self.serialize(instance, Action.CREATE, **kwargs)
            for group_name in create_group_names:
                yield {**message_body, "group": group_name}

    def send_prepared_messages(self, instance: Model):
        """
        Sends messages mapped to a specific instance after commit.
        """

        # Get pending messages
        messages = self.get_observer_state(instance).pending_messages

        # Ensure multiple updates within a single transaction do not create duplicate message sends
        self.get_observer_state(instance).pending_messages = []

        if not messages:
            return

        channel_layer = get_channel_layer()
        for message in messages:
            async_to_sync(channel_layer.group_send)(message["group"], deepcopy(message))

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
            try:
                # Try encoding instance.pk directly
                json.dumps(instance.pk)
                message_body["pk"] = instance.pk
            except TypeError:
                message_body["pk"] = str(instance.pk)

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
