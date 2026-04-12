from django.db import models
from adminapp.models import*
import datetime


# Create your models here.
class tbl_lessons(models.Model):
    batch=models.ForeignKey('adminapp.Batch', on_delete=models.CASCADE)
    modulenumber=models.IntegerField()
    moduletitle=models.CharField(max_length=100)
    lessontitle=models.CharField(max_length=100)
    pdfnotes=models.FileField(upload_to='pdfnotes/',blank=True, null=True)
    videos=models.FileField(upload_to='videos/',blank=True, null=True)

class tbl_assignment(models.Model):
    batch=models.ForeignKey('adminapp.Batch', on_delete=models.CASCADE)
    uploaddate=models.DateField(default=date.today)
    duedate=models.DateField()
    totalmarks=models.IntegerField()
    assignmentupload = models.FileField(upload_to='assignments/',blank=True, null=True)
    created_at = models.DateTimeField(default=date.today)

    class Meta:
        db_table = 'tbl_assignment'

    def _str_(self):
        return f"Assignment - {self.batch.batchname}"
    
class tbl_final(models.Model):
    student_enrolment_id = models.ForeignKey('studentapp.tbl_student_enrolment', on_delete=models.CASCADE)
    final_mark = models.IntegerField()
    
    class Meta:
        db_table = 'tbl_final'
        unique_together = ['student_enrolment_id']  # One final mark per enrollment
    
    def __str__(self):
        return f"Final Mark: {self.final_mark}"

