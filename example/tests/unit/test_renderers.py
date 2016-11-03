import json
import pytest
import unittest
from collections import namedtuple
from example.models import Entry, Comment, Author, Blog
from rest_framework_json_api import serializers, views
from rest_framework_json_api.renderers import JSONRenderer


DummyRequest = namedtuple("DummyRequest", ['query_params'])


# serializers
class RelatedModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id',)


class DummyTestSerializer(serializers.ModelSerializer):
    '''
    This serializer is a simple compound document serializer which includes only
    a single embedded relation
    '''
    related_models = RelatedModelSerializer(
        source='comment_set', many=True, read_only=True)

    class Meta:
        model = Entry
        fields = ('related_models',)

    class JSONAPIMeta:
        included_resources = ('related_models',)


class AuthorTestSerializer(serializers.ModelSerializer):

    class Meta:
        model = Author
        fields = ('name',)
        lookup_field = 'name'


class EntryTestSerializer(serializers.ModelSerializer):

    included_serializers = {
        'authors': AuthorTestSerializer,
    }

    class Meta:
        model = Entry
        fields = ('headline', 'authors',)
        lookup_field = 'headline'

    class JSONAPIMeta:
        included_resources = ('authors',)


# views
class DummyTestViewSet(views.ModelViewSet):
    queryset = Entry.objects.all()
    serializer_class = DummyTestSerializer


class EntryTestViewSet(views.ModelViewSet):
    queryset = Entry.objects.all()
    serializer_class = EntryTestSerializer


def test_simple_reverse_relation_included_renderer():
    '''
    Test renderer when a single reverse fk relation is passed.
    '''
    serializer = DummyTestSerializer(instance=Entry())
    renderer = JSONRenderer()
    rendered = renderer.render(
        serializer.data,
        renderer_context={'view': DummyTestViewSet()})

    assert rendered


@pytest.mark.django_db
class TestRenderer(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestRenderer, self).__init__(*args, **kwargs)
        self.maxDiff = None

    def setUp(self, *args, **kwargs):
        super(TestRenderer, self).setUp(*args, **kwargs)
        self.blog = Blog.objects.create(name="TestBlog")
        self.author = Author.objects.create(name="JohnSnow")
        self.entry1 = Entry.objects.create(headline="BlogEntryTestHeadline01", blog=self.blog)
        self.entry1.authors.add(self.author)

    def test_resource_obj_id_replaced_by_lookup_field(self):
        """
        Check that the id of the primary resource object is replace by the lookup field
        """

        entry_serializer = EntryTestSerializer(instance=self.entry1)
        renderer = JSONRenderer()

        json_response = renderer.render(
            entry_serializer.data,
            renderer_context={
                'view': EntryTestViewSet(),
                'request': DummyRequest(query_params={
                        'include': "authors"
                    }
                )
            }
        )

        expected_json_response = {
            'data': {
                'id': "BlogEntryTestHeadline01",
                'type': "entries",
                'attributes': {
                    'headline': "BlogEntryTestHeadline01"
                },
                'relationships': {
                    'authors': {
                        'data': [
                            {
                                'id': "1",  # TODO: make sure this is also changed according to the lookup_field
                                'type': "authors"
                            }
                        ],
                        'meta': {
                            'count': 1
                        }
                    }
                }
            },
            'included': [
                {
                    'id': "JohnSnow",
                    'type': "authors",
                    'attributes': {
                        'name': "JohnSnow"
                    }
                }
            ]
        }

        self.assertEquals(json.loads(json_response.decode('utf-8')), expected_json_response)

    def test_included_resource_obj_id_replaced_by_lookup_field(self):
        """
        Check that the id of the included resource objects is replace by the lookup field
        """
        pass
