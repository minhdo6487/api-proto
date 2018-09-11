from django.db import models

class Unaccent(models.Transform):
    bilateral = True
    lookup_name = 'unaccent'

    def as_postgresql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return "UNACCENT(%s)" % lhs, params

models.CharField.register_lookup(Unaccent)
models.TextField.register_lookup(Unaccent)
