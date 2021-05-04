from typing import Any, Iterable, List, Optional, Sequence
from django.db.models import Manager
from djangochannelsrestframework.extras import (
    post_bulk_create,
    pre_bulk_create,
    post_bulk_update,
    pre_bulk_update,
)
from django.utils.translation import gettext as _

class BulkManager(Manager):
    """Bulk manager for sending bulk signals."""

    def bulk_create(self, objs: Iterable[Any], **kwargs) -> List[Any]:
        """Bulk create overide

        Warning:
            This method **DOESN'T RETURN** the `AutoIncrement` fields, this means, that the ID is `None`
            in the instance.

        Notes:
            The ID is currently returned only in `PostgresSQL` or `MariaDB 10.5+`.
        """
        if not len(objs) > 0:
            raise ValueError(_(f"'objs' must be a not empty Iterable"))
        pre_bulk_create.send(
            sender=objs[0].__class__, instances=objs, created=True, **kwargs
        )
        items = super().bulk_create(objs, **kwargs)
        post_bulk_create.send(
            sender=objs[0].__class__, instances=objs, created=True, **kwargs
        )
        return items

    def bulk_update(self, objs: Iterable[Any], fields: Sequence[str], **kwargs) -> None:
        """Bulk create overide

        Warning:
            This method **DOESN'T RETURN** the `AutoIncrement` fields, this means, that the ID is `None`
            in the instance.

        Notes:
            The ID is currently returned only in `PostgresSQL` or `MariaDB 10.5+`.
        """
        if not len(objs) > 0:
            raise ValueError(_(f"'objs' must be a not empty Iterable"))
        pre_bulk_update.send(
            sender=objs[0].__class__,
            instances=objs,
            created=False,
            fields=fields,
            **kwargs
        )
        super().bulk_update(objs, fields, **kwargs)
        post_bulk_update.send(
            sender=objs[0].__class__,
            instances=objs,
            created=False,
            fields=fields,
            **kwargs
        )
