from django.db import models
from adminapp.models import*
from homeapp.models import*
from teacherapp.models import*
from datetime import date
from django.utils import timezone 

class tbl_student_enrolment(models.Model):
 
    enrolled_batchid=models.ForeignKey('adminapp.Batch', on_delete=models.CASCADE)
    course_status=models.CharField(max_length=100, default="active")
    enrollment_date=models.DateField(date.today)
    is_active_student=models.CharField(max_length=100, default="yes")
    studentid=models.ForeignKey('homeapp.tbl_student',on_delete=models.CASCADE)
    
class tbl_payment(models.Model):
    student_enrol_id=models.ForeignKey('tbl_student_enrolment', on_delete=models.CASCADE)
    paymentdate = models.DateField(default=date.today)
    payment_mode=models.CharField(max_length=100, default="card")
    paymentstatus=models.CharField(max_length=100, default="pending")
    amount=models.DecimalField(max_digits=8, decimal_places=2)

class tbl_assignmentstudent(models.Model):
    assignment = models.ForeignKey('teacherapp.tbl_assignment', on_delete=models.CASCADE, db_column='assignment_id')
    student = models.ForeignKey(tbl_Student, on_delete=models.CASCADE, db_column='student_id')
    submitteddate = models.DateTimeField(default=date.today)
    assignmentuploaded = models.FileField(upload_to='assignment_submission/')
    assigned_marks = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'tbl_assignmentstudent'
        unique_together = ['assignment', 'student']  # Prevent multiple submissions
    
    def __str__(self):
        return f"{self.student.firstname} - Assignment {self.assignment.id}"

class tbl_doubt(models.Model):
    description=models.CharField(max_length=200)
    date_submitted=models.DateTimeField(default=date.today)
    answer=models.CharField(max_length=200)
    answer_submitted=models.DateTimeField(default=date.today)
    student_enrolment_id=models.ForeignKey('tbl_student_enrolment', on_delete=models.CASCADE)
    lesson_id=models.ForeignKey('teacherapp.tbl_lessons',on_delete=models.CASCADE, null=True, blank=True)

class tbl_course_review(models.Model):
    student = models.ForeignKey(tbl_Student, on_delete=models.CASCADE)
    course = models.ForeignKey('adminapp.Course', on_delete=models.CASCADE)
    batch = models.ForeignKey('adminapp.Batch', on_delete=models.CASCADE, null=True, blank=True)
    rating = models.IntegerField(choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')])
    review_text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_approved = models.BooleanField(default=False)  # Optional: for admin approval
    
    class Meta:
        db_table = 'tbl_course_review'
        unique_together = ['student', 'course']  # One review per student per course
    
    def __str__(self):
        return f"{self.student.first_name} - {self.course.coursename} - {self.rating}★"
    
    