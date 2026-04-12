from django import forms
from .models import*
from adminapp.models import Batch
from datetime import datetime

class LessonForm(forms.ModelForm):
    class Meta:
        model = tbl_lessons
        fields = ['batch', 'modulenumber', 'moduletitle', 'lessontitle', 'pdfnotes', 'videos']
        widgets = {
            'batch': forms.Select(attrs={'class': 'form-control'}),
            'modulenumber': forms.NumberInput(attrs={'class': 'form-control'}),
            'moduletitle': forms.TextInput(attrs={'class': 'form-control'}),
            'lessontitle': forms.TextInput(attrs={'class': 'form-control'}),
            'pdfnotes': forms.FileInput(attrs={'class': 'form-control'}),
            'videos': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].queryset = Batch.objects.all()


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = tbl_assignment
        fields = ['batch', 'uploaddate', 'duedate', 'totalmarks', 'assignmentupload']
        widgets = {
            'batch': forms.Select(attrs={'class': 'form-control'}),
            'uploaddate': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'duedate': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'totalmarks': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '1000'
            }),
            'assignmentupload': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].queryset = Batch.objects.all()
        self.fields['assignmentupload'].required = False  # Make file upload optional
        
        # Set today's date as default for upload date
        self.fields['uploaddate'].initial = date.today()
    
    def clean_duedate(self):
        duedate = self.cleaned_data.get('duedate')
        uploaddate = self.cleaned_data.get('uploaddate')
        
        if duedate and uploaddate and duedate <= uploaddate:
            raise forms.ValidationError("Due date must be after upload date")
        return duedate
    
    def clean_assignmentupload(self):
        file = self.cleaned_data.get('assignmentupload')
        if file:
            # Check file size (limit to 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 10MB")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png']
            ext = file.name.lower()
            if not any(ext.endswith(allowed) for allowed in allowed_extensions):
                raise forms.ValidationError(f"Allowed file types: {', '.join(allowed_extensions)}")
        return file