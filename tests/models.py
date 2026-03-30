from django.db import models


class TestModel(models.Model):
    """Simple model to test with."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    name = models.CharField(max_length=255)


class TestModelWithCustomPK(models.Model):
    """Simple model with custom primary key to test with."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    name = models.CharField(max_length=255, primary_key=True)
    description = models.CharField(max_length=255, null=True, blank=True)


class DeferredGroupDynamicTestModel(models.Model):
    """Model used to verify dynamic observers against deferred queryset fields."""

    __test__ = False

    name = models.CharField(max_length=255)


class DeferredGroupStaticTestModel(models.Model):
    """Model used to verify static observers against deferred queryset fields."""

    __test__ = False

    name = models.CharField(max_length=255)
