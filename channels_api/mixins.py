

class CreateModelMixin(object):
    """Mixin class that handles the creation of an object using a DRF serializer."""

    def create(self, message, **kwargs):
        serializer = self.get_serializer(data=self.get_create_data())
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return serializer.data

    def perform_create(self, serializer):
        serializer.save()

    def get_create_data(self):
        """Override method to customize params parsing."""
        return self.get_content()


class RetrieveModelMixin(object):

    def retrieve(self, message, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return serializer.data


class ListModelMixin(object):

    def list(self, message, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return serializer.data


class UpdateModelMixin(object):

    def update(self, message, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=self.get_update_data())
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return serializer.data

    def perform_update(self, serializer):
        serializer.save()

    def get_update_data(self):
        return self.get_content()


class DeleteModelMixin(object):

    def delete(self, content, **kwargs):
        instance = self.get_object()
        self.perform_delete(instance)
        return dict()

    def perform_delete(self, instance):
        instance.delete()


class SerializerMixin(object):
    """Mixin class that handles the loading of the serializer class, context and object."""

    serializer_class = None

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
            % self.__class__.__name__
        )
        return self.serializer_class

    def get_serializer_context(self):
        return {
            'consumer': self,
            'message': self.message
        }
