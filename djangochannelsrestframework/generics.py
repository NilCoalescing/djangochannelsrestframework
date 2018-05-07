from typing import Dict, Type, Optional

from django.db.models import QuerySet, Model
from rest_framework.generics import get_object_or_404
from rest_framework.serializers import Serializer

from djangochannelsrestframework.consumers import AsyncAPIConsumer


class GenericAsyncAPIConsumer(AsyncAPIConsumer):
    """
    Base class for all other generic views.
    """

    # You'll need to either set these attributes,
    # or override `get_queryset()`/`get_serializer_class()`.
    # If you are overriding a view method, it is important that you call
    # `get_queryset()` instead of accessing the `queryset` property directly,
    # as `queryset` will get evaluated only once, and those results are cached
    # for all subsequent requests.

    queryset = None  # type: QuerySet
    serializer_class = None  # type: Type[Serializer]

    # If you want to use object lookups other than pk, set 'lookup_field'.
    # For more complex lookup requirements override `get_object()`.
    lookup_field = 'pk'  # type: str
    lookup_url_kwarg = None  # type: Optional[str]

    # TODO filter_backends

    # TODO pagination_class

    def get_queryset(self, **kwargs) -> QuerySet:
        """
        Get the list of items for this view.
        This must be an iterable, and may be a queryset.
        Defaults to using `self.queryset`.

        This method should always be used rather than accessing `self.queryset`
        directly, as `self.queryset` gets evaluated only once, and those results
        are cached for all subsequent requests.

        You may want to override this if you need to provide different
        querysets depending on the incoming request.

        (Eg. return a list of items that is specific to the user)
        """
        assert self.queryset is not None, (
            "'%s' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
            % self.__class__.__name__
        )

        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            queryset = queryset.all()
        return queryset

    def get_object(self, **kwargs) ->Model:
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(
            queryset=self.get_queryset(**kwargs),
            **kwargs
        )

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in kwargs, (
                'Expected view %s to be called with a URL keyword argument '
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                'attribute on the view correctly.' %
                (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: kwargs[lookup_url_kwarg]}

        obj = get_object_or_404(queryset, **filter_kwargs)
        # TODO check_object_permissions

        return obj

    def get_serializer(
            self,
            action_kwargs: Dict=None,
            *args, **kwargs) -> Serializer:
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class(
            **action_kwargs
        )

        kwargs['context'] = self.get_serializer_context(
            **action_kwargs
        )

        return serializer_class(*args, **kwargs)

    def get_serializer_class(self, **kwargs) -> Type[Serializer]:
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.

        You may want to override this if you need to provide different
        serializations depending on the incoming request.

        (Eg. admins get full serialization, others get basic serialization)
        """
        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
            % self.__class__.__name__
        )

        return self.serializer_class

    def get_serializer_context(self, **kwargs):
        """
        Extra context provided to the serializer class.
        """
        return {
            'scope': self.scope,
            'consumer': self
        }

    def filter_queryset(self, queryset: QuerySet, **kwargs):
        """
        Given a queryset, filter it with whichever filter backend is in use.

        You are unlikely to want to override this method, although you may need
        to call it either from a list view, or from a custom `get_object`
        method if you want to apply the configured filtering backend to the
        default queryset.
        """
        # TODO filter_backends

        return queryset
