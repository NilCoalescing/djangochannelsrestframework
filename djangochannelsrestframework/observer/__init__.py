from functools import partial
from typing import Type

from django.db.models import Model

from djangochannelsrestframework.observer.observer import Observer
from djangochannelsrestframework.observer.model_observer import ModelObserver


def observer(signal, **kwargs):
    return partial(Observer, signal=signal, kwargs=kwargs)


def model_observer(model: Type[Model], **kwargs):
    return partial(ModelObserver, model_cls=model, kwargs=kwargs)
