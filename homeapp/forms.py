from django import forms
from django.core.validators import validate_email
from datetime import date
import re
from .models import tbl_Student, tbl_Login

from django import forms
from django.core.validators import validate_email
from datetime import date
import re
from .models import tbl_Student, tbl_Login
from django.core.exceptions import ValidationError 

class StudentRegistrationForm(forms.ModelForm):
    # Login fields
    email = forms.EmailField(max_length=100, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your email address'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Create a password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm your password'
    }))
    
    class Meta:
        model = tbl_Student
        exclude = ['login', 'created_at', 'status']
        fields = [
            'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'phno', 'dob', 
            'gender', 'profile_pic', 'educational_background'
        ]
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'phno': 'Phone Number',
            'dob': 'Date of Birth',
            'gender': 'Gender',
            'profile_pic': 'Profile Picture',
            'educational_background': 'Educational Background',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),
            'phno': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number'
            }),
            'dob': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': date.today().strftime('%Y-%m-%d')
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('', 'Select Gender'),
                ('Male', 'Male'),
                ('Female', 'Female'),
                ('Other', 'Other')
            ]),
            'educational_background': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your educational background...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom attributes or modify initial data
        self.fields['gender'].choices = [
            ('', 'Select Gender'),
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Other', 'Other')
        ]
        # Make profile_pic optional since it has blank=True in model
        self.fields['profile_pic'].required = False
        self.fields['profile_pic'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        
        try:
            validate_email(email)
        except forms.ValidationError:
            raise forms.ValidationError("Enter a valid email address.")
        
        # Check if email already exists
        if tbl_Login.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        
        return email
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            raise forms.ValidationError("Password is required.")
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        # Add more password validation if needed
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError("Password must contain at least one digit.")
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        return cleaned_data
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name:
            raise forms.ValidationError("First name is required.")
        if len(first_name) < 2:
            raise forms.ValidationError("First name must be at least 2 characters long.")
        if not first_name.isalpha():
            raise forms.ValidationError("First name should contain only letters.")
        return first_name
    
    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name:
            raise forms.ValidationError("Last name is required.")
        if len(last_name) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters long.")
        if not last_name.isalpha():
            raise forms.ValidationError("Last name should contain only letters.")
        return last_name
    
    def clean_phno(self):
        phno = self.cleaned_data.get('phno')
        if not phno:
            raise forms.ValidationError("Phone number is required.")
        
        # Remove any non-digit characters
        phno_digits = re.sub(r'\D', '', str(phno))
        
        if len(phno_digits) < 10:
            raise forms.ValidationError("Phone number must be at least 10 digits long.")
        
        return phno
    
    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if not dob:
            raise forms.ValidationError("Date of birth is required.")
        
        # Calculate age
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        if age < 15:
            raise forms.ValidationError("You must be at least 15 years old to register.")
        
        if age > 100:
            raise forms.ValidationError("Please enter a valid date of birth.")
        
        return dob
    
    def clean_educational_background(self):
        educational_background = self.cleaned_data.get('educational_background')
        if not educational_background:
            raise forms.ValidationError("Educational background is required.")
        if len(educational_background) < 10:
            raise forms.ValidationError("Please provide more details about your educational background (at least 10 characters).")
        return educational_background
    
    def clean_profile_pic(self):
        profile_pic = self.cleaned_data.get('profile_pic')
        if profile_pic:
            # Check file size (limit to 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if profile_pic.size > max_size:
                raise forms.ValidationError("Image file too large ( > 5MB )")
            
          
        
        return profile_pic
class LoginForm(forms.Form):
     email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )

     password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )

     def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user = tbl_Login.objects.get(email=email)
                if user.password != password:   # (Plain text – later we can hash)
                    raise ValidationError("Invalid email or password")
            except tbl_Login.DoesNotExist:
                raise ValidationError("Invalid email or password")

        return cleaned_data