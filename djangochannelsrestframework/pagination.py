from collections import OrderedDict
from typing import Any, Dict, List, Optional, Union

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList

from djangochannelsrestframework.settings import api_settings


def _positive_int(integer_string, strict=False, cutoff=None):
    """
    Cast a string to a strictly positive integer.
    """
    ret = int(integer_string)
    if ret < 0 or (ret == 0 and strict):
        raise ValueError()
    if cutoff:
        return min(ret, cutoff)
    return ret


class WebsocketLimitOffsetPagination(LimitOffsetPagination):

    default_limit = api_settings.PAGE_SIZE
    count: int
    limit: int
    offset: int

    def get_paginated_response(
        self, data: Union[ReturnDict, ReturnList]
    ) -> OrderedDict:
        """Get the paginated response data

        Args:
            data: serializer data paginated.

        Return:
            Dictionary with the results and the count.
        """
        # TODO
        return OrderedDict(
            [
                ("count", self.count),
                ("results", data),
                ("limit", self.limit),
                ("offset", self.offset),
            ]
        )

    def paginate_queryset(
        self, queryset, scope: Dict[any, any], view=None, **kwargs: Dict[any, any]
    ) -> Optional[List[Optional[Any]]]:
        """Paginates a given queryset, based on the kwargs `limit` and `offset`.

        Args:
            queryset: database data.
            scope: context.
            view: ?
            kwargs: keyworded argument dictionary.

        Returns:
            List of instances of the model.
        """
        self.count = self.get_count(queryset)
        self.limit = self.get_limit(**kwargs)
        if self.limit is None:
            return None

        self.offset = self.get_offset(**kwargs)
        self.scope = scope
        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []
        return list(queryset[self.offset : self.offset + self.limit])

    def get_limit(self, **kwargs: Dict) -> int:
        """Gets the limit from the websocket message.

        Args:
            kwargs: keyworded argument dictionary.

        Returns:
            Limit results pagination.
        """

        limit_query_param = kwargs.get("limit", self.default_limit)
        if self.limit_query_param:
            try:
                return _positive_int(
                    limit_query_param, strict=True, cutoff=self.max_limit
                )
            except (KeyError, ValueError):
                pass

        return self.default_limit

    def get_offset(self, **kwargs: Dict) -> int:
        """Gets the offset from the websocket message

        Args:
            kwargs: keyworded argument dictionary.

        Returns:
            Offset value.
        """
        offset_query_param = kwargs.get("offset", 0)
        try:
            return _positive_int(
                offset_query_param,
            )
        except (KeyError, ValueError):
            return 0
