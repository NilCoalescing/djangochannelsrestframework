from django.db import models
from djangochannelsrestframework.managers import CustomManager

class TestModel(models.Model):
    """Simple model to test with."""

    name = models.CharField(max_length=255)

    objects = CustomManager()
    

class TestRelatedModel(models.Model):
    """Simple related mdoel to test with."""

    name = models.CharField(max_length=255)
    fk = models.ForeignKey(TestModel, related_name="test_related", on_delete=models.CASCADE)