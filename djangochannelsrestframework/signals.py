from django.db.models.signals import ModelSignal
from django.dispatch import Signal

post_bulk_create = Signal(providing_args=["sender", "instance", "created"])