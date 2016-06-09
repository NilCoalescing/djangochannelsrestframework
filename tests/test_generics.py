import json

from channels import route_class
from channels.tests import ChannelTestCase, Client, apply_routes

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from channels_api import generics
from .models import TestModel


class TestModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestModel
        fields = ('id', 'name')


class TestModelConsumer(generics.ModelConsumer):

    model = TestModel
    queryset = TestModel.objects.all()
    serializer_class = TestModelSerializer


class ModelConsumerTestCase(ChannelTestCase):

    def setUp(self):
        super().setUp()
        self.client = Client()

    def _send_and_consume(self, channel, data):
        """Helper that wraps data in a WebSocket frame.

        Returns the next message from the reply channel as json.
        """
        ws_frame = {'text': json.dumps(data), 'path': '/'}
        self.client.send_and_consume(channel, ws_frame)
        msg = self.client.get_next_message(self.client.reply_channel)
        return json.loads(msg['text'])

    def test_create(self):
        """Integration that asserts routing a message to the create channel.

        Asserts response is correct and an object is created.
        """
        with apply_routes([route_class(TestModelConsumer)]):
            json_content = self._send_and_consume('testmodel.create', {'name': 'some-name'})

            # it should create an object
            self.assertEqual(TestModel.objects.count(), 1)

            # it should respond with the serializer.data
            self.assertEqual(json_content, TestModelSerializer(TestModel.objects.first()).data)

    def test_create_failure(self):
        """Integration that asserts error handling of a message to the create channel."""
        class FailingTestModelConsumer(TestModelConsumer):

            def create(self, message, **kwargs):
                raise ValidationError("You fail")

        with apply_routes([route_class(FailingTestModelConsumer)]):
            json_content = self._send_and_consume('testmodel.create', {'name': 'some-name'})
            # it should not create an object
            self.assertEqual(TestModel.objects.count(), 0)
            # it should respond with an error
            self.assertEqual(json_content, {'errors': ['You fail']})

    def test_delete(self):
        with apply_routes([route_class(TestModelConsumer)]):
            instance = TestModel.objects.create(name='Test')
            self._send_and_consume('testmodel.delete', {'id': instance.id})
            # it should delete the object
            self.assertEqual(TestModel.objects.count(), 0)

    def test_update(self):

        with apply_routes([route_class(TestModelConsumer)]):
            instance = TestModel.objects.create(name="Test")
            json_content = self._send_and_consume('testmodel.update', {'name': 'Success', 'id': instance.id})
            # it should update the object
            instance.refresh_from_db()
            self.assertEqual(instance.name, 'Success')
            # it should respond with serializer.data
            self.assertEqual(json_content, TestModelSerializer(instance).data)

    def test_retrieve(self):

        with apply_routes([route_class(TestModelConsumer)]):
            instance = TestModel.objects.create(name="Test")
            json_content = self._send_and_consume('testmodel.retrieve', {'id': instance.id})
            # it should respond with serializer.data
            self.assertEqual(json_content, TestModelSerializer(instance).data)

    def test_list(self):

        with apply_routes([route_class(TestModelConsumer)]):
            for x in range(3):
                TestModel.objects.create(name="Test:{}".format(x))
            json_content = self._send_and_consume('testmodel.list', {})
            # it should return all
            instances = TestModel.objects.all()
            self.assertEqual(json_content, TestModelSerializer(instances, many=True).data)
