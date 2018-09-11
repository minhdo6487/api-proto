from django.db import models
from django import VERSION as DJANGO_VERSION
from v2.utils.geohash_service import Geohash, convert_to_point
import six


class GeohashField(models.CharField, metaclass=models.SubfieldBase):

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 12
        kwargs['db_index'] = True
        return super(GeohashField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, six.string_types):
            return Geohash(value)
        return convert_to_point(value).geohash


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^v2\.core\.geohash\.fields\.GeohashField"])
except:
    pass