import pytest
from django.contrib.auth import get_user_model
from djangochannelsrestframework.signals import post_bulk_create
from django.dispatch import receiver

from .models import TestModel, TestRelatedModel

@pytest.mark.django_db(transaction=True)
def test_bulk_signal():
    
    @receiver(post_bulk_create, sender=TestModel)
    def function_signal(sender, instance : TestModel, created : bool, **kwargs):
        print("function signal", sender, instance)
        if created:
            print("before refresh")
            instance.refresh_from_db()
            print("refreshed instance", instance)
            obj = TestRelatedModel(name=instance.name, pk=instance)
            obj.save()
            
    test_models = TestModel.objects.bulk_create([
        TestModel(name="test 1"),
        TestModel(name="test 2"),
    ])
    assert test_models

    test_related_models = list(TestRelatedModel.objects.all())
    assert test_related_models