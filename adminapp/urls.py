from .import views
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admindashboard',views.loadadmindashboard,name='admindashboard'),

    path('manage_streams', views.manage_streams, name='manage_streams'),
    path('admin/streams/add/', views.manage_streams, name='add_stream'),
    path('admin/streams/edit/<int:stream_id>/', views.edit_stream, name='edit_stream'),
    path('admin/streams/delete/<int:stream_id>/', views.delete_stream, name='delete_stream'),

    path('manage_courses', views.manage_courses, name='manage_courses'),
    path('admin/courses/add/', views.add_course, name='add_course'),
    path('admin/courses/edit/<int:course_id>/', views.edit_course, name='edit_course'),
    path('admin/courses/delete/<int:course_id>/', views.delete_course, name='delete_course'),
    path('admin/courses/detail/<int:course_id>/', views.course_detail, name='course_detail'),
    path('admin/courses/by-stream/', views.get_courses_by_stream, name='get_courses_by_stream'),

    path('manage_batches', views.manage_batches, name='manage_batches'),
    path('admin/batches/add/', views.add_batch, name='add_batch'),
    path('admin/batches/edit/<int:batch_id>/', views.edit_batch, name='edit_batch'),
    path('admin/batches/delete/<int:batch_id>/', views.delete_batch, name='delete_batch'),
    path('admin/batches/detail/<int:batch_id>/', views.batch_detail, name='batch_detail'),
    path('admin/batches/by-course/', views.get_batches_by_course, name='get_batches_by_course'),

    path('admin/teachers/', views.manage_teachers, name='manage_teachers'),
    path('admin/teachers/view/<int:teacher_id>/', views.view_teacher, name='view_teacher'),
    path('admin/teachers/edit/<int:teacher_id>/', views.edit_teacher, name='edit_teacher'),
    path('admin/teachers/delete/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),

    path('admin/teacher-batches/', views.manage_teacher_batches, name='manage_teacher_batches'),
    path('admin/get-teachers-by-stream/', views.get_teachers_by_stream, name='get_teachers_by_stream'),
    path('admin/replace-teacher/<int:batch_id>/', views.replace_teacher_assignment, name='replace_teacher_assignment'),

    path('exams/', views.exam_management, name='exam_management'),
    path('exams/create/', views.create_exam, name='create_exam'),
    path('exams/get-questions/', views.get_exam_questions, name='get_exam_questions'),
    path('exams/get-question-details/', views.get_question_details, name='get_question_details'),
    path('exams/add-question/', views.add_question, name='add_question'),
    path('exams/update-question/', views.update_question, name='update_question'),
    path('exams/delete-question/', views.delete_question, name='delete_question'),
    path('exams/delete/', views.delete_exam, name='delete_exam'),

    path('manage-students/', views.manage_students, name='manage_students'),
    path('student/<int:student_id>/', views.student_detail, name='student_detail'),
    path('student/<int:student_id>/payments/', views.student_payments, name='student_payments'),
    path('student/<int:student_id>/progress/<int:enrollment_id>/', views.student_progress, name='student_progress'),
    path('export-students-csv/', views.export_students_csv, name='export_students_csv'),

]
if settings.DEBUG: 
 urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
