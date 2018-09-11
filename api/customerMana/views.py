from rest_framework.parsers import JSONParser, FormParser
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.customer.models import Customer
from api.customerMana.serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, FormParser,)