# from rest_framework.parsers import JSONParser, FormParser
# from rest_framework import viewsets
# from rest_framework.permissions import IsAuthenticated
# from core.user.models import BusinessArea, BusinessSubArea
# from api.businessMana.serializers import BusinessAreaSerializer, BusinessSubAreaSerializer
#
#
# class BusinessAreaViewSet(viewsets.ModelViewSet):
# """ Handle all function for Business
#     """
#     queryset = BusinessArea.objects.all()
#     serializer_class = BusinessAreaSerializer
#     permission_classes = (IsAuthenticated,)
#     parser_classes = (JSONParser, FormParser,)
#
#
# class BusinessSubAreaViewSet(viewsets.ModelViewSet):
#     """ Handle all function for Business
#     """
#     queryset = BusinessSubArea.objects.all()
#     serializer_class = BusinessSubAreaSerializer
#     permission_classes = (IsAuthenticated,)
#     parser_classes = (JSONParser, FormParser,)
