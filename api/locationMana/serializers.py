from rest_framework import serializers

from core.location.models import Country, City, District


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District