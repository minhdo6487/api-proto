from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from GolfConnect.settings import BASE_DIR
from os.path import exists, join


@api_view(['GET'])
def version(request):
    version_str = '1.0.0'
    version_file = join(BASE_DIR, 'version')
    if exists(version_file):
        with open(version_file) as file:
            version_str = file.read().strip()

    return Response({'version': version_str}, status=200)
