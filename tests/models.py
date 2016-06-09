from django.db import models


class TestModel(models.Model):
    """Simple model to test with."""

    name = models.CharField(max_length=255)
