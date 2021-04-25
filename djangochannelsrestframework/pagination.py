from collections import OrderedDict
from djangochannelsrestframework.settings import api_settings
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination


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

    def get_paginated_response(self, data):
        # TODO
        return OrderedDict(
            [
                ("results", data),
            ]
        )

    def paginate_queryset(self, queryset, scope, view=None, **kwargs):
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

    def get_limit(self, **kwargs):
        limit_query_param = kwargs.get("limit", self.default_limit)
        if self.limit_query_param:
            try:
                return _positive_int(
                    limit_query_param, strict=True, cutoff=self.max_limit
                )
            except (KeyError, ValueError):
                pass

        return self.default_limit

    def get_offset(self, **kwargs):
        offset_query_param = kwargs.get("offset", 0)
        try:
            return _positive_int(
                offset_query_param,
            )
        except (KeyError, ValueError):
            return 0
