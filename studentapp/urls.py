from .import views
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('student/home/', views.student_home, name='student_home'),
    path('student/course/<int:course_id>/', views.course_detail, name='course_detail'),

    path('enroll/course/<int:course_id>/', views.enroll_course, name='enroll_course'),
    path('enroll/payment/', views.process_payment, name='process_payment'),
    path('enroll/success/<int:enrollment_id>/', views.payment_success, name='payment_success'),
    path('my-courses/', views.my_courses, name='my_courses'),
    path('batch-classes/<int:batch_id>/', views.batch_classes, name='batch_classes'),
    path('submit-assignment/<int:batch_id>/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
    path('mark-lesson-viewed/<int:lesson_id>/', views.mark_lesson_viewed, name='mark_lesson_viewed'),
    path('cancel-enrollment/<int:enrollment_id>/', views.cancel_enrollment, name='cancel_enrollment'),
    path('download-assignment-file/<int:assignment_id>/', views.download_assignment_file, name='download_assignment_file'),
    path('ask-doubt/', views.ask_doubt, name='ask_doubt'),
    path('get-lesson-doubts/<int:lesson_id>/', views.get_lesson_doubts, name='get_lesson_doubts'),

    path('payment-details/<int:batch_id>/', views.payment_details, name='payment_details'),
    path('make-payment/<int:batch_id>/', views.make_payment, name='make_payment'),
    path('process-balance-payment/<int:batch_id>/', views.process_balance_payment, name='process_balance_payment'),


    path('batch-exams/<int:batch_id>/', views.batch_exams, name='batch_exams'),
    path('exam-instructions/<int:batch_id>/<int:exam_id>/', views.exam_instructions, name='exam_instructions'),
    path('take-exam/<int:batch_id>/<int:exam_id>/', views.take_exam, name='take_exam'),
    path('submit-exam/<int:batch_id>/<int:exam_id>/', views.submit_exam, name='submit_exam'),
    path('view-exam-result/<int:batch_id>/<int:exam_id>/', views.view_exam_result, name='view_exam_result'),

    path('add-review/<int:course_id>/<int:batch_id>/', views.add_course_review, name='add_course_review'),

    path('profile/', views.student_profile, name='student_profile'),
    path('attended-exams/', views.attended_exams, name='attended_exams'),
    path('view-certificate/<int:enrollment_id>/', views.view_certificate, name='view_certificate'),

    
]
if settings.DEBUG: 
 urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)