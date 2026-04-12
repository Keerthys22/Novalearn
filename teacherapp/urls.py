from .import views
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from teacherapp.views import *



urlpatterns = [
path('teacherdashboard', views.teacherbatch, name='teacherdashboard'),
path('teacher/dashboard/', views.teacherbatch, name='teacherdashboard'),

path('teacher/profile/', views.teacher_profile, name='teacher_profile'),
 
path('manage_recorded_classes', views.manage_recorded_classes, name='manage_recorded_classes'),
path('add_lesson_page', views.add_lesson_page, name='add_lesson_page'),  # Changed this
path('add-lesson/submit/', views.add_lesson, name='add_lesson'),
path('edit-lesson/<int:lesson_id>', views.edit_lesson, name='edit_lesson'),
path('delete-lesson/<int:lesson_id>', views.delete_lesson, name='delete_lesson'),   
path('setbatchsession/<int:batch_id>', views.set_batch_session, name='setbatchsession'),

path('manage-assignments/', views.manage_assignments, name='manage_assignments'),
path('add-assignment-page/', views.add_assignment_page, name='add_assignment_page'),
path('add-assignment/', views.add_assignment, name='add_assignment'),
path('edit-assignment/<int:assignment_id>/', views.edit_assignment, name='edit_assignment'),
path('delete-assignment/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),
path('download-assignment/<int:assignment_id>/', views.download_assignment, name='download_assignment'),

path('manage-doubts/', views.manage_doubts, name='manage_doubts'),
path('lesson-doubts/<int:lesson_id>/', views.lesson_doubts, name='lesson_doubts'),
path('answer-doubt/<int:doubt_id>/', views.answer_doubt, name='answer_doubt'),
path('doubt-detail/<int:doubt_id>/', views.doubt_detail, name='doubt_detail'),
path('delete-doubt/<int:doubt_id>/', views.delete_doubt, name='delete_doubt'),
path('bulk-answer-doubts/<int:lesson_id>/', views.bulk_answer_doubts, name='bulk_answer_doubts'),
    
    # AJAX endpoints
path('ajax-answer-doubt/', views.ajax_answer_doubt, name='ajax_answer_doubt'),
path('get-lesson-doubts-api/<int:lesson_id>/', views.get_lesson_doubts_api, name='get_lesson_doubts_api'),

path('my-students/', views.teacher_students, name='teacher_students'),
path('student-assignments/<int:student_id>/<int:batch_id>/', views.student_assignments_page, name='student_assignments_page'),
path('student-exam-marks/<int:student_id>/<int:batch_id>/', views.student_exam_marks_page, name='student_exam_marks_page'),
path('student-payment/<int:student_id>/<int:batch_id>/', views.student_payment_page, name='student_payment_page'),
path('student-final-score/<int:student_id>/<int:batch_id>/', views.student_final_score_page, name='student_final_score_page'),
path('save-assignment-marks/', views.save_assignment_marks, name='save_assignment_marks'),
path('save-final-mark/', views.save_final_mark, name='save_final_mark'),
]
if settings.DEBUG: 
 urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)