from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

"""
    List of mixins
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
"""


class ModelViewSetNoCreate(mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           mixins.DestroyModelMixin,
                           mixins.ListModelMixin,
                           GenericViewSet):
    pass


class CreateOnlyViewSet(mixins.CreateModelMixin,
                        GenericViewSet):
    pass


class CreateRetrieViewSet(mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          GenericViewSet):
    pass


class NotUpdateViewSet(mixins.RetrieveModelMixin,
                       mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.DestroyModelMixin,
                       GenericViewSet):
    pass


class GetAndUpdateViewSet(mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.ListModelMixin,
                          GenericViewSet):
    pass


class ListOnlyViewSet(mixins.ListModelMixin,
                      GenericViewSet):
    pass


class OnlyGetViewSet(mixins.RetrieveModelMixin,
                     mixins.ListModelMixin,
                     GenericViewSet):
    pass


class NotDeleteViewSet(mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.ListModelMixin,
                       GenericViewSet):
    pass