import pytest
from django.contrib.auth import get_user_model
from djangochannelsrestframework.signals import post_bulk_create, pre_bulk_create, post_bulk_update, pre_bulk_update
from django.dispatch import receiver

from .models import TestModel, TestRelatedModel

@pytest.mark.django_db(transaction=True)
def test_post_bulk_create_signal():

    data = []
    
    @receiver(post_bulk_create, sender=TestModel)
    def function_signal(sender, instance : TestModel, created : bool, **kwargs):
        if created:
            data.append(instance)
            
    test_models = TestModel.objects.bulk_create([
        TestModel(name="test 1"),
        TestModel(name="test 2"),
    ])
    assert test_models
    assert test_models[0] == data[0]
    assert test_models[1] == data[1]

@pytest.mark.django_db(transaction=True)
def test_pre_bulk_create_signal():

    data = []
    
    @receiver(pre_bulk_create, sender=TestModel)
    def function_signal(sender, instance : TestModel, created : bool, **kwargs):
        if created:
            data.append(instance)
            
    test_models = TestModel.objects.bulk_create([
        TestModel(name="test 1"),
        TestModel(name="test 2"),
    ])
    assert test_models
    assert test_models[0] == data[0]
    assert test_models[1] == data[1]

@pytest.mark.django_db(transaction=True)
def test_pre_bulk_update_signal():

    data = []
    
    @receiver(pre_bulk_update, sender=TestModel)
    def function_signal(sender, instance : TestModel, created : bool, **kwargs):
        if not created:
            data.append(instance)
            
    test_models = [
        TestModel.objects.create(name="test 1"),
        TestModel.objects.create(name="test 2"),
    ]
    test_models[0].name = "updated test 1"
    test_models[1].name = "updated test 2"
    TestModel.objects.bulk_update(test_models, ["name"])
    assert test_models
    assert test_models[0] == data[0]
    assert test_models[1] == data[1]

@pytest.mark.django_db(transaction=True)
def test_post_bulk_update_signal():

    data = []
    
    @receiver(post_bulk_update, sender=TestModel)
    def function_signal(sender, instance : TestModel, created : bool, **kwargs):
        if not created:
            data.append(instance)
            
    test_models = [
        TestModel.objects.create(name="test 1"),
        TestModel.objects.create(name="test 2"),
    ]
    test_models[0].name = "updated test 1"
    test_models[1].name = "updated test 2"
    TestModel.objects.bulk_update(test_models, ["name"])
    assert test_models
    assert test_models[0] == data[0]
    assert test_models[1] == data[1]