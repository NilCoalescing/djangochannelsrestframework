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
