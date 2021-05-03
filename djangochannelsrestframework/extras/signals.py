from django.db.models.signals import ModelSignal


post_bulk_create = ModelSignal()
pre_bulk_create = ModelSignal()
post_bulk_update = ModelSignal()
pre_bulk_update = ModelSignal()
