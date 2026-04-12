from django import forms
from .models import *
from adminapp.models import*

class EnrollmentForm(forms.Form):
    """Form for student to select batch for enrollment"""
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.none(),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        empty_label=None,
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id', None)
        super().__init__(*args, **kwargs)
        
        if course_id:
            # Only show OPEN batches for this course
            self.fields['batch'].queryset = Batch.objects.filter(
                course_id=course_id,
                status='Open'
            ).order_by('startdate')
            
        self.fields['batch'].label = "Select a Batch"
        self.fields['batch'].help_text = "Choose the batch you want to join"


class PaymentForm(forms.Form):
    """Payment details form - amount handled in view/template, not in model"""
    
    PAYMENT_MODE_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Digital Wallet'),
    ]
    
    # Card details
    card_number = forms.CharField(
        max_length=16,
        min_length=16,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456',
            'pattern': '[0-9]{16}',
            'maxlength': '16'
        }),
        required=True,
        label="Card Number"
    )
    
    card_holder = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Name on Card'
        }),
        required=True,
        label="Card Holder Name"
    )
    
    expiry_month = forms.ChoiceField(
        choices=[(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label="Expiry Month"
    )
    
    expiry_year = forms.ChoiceField(
        choices=[(str(i), str(i)) for i in range(2024, 2035)],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label="Expiry Year"
    )
    
    cvv = forms.CharField(
        max_length=3,
        min_length=3,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'pattern': '[0-9]{3}',
            'maxlength': '3'
        }),
        required=True,
        label="CVV"
    )
    
    payment_mode = forms.ChoiceField(
        choices=PAYMENT_MODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label="Payment Mode",
        initial='card'
    )
    
    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number')
        if card_number and not card_number.isdigit():
            raise forms.ValidationError("Card number should contain only digits")
        return card_number
    
    def clean_cvv(self):
        cvv = self.cleaned_data.get('cvv')
        if cvv and not cvv.isdigit():
            raise forms.ValidationError("CVV should contain only digits")
        return cvv
    
class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = tbl_assignmentstudent
        fields = ['assignmentuploaded']
        widgets = {
            'assignmentuploaded': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    # Add a comments field that's not in the model
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add any comments (optional)...'})
    )

class DoubtForm(forms.ModelForm):
    class Meta:
        model = tbl_doubt
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Type your doubt or question here...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].label = 'Your Question'