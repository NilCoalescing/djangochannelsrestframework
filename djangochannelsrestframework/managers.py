from typing import Any, Iterable, List, Optional, Sequence
from django.db.models import Manager
from djangochannelsrestframework.signals import post_bulk_create, pre_bulk_create, post_bulk_update, pre_bulk_update


class CustomManager(Manager):
    def bulk_create(self, objs: Iterable[Any], **kwargs) -> List[Any]:
        for obj in objs:
            pre_bulk_create.send(sender=obj.__class__, instance=obj, created=True, **kwargs)
        temp = super().bulk_create(objs, **kwargs)
        for obj in objs:
            post_bulk_create.send(sender=obj.__class__, instance=obj, created=True, **kwargs)
        return temp

    def bulk_update(self, objs: Iterable[Any], fields: Sequence[str], **kwargs) -> None:
        for obj in objs:
            pre_bulk_update.send(sender=obj.__class__, instance=obj, created=False, fields=fields, **kwargs)
        temp = super().bulk_update(objs, fields, **kwargs)
        for obj in objs:
            post_bulk_update.send(sender=obj.__class__, instance=obj, created=False, fields=fields, **kwargs)