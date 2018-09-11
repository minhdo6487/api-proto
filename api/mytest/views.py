
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
def hello(request):
  return Response({'status': 200}, status=200)


@api_view(['GET'])
@permission_classes((IsAuthenticated,))
def hello_auth(request):
  response = {
    'status': 200,
    'user': request.user.id,
  }
  return Response(response, status=response['status'])
