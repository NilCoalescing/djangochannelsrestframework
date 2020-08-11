from functools import partial
from typing import Type

from django.db.models import Model

from djangochannelsrestframework.observer.observer import Observer
from djangochannelsrestframework.observer.model_observer import ModelObserver


def observer(signal, **kwargs):
    """
    **WARNING**
    When using this to decorate a method to avoid the method firing multiple
    times you should ensure that if there are multiple `@observer` wrapped
    methods within a single file that each method has a different name.
    """
    return partial(Observer, signal=signal, kwargs=kwargs)


def model_observer(model: Type[Model], **kwargs):
    """
    **WARNING**
    When using this to decorate a method to avoid the method firing multiple
    times you should ensure that if there are multiple `@model_observer`
    wrapped methods for the same model type within a single file that each
    method has a different name.
    """
    return partial(ModelObserver, model_cls=model, kwargs=kwargs)
