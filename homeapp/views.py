from django.shortcuts import render
from django.shortcuts import render,redirect
from .forms import *
from .models import *
from adminapp.models import*
import hashlib 
from django.contrib import messages

def index(request):
    return render(request, 'index.html')


 # For password hashing

def studentregisters(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, request.FILES)
        print("Student form loaded")
        
        if form.is_valid():
            # Extract data from form
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phno = form.cleaned_data['phno']
            dob = form.cleaned_data['dob']
            gender = form.cleaned_data['gender']
            profile_pic = request.FILES.get('profile_pic')  # Get file from FILES
            educational_background = form.cleaned_data['educational_background']
            
            print(f"Student: {first_name} {last_name}")
            print(f"Email: {email}")
            print(f"Phone: {phno}")
            print(f"DOB: {dob}")
            print(f"Profile pic received: {'Yes' if profile_pic else 'No'}")
          
            
            # Create login record first
            usertype = "student"
            try:
                # Check if email already exists
                if tbl_Login.objects.filter(email=email).exists():
                    messages.error(request, "Email already registered!")
                    return render(request, 'studentreg.html', {'form': form})
                
                logindata = tbl_Login(
                    email=email, 
                    password=password, 
                    usertype=usertype
                )
                logindata.save()
                print("Login data saved")
                
                # Create student record
                student = tbl_Student(
                    first_name=first_name,
                    last_name=last_name,
                    phno=phno,
                    dob=dob,
                    gender=gender,
                    educational_background=educational_background,
                    login=logindata,
                    status="Active"
                )
                
                # Handle profile picture file upload
                if profile_pic:
                    student.profile_pic = profile_pic
                    print(f"Profile picture saved: {profile_pic.name}")
                
                student.save()
                print("Student saved successfully!")
                
                messages.success(request, "Student registration successful! Please login.")
                return redirect('student_login')  # Redirect to login page
                
            except Exception as e:
                print(f"Error saving data: {e}")
                print("Save failed")
                messages.error(request, f"Registration failed: {str(e)}")
                return render(request, 'studentreg.html', {'form': form})
                
        else:
            print("Form validation failed")
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
            return render(request, 'studentreg.html', {'form': form})
    
    else:
        # GET request - show empty form
        form = StudentRegistrationForm()
        return render(request, 'studentreg.html', {'form': form})
    
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            # Check if user exists with email and password
            if tbl_Login.objects.filter(email=email, password=password).exists():
                userdetail = tbl_Login.objects.get(email=email, password=password)
                
                # Store user info in session
                request.session['id'] = userdetail.id
                request.session['email'] = userdetail.email
                request.session['usertype'] = userdetail.usertype
                
                # Redirect based on keyuser from database
                if userdetail.usertype == 'admin':
                    return redirect('admindashboard')
                elif userdetail.usertype == 'teacher':
                    try:
                        teacher = tbl_teacher.objects.get(login=userdetail)
                        request.session['teacher_id'] = teacher.id
                        return redirect('teacherdashboard')
                    except tbl_teacher.DoesNotExist:
                        return render(request, 'login.html', {
                            'form': form,
                            'error': 'Teacher profile not found. Contact administrator.'
                        })
                elif userdetail.usertype == 'student':
                    studentdata=tbl_Student.objects.get(login=userdetail.id)
                    request.session['studentid']=studentdata.id
                    return redirect('student_home')
                else:
                    return render(request,'login.html')
            else:
                return render(request, 'login.html', {
                    'form': form,
                    'error': 'Invalid email or password'
                })
        else:
            # Form validation failed
            return render(request, 'login.html', {'form': form})
    
    else:
        # GET request - show empty form
        form = LoginForm()
        return render(request, 'login.html', {'form': form})
    
def logout_with_preloader(request):
    """Show preloader then logout"""
    return render(request, 'logout_confirm.html')
    

def logout_view(request):
    """Logout user and clear session data"""
    
    # Get user type before clearing session (for logging purposes)
    user_type = request.session.get('usertype', 'unknown')
    user_email = request.session.get('email', 'unknown')
    
    print(f"Logging out {user_type}: {user_email}")
    
    # Clear all session data
    request.session.flush()
    
    # Add success message
    messages.success(request, 'You have been successfully logged out!')
    
    # Redirect to login page
    return render(request, 'index.html')

def about(request):
    """About page view"""
    return render(request, 'about.html')

def contact(request):
    """Contact page view with form handling"""
    if request.method == 'POST':
        # Handle contact form submission here
        # You can save to database or send email
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Process the message (save to database, send email, etc.)
        
        messages.success(request, 'Thank you for contacting us! We will get back to you soon.')
        return redirect('contact')
    
    return render(request, 'contact.html')

def index(request):
    """Home page with dynamic courses and teachers"""
    
    # Get first 3 courses
    popular_courses = Course.objects.select_related('stream').all().order_by('-id')[:3]
    
    # Get all active teachers
    teachers = tbl_teacher.objects.all().select_related('department')[:4]  # Get first 4 teachers
    
    context = {
        'popular_courses': popular_courses,
        'teachers': teachers,
    }
    return render(request, 'index.html', context)