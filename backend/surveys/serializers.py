from rest_framework import serializers

from .models import Response


class ResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ["id", "external_id", "status", "answers", "submitted_at"]


class WebhookSerializer(serializers.Serializer):
    survey_key = serializers.CharField()
    event_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["partial", "complete"])
    answers = serializers.JSONField()
    submitted_at = serializers.DateTimeField()


class ResultsFilterSerializer(serializers.Serializer):
    def get_fields(self):
        # "from" is a Python keyword, so it cannot be declared as a class attribute.
        return {
            "from": serializers.DateField(required=False),
            "to": serializers.DateField(required=False),
        }

    def validate(self, attrs):
        if "from" in attrs and "to" in attrs and attrs["from"] > attrs["to"]:
            raise serializers.ValidationError(
                {"to": "Debe ser igual o posterior a from."}
            )
        return attrs

