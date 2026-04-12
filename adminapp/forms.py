from django import forms
from .models import Stream
from .models import Course
from .models import Batch
import re
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from .models import*

class StreamForm(forms.ModelForm):
    class Meta:
        model = Stream
        fields = ['streamcode', 'stream_name', 'description', 'status']  # Keep status in fields but exclude from widget
        widgets = {
            'streamcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter stream code (e.g., ENG, SCI)',
                'maxlength': '20'
            }),
            'stream_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter stream name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter description (optional)',
                'rows': 4
            }),
            # Don't include status widget - it will be hidden
        }
        labels = {
            'streamcode': 'Stream Code',
            'stream_name': 'Stream Name',
            'description': 'Description',
            'status': 'Status',  # This won't show in the form
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default status to 1 (Active) for new forms
        if not self.instance.pk:  # Only for new forms (not editing existing)
            self.fields['status'].initial = 1
        # Hide the status field from the form display
        self.fields['status'].widget = forms.HiddenInput()

    def clean_streamcode(self):
        streamcode = self.cleaned_data.get('streamcode')
        if not streamcode:
            raise forms.ValidationError("Stream code is required.")
        # Check if streamcode already exists (excluding current instance for edit)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            if Stream.objects.filter(streamcode=streamcode.upper()).exclude(pk=instance.pk).exists():
                raise forms.ValidationError("This stream code already exists.")
        else:
            if Stream.objects.filter(streamcode=streamcode.upper()).exists():
                raise forms.ValidationError("This stream code already exists.")
        return streamcode.upper()  # Convert to uppercase

    def clean_stream_name(self):
        stream_name = self.cleaned_data.get('stream_name')
        if not stream_name:
            raise forms.ValidationError("Stream name is required.")
        if len(stream_name) < 3:
            raise forms.ValidationError("Stream name must be at least 3 characters long.")
        return stream_name

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['stream', 'coursename', 'description', 'durationweeks', 'rate', 'image']
        widgets = {
            'stream': forms.Select(attrs={'class': 'form-control'}),
            'coursename': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter course name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter course description'}),
            'durationweeks': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duration in weeks', 'min': 1, 'max': 52}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_streams = Stream.objects.filter(status=1).order_by('stream_name')
        
        # Create a ModelChoiceField with custom empty label
        self.fields['stream'] = forms.ModelChoiceField(
            queryset=active_streams,
            widget=forms.Select(attrs={'class': 'form-control'}),
            label='Stream',
            empty_label="--- Select Stream ---",
            required=True
        )
        
        # Add help texts
        self.fields['rate'].help_text = "Enter course price in USD"
        self.fields['image'].help_text = "Upload course image (JPG, PNG, GIF)"
        self.fields['durationweeks'].help_text = "Enter duration in weeks (1-52)"
        
    def clean_rate(self):
        rate = self.cleaned_data.get('rate')
        if rate < 0:
            raise forms.ValidationError("Rate cannot be negative")
        return rate
    
    def clean_durationweeks(self):
        duration = self.cleaned_data.get('durationweeks')
        if duration < 1 or duration > 52:
            raise forms.ValidationError("Duration must be between 1 and 52 weeks")
        return duration
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image file too large (max 5MB)")
            
            # Check file extension
            import os
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                raise forms.ValidationError("Only JPG, PNG, and GIF files are allowed")
        return image


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['batchcode', 'batchname', 'course', 'startdate', 'status']  # Added new fields

        widgets = {
            'batchcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter batch code (e.g. B2025)',
                'style': 'text-transform:uppercase'
            }),
            'batchname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter batch name'
            }),
            'course': forms.Select(attrs={
                'class': 'form-control'
            }),
            'startdate': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Select start date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('Open', 'Open'),
                ('In Progress', 'In Progress'),
                ('Closed', 'Closed'),
                ('Completed', 'Completed')
            ]),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add default "Select" label to course dropdown
        self.fields['course'].empty_label = "--- Select Course ---"
        
        # Order courses by name
        self.fields['course'].queryset = Course.objects.all().order_by('coursename')
        
        # Set default status
        self.fields['status'].initial = 'Open'
        
        # Make startdate optional (since it has blank=True, null=True in model)
        self.fields['startdate'].required = False
        
        # Add help text
        self.fields['batchcode'].help_text = "Unique batch code (will be auto-uppercased)"
        self.fields['startdate'].help_text = "Leave empty if not decided yet"
        
    def clean_batchcode(self):
        """Convert batchcode to uppercase and check uniqueness"""
        batchcode = self.cleaned_data.get('batchcode')
        if batchcode:
            # Convert to uppercase
            batchcode = batchcode.upper()
            
            # Check uniqueness (exclude current instance when editing)
            if Batch.objects.filter(batchcode=batchcode).exclude(id=self.instance.id).exists():
                raise forms.ValidationError("Batch code already exists. Please use a unique code.")
                
        return batchcode
    
    def clean_startdate(self):
        """Optional: Add validation for start date if needed"""
        startdate = self.cleaned_data.get('startdate')
        # You can add validation here if needed
        # Example: Ensure start date is not in the past
        # from datetime import date
        # if startdate and startdate < date.today():
        #     raise forms.ValidationError("Start date cannot be in the past")
        return startdate



