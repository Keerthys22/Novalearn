from django.db import models
from homeapp.models import *
from studentapp.models import *

class Stream(models.Model):
    streamcode = models.CharField(max_length=20, unique=True)
    stream_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    STATUS_CHOICES = (
        (1, 'Active'),
        (0, 'Inactive'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)

    class Meta:
        db_table = 'tbl_stream'

    
    def __str__(self):  # Fixed: double underscore on both sides
        return f"{self.streamcode} - {self.stream_name}" 
    
class Course(models.Model):
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE)  # links to Stream
    coursename = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    durationweeks = models.PositiveIntegerField()  # duration in weeks
    rate = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.FileField(upload_to='courseimage/', blank=True, null=True)
    class Meta:
        db_table = 'tbl_course'

    def __str__(self):  # Fixed: double underscore on both sides
        return f"{self.coursename} ({self.stream.streamcode})"
    
class Batch(models.Model):
    batchcode = models.CharField(max_length=50, unique=True)
    batchname = models.CharField(max_length=100)
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    startdate=models.DateField(blank=True, null=True)
    status=models.CharField(max_length=100, default="Open")
    class Meta:
        db_table = 'tbl_batch'

    def _str_(self):
        return f"{self.batchname} ({self.batchcode})"
    
class tbl_teacher(models.Model):
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    qualification = models.CharField(max_length=100)
    specialization = models.TextField()
    experienceyear = models.PositiveIntegerField()  # Changed to PositiveIntegerField
    department = models.ForeignKey('Stream', on_delete=models.CASCADE)
    bio = models.FileField(upload_to='teacherbio/', blank=True, null=True)  # Added null=True
    profilepic = models.FileField(upload_to='teacherpic/', blank=True, null=True)  # Changed to ImageField
    login = models.ForeignKey(tbl_Login, on_delete=models.CASCADE)
    class Meta:
        db_table = 'tbl_teacher'
    
    def __str__(self):
        return f"{self.firstname} {self.lastname}"
    
class tbl_teacherbatch(models.Model):
    teacher = models.ForeignKey(tbl_teacher, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'tbl_teacherbatch'
        unique_together = ['teacher', 'batch']  # Prevent duplicate assignments
    
    def __str__(self):
        return f"{self.teacher.firstname} {self.teacher.lastname} -> {self.batch.batchname}"

class exam(models.Model):
    courseid=models.ForeignKey('Course', on_delete=models.CASCADE)
    totalscore=models.IntegerField()
    examcode=models.CharField(max_length=50)
    duration=models.IntegerField()

class tbl_question(models.Model):
    question=models.CharField(max_length=100)

class tbl_option(models.Model):
    questionid=models.ForeignKey('tbl_question', on_delete=models.CASCADE)
    option=models.CharField(max_length=100)
    answerstatus=models.BooleanField(default="false")
    
class tbl_examquestion(models.Model):
    questionid=models.ForeignKey('tbl_question', on_delete=models.CASCADE)
    examid=models.ForeignKey('exam', on_delete=models.CASCADE)

class tbl_student_examresult(models.Model):
    student_enrol_id=models.ForeignKey('studentapp.tbl_student_enrolment', on_delete=models.CASCADE)
    examid=models.ForeignKey('exam', on_delete=models.CASCADE)
    total_score_obtained=models.IntegerField()

