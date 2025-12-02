from django.urls import path
from . import views
from .auth_views import login_view, logout_view, check_auth

urlpatterns = [
    path('', views.index, name='index'),
    path('init-db', views.init_db, name='init_db'),
    path('jd/analyze/pdf', views.analyze_jd_pdf, name='analyze_jd_pdf'),
    path('resumes/upload', views.upload_resumes, name='upload_resumes'),
    path('match/top-by-role', views.get_top_matches_by_role, name='match_top_by_role'),
    path('match/top-by-jd', views.get_top_matches_by_jd_id, name='match_top_by_jd'),
    path('send-emails', views.send_emails_to_candidates, name='send_emails'),
    path('acknowledge/<str:outreach_id>', views.acknowledge_interest, name='acknowledge_interest'),
    path('confirm-interview/<str:interview_id>', views.confirm_interview, name='confirm_interview'),
    path('schedule-interviews', views.schedule_interviews, name='schedule_interviews'),
    path('interviews/status', views.get_interviews_status, name='get_interviews_status'),
    # Authentication endpoints
    path('auth/login', login_view, name='login'),
    path('auth/logout', logout_view, name='logout'),
    path('auth/check', check_auth, name='check_auth'),
]