class TeacherRegistrationForm(forms.ModelForm):
    # Login fields
    email = forms.EmailField(max_length=100, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter teacher\'s email address',
        'id': 'teacher-email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Create a password',
        'id': 'teacher-password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirm password',
        'id': 'teacher-confirm-password'
    }))
    
    class Meta:
        model = tbl_teacher
        exclude = ['login']  # Exclude login field, we'll handle it separately
        fields = [
            'email', 'password', 'confirm_password',
            'firstname', 'lastname', 'qualification', 
            'specialization', 'experienceyear', 'department',
            'bio', 'profilepic'
        ]
        widgets = {
            'firstname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name',
                'id': 'teacher-firstname'
            }),
            'lastname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name',
                'id': 'teacher-lastname'
            }),
            'qualification': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., M.Tech, PhD, M.Sc',
                'id': 'teacher-qualification'
            }),
            'specialization': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Areas of specialization',
                'id': 'teacher-specialization'
            }),
            'experienceyear': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Years of experience',
                'min': 0,
                'max': 50,
                'id': 'teacher-experience'
            }),
            'department': forms.Select(attrs={
                'class': 'form-control',
                'id': 'teacher-department'
            }),
            'bio': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'teacher-bio',
                'accept': '.pdf,.doc,.docx'
            }),
            'profilepic': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'teacher-profilepic',
                'accept': 'image/*'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add empty label for department dropdown
        self.fields['department'].empty_label = "--- Select Department ---"
        
        # Filter only active streams for department
        self.fields['department'].queryset = Stream.objects.filter(status=1).order_by('stream_name')
        
        # Make file fields optional
        self.fields['bio'].required = False
        self.fields['profilepic'].required = False
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        
        try:
            validate_email = EmailValidator()
            validate_email(email)
        except ValidationError:
            raise forms.ValidationError("Enter a valid email address.")
        
        # Check if email already exists
        if tbl_Login.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        
        return email.lower()  # Convert to lowercase
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password:
            raise forms.ValidationError("Password is required.")
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        return cleaned_data
    
    def clean_firstname(self):
        firstname = self.cleaned_data.get('firstname')
        if not firstname:
            raise forms.ValidationError("First name is required.")
        if len(firstname) < 2:
            raise forms.ValidationError("First name must be at least 2 characters long.")
        return firstname
    
    def clean_lastname(self):
        lastname = self.cleaned_data.get('lastname')
        if not lastname:
            raise forms.ValidationError("Last name is required.")
        if len(lastname) < 2:
            raise forms.ValidationError("Last name must be at least 2 characters long.")
        return lastname
    
    def clean_experienceyear(self):
        experience = self.cleaned_data.get('experienceyear')
        if experience is None:
            raise forms.ValidationError("Experience years is required.")
        if experience < 0:
            raise forms.ValidationError("Experience cannot be negative.")
        if experience > 50:
            raise forms.ValidationError("Experience cannot exceed 50 years.")
        return experience
    
    def clean_bio(self):
        bio = self.cleaned_data.get('bio')
        if bio:
            # Check file size (limit to 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if bio.size > max_size:
                raise forms.ValidationError("Bio file too large ( > 10MB )")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx']
            if not any(bio.name.lower().endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError("Only PDF, DOC, and DOCX files are allowed.")
        
        return bio
    
    def clean_profilepic(self):
        profilepic = self.cleaned_data.get('profilepic')
        if profilepic:
            # Check file size (limit to 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if profilepic.size > max_size:
                raise forms.ValidationError("Image file too large ( > 5MB )")
            
            # Check if it's an image
            if not profilepic.content_type.startswith('image/'):
                raise forms.ValidationError("Only image files are allowed.")
        
        return profilepic
    
class TeacherBatchAssignmentForm(forms.Form):
    teacher = forms.ModelChoiceField(
        queryset=tbl_teacher.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'teacher-select'
        }),
        label="Select Teacher",
        empty_label="--- Select Teacher ---",
        required=True
    )
    
    def __init__(self, stream=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if stream:
            # Filter teachers by department/stream
            self.fields['teacher'].queryset = tbl_teacher.objects.filter(
                department=stream
            ).order_by('firstname', 'lastname')