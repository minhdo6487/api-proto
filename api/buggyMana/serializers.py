from rest_framework import serializers
from core.golfcourse.models import GolfCourseBuggy,GolfCourseCaddy
class GolfCourseBuggySerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseBuggy
        fields = ('buggy','from_date','to_date','price_9','price_18','price_27','price_36','price_standard_9','price_standard_18','price_standard_27','price_standard_36')
    def to_native(self, obj):
        if obj:
            serializers = super(GolfCourseBuggySerializer, self).to_native(obj)
            serializers.update({'guest_type':'G',
                                'buggy_id': obj.id})
            return serializers
class GolfCourseCaddySerializer(serializers.ModelSerializer):
    class Meta:
        model = GolfCourseCaddy
        fields = ('price_9','price_18','price_27','price_36')
    def to_native(self, obj):
        if obj:
            serializers = super(GolfCourseCaddySerializer, self).to_native(obj)
            serializers.update({'guest_type':'G'})
            return serializers