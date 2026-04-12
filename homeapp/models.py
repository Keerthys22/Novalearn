from django.db import models
from datetime import date

# Create your models here.
class tbl_Login(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    usertype = models.CharField(max_length=50)

    def _str_(self):
        return self.email
    
class tbl_Student(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phno = models.CharField(max_length=15)
    dob = models.DateField()
    gender = models.CharField(max_length=10)
    profile_pic = models.FileField(upload_to='studentpic/',blank=True)
    educational_background = models.TextField()
    created_at = models.DateField(default=date.today)
    login = models.ForeignKey(tbl_Login, on_delete=models.CASCADE)
    status = models.CharField(max_length=20,default="Active")

    def _str_(self):
        return self.name
