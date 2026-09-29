from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response as ApiResponse
from rest_framework.views import APIView

from .models import Response, Survey
from .serializers import ResponseSerializer, ResultsFilterSerializer, WebhookSerializer


class SurveyResultsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, survey_id):
        survey = get_object_or_404(
            Survey, pk=survey_id, organization__memberships__user=request.user
        )
        serializer = ResultsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data
        responses = Response.objects.filter(survey=survey)
        if "from" in filters:
            responses = responses.filter(submitted_at__date__gte=filters["from"])
        if "to" in filters:
            responses = responses.filter(submitted_at__date__lte=filters["to"])

        return ApiResponse(
            {
                "survey": {"id": survey.id, "title": survey.title},
                "count": responses.count(),
                "results": ResponseSerializer(responses, many=True).data,
            }
        )


class ResponseWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if request.headers.get("X-Webhook-Token") != settings.WEBHOOK_TOKEN:
            return ApiResponse({"detail": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = WebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        survey = get_object_or_404(Survey, external_key=payload["survey_key"])

        response, created = Response.objects.get_or_create(
            survey=survey,
            external_id=payload["event_id"],
            defaults={
                "status": payload["status"],
                "answers": payload["answers"],
                "submitted_at": payload["submitted_at"],
            },
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK

        return ApiResponse(ResponseSerializer(response).data, status=response_status)

