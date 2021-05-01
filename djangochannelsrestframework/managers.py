from typing import Any, Iterable, List, Optional
from django.db.models import Manager
from djangochannelsrestframework.signals import post_bulk_create


class CustomManager(Manager):
    def bulk_create(self, objs: Iterable[Any], **kwargs) -> List[Any]:
        temp = super().bulk_create(objs, **kwargs)
        print("bulk create", temp, objs)
        for obj in temp:
            print("loop", obj)
            post_bulk_create.send(sender=obj.__class__, instance=obj, created=True)
        return temp