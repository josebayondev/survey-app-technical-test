from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.query import QuerySet
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Membership, Organization, Response, Survey


class SurveyApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Northwind")
        self.user = get_user_model().objects.create_user("ana", password="ana123")
        Membership.objects.create(user=self.user, organization=self.organization)
        self.survey = Survey.objects.create(
            organization=self.organization,
            title="Customer satisfaction",
            external_key="northwind-csat",
        )
        Response.objects.create(
            survey=self.survey,
            external_id="evt-001",
            status="complete",
            answers={"nps": 9},
            submitted_at=timezone.now() - timedelta(days=1),
        )
        self.other_organization = Organization.objects.create(name="Contoso")
        self.other_survey = Survey.objects.create(
            organization=self.other_organization,
            title="Employee NPS",
            external_key="contoso-enps",
        )
        self.webhook_payload = {
            "survey_key": self.survey.external_key,
            "event_id": "evt-002",
            "status": "complete",
            "answers": {"nps": 8},
            "submitted_at": timezone.now().isoformat(),
        }
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_authorized_user_can_list_results(self):
        response = self.client.get(f"/api/surveys/{self.survey.id}/results/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_user_cannot_access_survey_from_another_organization(self):
        response = self.client.get(f"/api/surveys/{self.other_survey.id}/results/")

        self.assertEqual(response.status_code, 404)

    def test_member_of_several_organizations_can_access_each_survey(self):
        Membership.objects.create(user=self.user, organization=self.other_organization)

        own_response = self.client.get(f"/api/surveys/{self.survey.id}/results/")
        other_response = self.client.get(
            f"/api/surveys/{self.other_survey.id}/results/"
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 200)

    def test_webhook_rejects_invalid_token(self):
        response = self.client.post(
            "/api/webhooks/responses/",
            {
                "survey_key": self.survey.external_key,
                "event_id": "evt-002",
                "status": "complete",
                "answers": {"nps": 8},
                "submitted_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_webhook_duplicate_event_creates_single_response(self):
        first_response = self.client.post(
            "/api/webhooks/responses/",
            self.webhook_payload,
            format="json",
            headers={"X-Webhook-Token": settings.WEBHOOK_TOKEN},
        )
        second_response = self.client.post(
            "/api/webhooks/responses/",
            self.webhook_payload,
            format="json",
            headers={"X-Webhook-Token": settings.WEBHOOK_TOKEN},
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.data["id"], first_response.data["id"])
        self.assertEqual(Response.objects.filter(external_id="evt-002").count(), 1)

    def test_response_event_is_unique_per_survey(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Response.objects.create(
                survey=self.survey,
                external_id="evt-001",
                status="complete",
                answers={"nps": 9},
                submitted_at=timezone.now(),
            )

    def test_webhook_handles_concurrent_duplicate_event(self):
        original_get = QuerySet.get
        missed_lookups = []

        def get_missing_first_response(queryset, *args, **kwargs):
            # Simulates another request inserting the event right after our lookup.
            if queryset.model is Response and not missed_lookups:
                missed_lookups.append(kwargs)
                raise Response.DoesNotExist
            return original_get(queryset, *args, **kwargs)

        with mock.patch.object(QuerySet, "get", get_missing_first_response):
            response = self.client.post(
                "/api/webhooks/responses/",
                {**self.webhook_payload, "event_id": "evt-001"},
                format="json",
                headers={"X-Webhook-Token": settings.WEBHOOK_TOKEN},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Response.objects.filter(external_id="evt-001").count(), 1)
        self.assertEqual(len(missed_lookups), 1)

    def test_webhook_accepts_same_event_id_in_another_survey(self):
        response = self.client.post(
            "/api/webhooks/responses/",
            {
                **self.webhook_payload,
                "survey_key": self.other_survey.external_key,
                "event_id": "evt-001",
            },
            format="json",
            headers={"X-Webhook-Token": settings.WEBHOOK_TOKEN},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Response.objects.filter(external_id="evt-001").count(), 2)

