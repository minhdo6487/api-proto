from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from rest_framework import viewsets
from rest_framework.parsers import JSONParser, FormParser

from core.golfcourse.models import GolfCourse
from utils.django.models import get_or_none
from api.galleryMana.serializers import GolfCourseGallerySerializer
from core.gallery.models import Gallery


class GalleryViewSet(viewsets.ModelViewSet):
    """ Viewset handle for requesting course information
    """
    queryset = Gallery.objects.all()
    serializer_class = GolfCourseGallerySerializer
    parser_classes = (JSONParser, FormParser,)

    def create(self, request):
        gc_id = request.DATA.get('object_id', "''")
        image = request.DATA.get('picture', "''")
        description = request.DATA.get('description', "''")
        if gc_id == '':
            return Response({"details": "Some Field Is Missing"}, status=400)
        golfcourse = get_or_none(GolfCourse, pk=gc_id)
        if golfcourse is None:
            return Response(status=404)
        ctype = ContentType.objects.get_for_model(golfcourse)
        try:
            data = {'picture': image, 'content_type': ctype.id, 'object_id': golfcourse.id, 'description': description}
            new_image = GolfCourseGallerySerializer(data=data)
            if not new_image.is_valid():
                return Response(new_image.errors, status=400)
            new_image.save()
            return Response(new_image.data, status=200)
        except Exception:
            return Response({"details": "Some Field Is Missing"}, status=400)

    def retrieve(self, request, pk=None):
        # gc_id = request.QUERY_PARAMS.get('golfcourse_id', 0)
        gc_id = pk
        if gc_id == 0:
            return Response({"details": "Some Field Is Missing"}, status=400)
        golfcourse = get_or_none(GolfCourse, pk=gc_id)

        if golfcourse is None:
            return Response(status=404)
        ctype = ContentType.objects.get_for_model(golfcourse)

        return_data = Gallery.objects.filter(content_type=ctype.id, object_id=golfcourse.id)
        re_data = []
        for item in return_data:
            return_item = {'id': item.id, 'picture': item.picture}
            re_data.append(return_item)
        return Response({'details': re_data}, status=200)

    def list(self, request):
        ctype = ContentType.objects.get_by_natural_key('golfcourse', 'golfcourse')

        return_data = Gallery.objects.filter(content_type=ctype.id)
        re_data = []
        for item in return_data:
            return_item = {'id': item.id, 'picture': item.picture}
            re_data.append(return_item)
        return Response({'details': re_data}, status=200)