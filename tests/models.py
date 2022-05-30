from django.db import models


class TestModel(models.Model):
    """Simple model to test with."""

    name = models.CharField(max_length=255)


class TestModelWithCustomPK(models.Model):
    """Simple model with custom primary key to test with."""

    name = models.CharField(max_length=255, primary_key=True)
