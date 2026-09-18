from django.urls import path
from .views import (
    MentorReviewQueueView,
    AttemptEventsDetailView,
    SubmitMentorVerdictView
)

urlpatterns = [
    path('review-queue/', MentorReviewQueueView.as_view(), name='mentor_review_queue'),
    path('attempts/<uuid:attempt_id>/events/', AttemptEventsDetailView.as_view(), name='attempt_events_detail'),
    path('attempts/<uuid:attempt_id>/verdict/', SubmitMentorVerdictView.as_view(), name='submit_mentor_verdict'),
]
