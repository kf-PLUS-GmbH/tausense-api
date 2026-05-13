from rest_framework import serializers

from municipalities.models import Municipality


class MunicipalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipality
        fields = ('id', 'name', 'geo_boundary')
