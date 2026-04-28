from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import*
from studentapp.models import*
from django.db.models import Count, Avg, Sum, Q
from datetime import date, timedelta
from django.utils import timezone
from .forms import*
from .models import Course, Batch
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST 
import json


from .models import tbl_teacher, tbl_Login, Stream
# Create your views here.
def loadadmindashboard(request):
    """Load admin dashboard with real data and charts"""
    
    # ===== STATS CARDS =====
    
    # Total Students
    total_students = tbl_Student.objects.filter(status='Active').count()
    
    # New students this month
    first_day_month = date.today().replace(day=1)
    new_students = tbl_Student.objects.filter(
        created_at__gte=first_day_month
    ).count()
    
    # Total Teachers
    total_teachers = tbl_teacher.objects.count()
    
    # Total Courses
    total_courses = Course.objects.count()
    
    # Total Batches
    total_batches = Batch.objects.count()
    
    # Active Enrollments
    active_enrollments = tbl_student_enrolment.objects.filter(
        is_active_student='yes',
        course_status='active'
    ).count()
    
    # Completed Courses
    completed_courses = tbl_student_enrolment.objects.filter(
        course_status='completed'
    ).count()
    
    # Pending Certificates (students who completed but no final mark)
    pending_certificates = tbl_student_enrolment.objects.filter(
        course_status='completed',
        is_active_student='yes'
    ).exclude(
        id__in=tbl_final.objects.values_list('student_enrolment_id', flat=True)
    ).count()
    
    # Total Revenue
    total_revenue = tbl_payment.objects.filter(
        paymentstatus='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Revenue this month
    monthly_revenue = tbl_payment.objects.filter(
        paymentstatus='completed',
        paymentdate__gte=first_day_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # ===== ENROLLMENT CHART DATA (Last 6 months) =====
    
    months = []
    enrollment_data = []
    today = date.today()
    
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30*i)
        month_name = month_date.strftime('%b')
        months.append(month_name)
        
        # Get first and last day of that month
        first_day = month_date.replace(day=1)
        if month_date.month == 12:
            last_day = month_date.replace(day=31)
        else:
            last_day = month_date.replace(month=month_date.month+1, day=1) - timedelta(days=1)
        
        # Count enrollments in that month
        month_enrollments = tbl_student_enrolment.objects.filter(
            enrollment_date__gte=first_day,
            enrollment_date__lte=last_day
        ).count()
        enrollment_data.append(month_enrollments)
    
    # ===== STREAM DISTRIBUTION CHART =====
    
    streams = Stream.objects.filter(status=1)
    stream_labels = []
    stream_data = []
    stream_colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#6f42c1', '#fd7e14', '#20c9a6']
    
    for stream in streams:
        stream_labels.append(stream.stream_name)
        # Count enrollments in this stream
        count = tbl_student_enrolment.objects.filter(
            enrolled_batchid__course__stream=stream,
            is_active_student='yes'
        ).count()
        stream_data.append(count)
    
    # ===== COURSE POPULARITY CHART =====
    
    popular_courses = Course.objects.annotate(
        student_count=Count('batch__tbl_student_enrolment')
    ).order_by('-student_count')[:5]
    
    course_labels = [c.coursename[:15] + '...' if len(c.coursename) > 15 else c.coursename for c in popular_courses]
    course_data = [c.student_count for c in popular_courses]
    
    # ===== RECENT ACTIVITIES =====
    
    recent_activities = []
    
    # Recent enrollments
    recent_enrollments = tbl_student_enrolment.objects.select_related(
        'studentid', 'enrolled_batchid__course'
    ).order_by('-enrollment_date')[:5]
    
    for enrollment in recent_enrollments:
        recent_activities.append({
            'time': enrollment.enrollment_date,
            'user': f"{enrollment.studentid.first_name} {enrollment.studentid.last_name}",
            'activity': f"Enrolled in {enrollment.enrolled_batchid.course.coursename}",
            'status': 'success',
            'status_text': 'Enrolled',
            'icon': 'fa-user-graduate'
        })
    
    # Recent payments
    recent_payments = tbl_payment.objects.select_related(
        'student_enrol_id__studentid',
        'student_enrol_id__enrolled_batchid__course'
    ).filter(paymentstatus='completed').order_by('-paymentdate')[:5]
    
    for payment in recent_payments:
        recent_activities.append({
            'time': payment.paymentdate,
            'user': f"{payment.student_enrol_id.studentid.first_name} {payment.student_enrol_id.studentid.last_name}",
            'activity': f"Paid ₹{payment.amount} for {payment.student_enrol_id.enrolled_batchid.course.coursename}",
            'status': 'info',
            'status_text': 'Payment',
            'icon': 'fa-credit-card'
        })
    
    # Recent completions
    recent_completions = tbl_student_enrolment.objects.filter(
        course_status='completed'
    ).select_related('studentid', 'enrolled_batchid__course').order_by('-enrollment_date')[:5]
    
    for completion in recent_completions:
        recent_activities.append({
            'time': completion.enrollment_date,
            'user': f"{completion.studentid.first_name} {completion.studentid.last_name}",
            'activity': f"Completed {completion.enrolled_batchid.course.coursename}",
            'status': 'success',
            'status_text': 'Completed',
            'icon': 'fa-check-circle'
        })
    
    # Sort activities by time (newest first)
    recent_activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = recent_activities[:10]  # Keep only 10 most recent
    
    # Format time for display
    for activity in recent_activities:
        if isinstance(activity['time'], date):
            if activity['time'] == date.today():
                activity['time_display'] = 'Today'
            elif activity['time'] == date.today() - timedelta(days=1):
                activity['time_display'] = 'Yesterday'
            else:
                activity['time_display'] = activity['time'].strftime('%d %b')
    
    # ===== TOP PERFORMING STUDENTS =====
    
    top_students = tbl_final.objects.select_related(
        'student_enrolment_id__studentid',
        'student_enrolment_id__enrolled_batchid__course'
    ).order_by('-final_mark')[:5]
    
    # ===== RECENT REVIEWS =====
    
    recent_reviews = tbl_course_review.objects.select_related(
        'student', 'course', 'batch'
    ).filter(is_approved=False).order_by('-created_at')[:5]
    
    # ===== BATCH STATUS =====
    
    open_batches = Batch.objects.filter(status='Open').count()
    ongoing_batches = Batch.objects.filter(status='Ongoing').count()
    completed_batches = Batch.objects.filter(status='Completed').count()
    
    context = {
        # Stats
        'total_students': total_students,
        'new_students': new_students,
        'total_teachers': total_teachers,
        'total_courses': total_courses,
        'total_batches': total_batches,
        'active_enrollments': active_enrollments,
        'completed_courses': completed_courses,
        'pending_certificates': pending_certificates,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        
        # Chart Data
        'months': json.dumps(months),
        'enrollment_data': json.dumps(enrollment_data),
        'stream_labels': json.dumps(stream_labels),
        'stream_data': json.dumps(stream_data),
        'stream_colors': json.dumps(stream_colors[:len(stream_labels)]),
        'course_labels': json.dumps(course_labels),
        'course_data': json.dumps(course_data),
        
        # Activities
        'recent_activities': recent_activities,
        'top_students': top_students,
        'recent_reviews': recent_reviews,
        
        # Batch Stats
        'open_batches': open_batches,
        'ongoing_batches': ongoing_batches,
        'completed_batches': completed_batches,
    }
    
    return render(request, 'adminhome.html', context)



def manage_streams(request):
    """Display all streams with add/edit/delete functionality"""
    streams = Stream.objects.all().order_by('stream_name')
    
    # Handle add form submission
    if request.method == 'POST' and 'add_form' in request.POST:
        add_form = StreamForm(request.POST)
        if add_form.is_valid():
            stream = add_form.save(commit=False)
            # Ensure status is set to active (1) for new streams
            if not stream.pk:  # New stream
                stream.status = 1
            stream.save()
            messages.success(request, f'Stream "{stream.stream_name}" added successfully!')
            return redirect('manage_streams')
        else:
            # If form is invalid, show errors
            for field, errors in add_form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        add_form = StreamForm()
    
    # Prepare context
    context = {
        'streams': streams,
        'add_form': add_form,
    }
    return render(request, 'stream_management.html', context)


def edit_stream(request, stream_id):
    """Handle stream editing via modal form"""
    stream = get_object_or_404(Stream, id=stream_id)
    
    if request.method == 'POST':
        # Create form with instance for editing
        form = StreamForm(request.POST, instance=stream)
        if form.is_valid():
            updated_stream = form.save()
            messages.success(request, f'Stream "{updated_stream.stream_name}" updated successfully!')
            return redirect('manage_streams')
        else:
            # If form is invalid, show error message
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return redirect('manage_streams')

def delete_stream(request, stream_id):
    """Handle stream deletion"""
    stream = get_object_or_404(Stream, id=stream_id)
    
    if request.method == 'POST':
        stream_name = stream.stream_name
        stream.delete()
        messages.success(request, f'Stream "{stream_name}" deleted successfully!')
    
    return redirect('manage_streams')


def manage_courses(request):
    """Display all courses with CRUD functionality"""
    courses = Course.objects.all().order_by('coursename')
    streams = Stream.objects.filter(status=1)  # Only active streams
    
    # Handle add form submission
    if request.method == 'POST' and 'add_course' in request.POST:
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Course "{course.coursename}" added successfully!')
            return redirect('manage_courses')
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CourseForm()
    
    context = {
        'courses': courses,
        'streams': streams,
        'form': form,
    }
    return render(request, 'course_management.html', context)


def add_course(request):
    """Add new course - separate view for POST only"""
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Course "{course.coursename}" added successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('manage_courses')

def edit_course(request, course_id):
    """Handle course editing"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            updated_course = form.save()
            messages.success(request, f'Course "{updated_course.coursename}" updated successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('manage_courses')


def delete_course(request, course_id):
    """Handle course deletion"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        course_name = course.coursename
        course.delete()
        messages.success(request, f'Course "{course_name}" deleted successfully!')
    
    return redirect('manage_courses')


def get_courses_by_stream(request):
    """AJAX endpoint to get courses by stream (for dropdowns)"""
    stream_id = request.GET.get('stream_id')
    
    if stream_id:
        courses = Course.objects.filter(stream_id=stream_id).order_by('coursename')
        courses_data = [{'id': course.id, 'name': course.coursename} for course in courses]
    else:
        courses_data = []
    
    return JsonResponse({'courses': courses_data})


def course_detail(request, course_id):
    """View individual course details"""
    course = get_object_or_404(Course, id=course_id)
    
    context = {
        'course': course,
    }
    return render(request, 'course_detail.html', context)


def manage_batches(request):
    """Display all batches with CRUD functionality"""
    # Get all batches with related course data - INCLUDES new fields
    batches = Batch.objects.all().select_related('course__stream').order_by('-id')
    courses = Course.objects.all().select_related('stream').order_by('coursename')
    
    # Handle add form submission
    if request.method == 'POST' and 'add_batch' in request.POST:
        form = BatchForm(request.POST)
        if form.is_valid():
            batch = form.save()  # Saves batchcode, batchname, course, startdate, status
            messages.success(request, f'Batch "{batch.batchname}" added successfully!')
            return redirect('manage_batches')
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = BatchForm()
    
    context = {
        'batches': batches,
        'courses': courses,
        'form': form,
    }
    return render(request, 'batch_management.html', context)


def add_batch(request):
    """Add new batch - separate view for POST only"""
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            batch = form.save()  # Saves all fields including startdate and status
            messages.success(request, f'Batch "{batch.batchname}" added successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('manage_batches')


def edit_batch(request, batch_id):
    """Handle batch editing"""
    batch = get_object_or_404(Batch, id=batch_id)
    
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            updated_batch = form.save()  # Updates all fields including startdate and status
            messages.success(request, f'Batch "{updated_batch.batchname}" updated successfully!')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('manage_batches')


def delete_batch(request, batch_id):
    """Handle batch deletion"""
    batch = get_object_or_404(Batch, id=batch_id)
    
    if request.method == 'POST':
        batch_name = batch.batchname
        batch.delete()
        messages.success(request, f'Batch "{batch_name}" deleted successfully!')
    
    return redirect('manage_batches')


def batch_detail(request, batch_id):
    """View individual batch details"""
    # Get batch with related course and stream data
    batch = get_object_or_404(
        Batch.objects.select_related('course__stream'), 
        id=batch_id
    )
    
    context = {
        'batch': batch,
    }
    return render(request, 'batch_detail.html', context)


def get_batches_by_course(request):
    """AJAX endpoint to get batches by course"""
    course_id = request.GET.get('course_id')
    
    if course_id:
        batches = Batch.objects.filter(course_id=course_id).order_by('batchcode')
        batches_data = [{'id': batch.id, 'code': batch.batchcode, 'name': batch.batchname} for batch in batches]
    else:
        batches_data = []
    
    return JsonResponse({'batches': batches_data})




def manage_teachers(request):
    """Display all teachers and handle teacher management"""
    teachers = tbl_teacher.objects.all().order_by('-id')
    streams = Stream.objects.filter(status=1)
    
    # Handle add form submission
    if request.method == 'POST' and 'add_teacher' in request.POST:
        form = TeacherRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Create login credentials first
                email = form.cleaned_data['email']
                password = form.cleaned_data['password']
                
                login_obj = tbl_Login.objects.create(
                    email=email,
                    password=password,
                    usertype='teacher'
                )
                
                # Create teacher with login reference
                teacher = form.save(commit=False)
                teacher.login = login_obj
                teacher.save()
                
                messages.success(request, f'Teacher {teacher.firstname} {teacher.lastname} added successfully!')
                return redirect('manage_teachers')
                
            except Exception as e:
                messages.error(request, f'Error adding teacher: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = TeacherRegistrationForm()
    
    context = {
        'teachers': teachers,
        'streams': streams,
        'form': form,
        'total_teachers': teachers.count(),
        'active_streams': streams.count(),
    }
    return render(request, 'teacher_management.html', context)

def view_teacher(request, teacher_id):
    """View teacher details"""
    teacher = get_object_or_404(tbl_teacher, id=teacher_id)
    
    context = {
        'teacher': teacher,
    }
    return render(request, 'teacher_view.html', context)

def edit_teacher(request, teacher_id):
    """Edit teacher details"""
    teacher = get_object_or_404(tbl_teacher, id=teacher_id)
    
    if request.method == 'POST':
        # Handle teacher update
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        qualification = request.POST.get('qualification')
        specialization = request.POST.get('specialization')
        experienceyear = request.POST.get('experienceyear')
        department_id = request.POST.get('department')
        
        if firstname and lastname and department_id:
            try:
                teacher.firstname = firstname
                teacher.lastname = lastname
                teacher.qualification = qualification
                teacher.specialization = specialization
                teacher.experienceyear = experienceyear
                teacher.department = Stream.objects.get(id=department_id)
                
                # Handle file uploads
                if 'bio' in request.FILES:
                    teacher.bio = request.FILES['bio']
                if 'profilepic' in request.FILES:
                    teacher.profilepic = request.FILES['profilepic']
                
                teacher.save()
                messages.success(request, f'Teacher {teacher.firstname} {teacher.lastname} updated successfully!')
            except Exception as e:
                messages.error(request, f'Error updating teacher: {str(e)}')
        else:
            messages.error(request, 'Please fill all required fields.')
    
    return redirect('manage_teachers')

def delete_teacher(request, teacher_id):
    """Delete teacher and associated login"""
    if request.method == 'POST':
        teacher = get_object_or_404(tbl_teacher, id=teacher_id)
        teacher_name = f"{teacher.firstname} {teacher.lastname}"
        
        try:
            # Delete associated login
            if teacher.login:
                teacher.login.delete()
            
            # Delete teacher
            teacher.delete()
            
            messages.success(request, f'Teacher {teacher_name} deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting teacher: {str(e)}')
    
    return redirect('manage_teachers')




def manage_teacher_batches(request):
    """Display batches with assigned teachers and manage assignments"""
    
    # Get all batches with their course and stream info
    batches = Batch.objects.all().select_related(
        'course', 
        'course__stream'
    ).order_by('course__stream__stream_name', 'batchname')
    
    # Get all teacher-batch assignments
    assignments = tbl_teacherbatch.objects.all().select_related(
        'teacher',
        'teacher__department',
        'batch',
        'batch__course'
    )
    
    # Create a list of batches with their assigned teachers
    batch_list = []
    for batch in batches:
        batch_teachers = []
        for assignment in assignments:
            if assignment.batch_id == batch.id:
                batch_teachers.append({
                    'teacher': assignment.teacher,
                    'assignment_id': assignment.id
                })
        
        batch_list.append({
            'batch': batch,
            'teachers': batch_teachers,
            'teacher_count': len(batch_teachers)
        })
    
    # Get all streams for filter
    streams = Stream.objects.filter(status=1).order_by('stream_name')
    
    # Calculate statistics
    total_batches = len(batch_list)
    total_assignments = assignments.count()
    assigned_batches_count = sum(1 for item in batch_list if item['teacher_count'] > 0)
    unassigned_batches = total_batches - assigned_batches_count
    teachers_count = tbl_teacher.objects.count()
    
    # Handle assignment (same as before)
    if request.method == 'POST':
        if 'assign_teacher' in request.POST:
            batch_id = request.POST.get('batch_id')
            teacher_id = request.POST.get('teacher')
            
            if batch_id and teacher_id:
                batch = get_object_or_404(Batch, id=batch_id)
                teacher = get_object_or_404(tbl_teacher, id=teacher_id)
                
                # Check if teacher is already assigned to this batch
                if tbl_teacherbatch.objects.filter(batch=batch, teacher=teacher).exists():
                    messages.warning(request, f'{teacher.firstname} {teacher.lastname} is already assigned to {batch.batchname}')
                else:
                    # Create new assignment
                    assignment = tbl_teacherbatch.objects.create(
                        batch=batch,
                        teacher=teacher
                    )
                    messages.success(request, f'Successfully assigned {teacher.firstname} {teacher.lastname} to {batch.batchname}')
                
                return redirect('manage_teacher_batches')
        
        elif 'remove_assignment' in request.POST:
            assignment_id = request.POST.get('assignment_id')
            if assignment_id:
                assignment = get_object_or_404(tbl_teacherbatch, id=assignment_id)
                teacher_name = f"{assignment.teacher.firstname} {assignment.teacher.lastname}"
                batch_name = assignment.batch.batchname
                assignment.delete()
                messages.success(request, f'Removed {teacher_name} from {batch_name}')
                return redirect('manage_teacher_batches')
    
    context = {
        'batch_list': batch_list,  # Simple list instead of dictionary
        'streams': streams,
        'total_batches': total_batches,
        'total_assignments': total_assignments,
        'unassigned_batches': unassigned_batches,
        'teachers_count': teachers_count,
        'assigned_batches_count': assigned_batches_count,
    }
    
    return render(request, 'teacher_batch_management.html', context)

def get_teachers_by_stream(request):
    """Get teachers by stream for AJAX request"""
    stream_id = request.GET.get('stream_id')
    if stream_id:
        teachers = tbl_teacher.objects.filter(department_id=stream_id).order_by('firstname', 'lastname')
        teachers_data = [
            {
                'id': teacher.id,
                'name': f"{teacher.firstname} {teacher.lastname}",
                'qualification': teacher.qualification,
                'experience': teacher.experienceyear
            }
            for teacher in teachers
        ]
        return JsonResponse({'teachers': teachers_data})
    return JsonResponse({'teachers': []})

def replace_teacher_assignment(request, batch_id):
    """Replace teacher assignment for a batch"""
    batch = get_object_or_404(Batch, id=batch_id)
    
    if request.method == 'POST':
        old_teacher_id = request.POST.get('old_teacher_id')
        new_teacher_id = request.POST.get('new_teacher_id')
        
        if old_teacher_id and new_teacher_id:
            # Remove old assignment
            tbl_teacherbatch.objects.filter(
                batch=batch, 
                teacher_id=old_teacher_id
            ).delete()
            
            # Create new assignment
            tbl_teacherbatch.objects.create(
                batch=batch,
                teacher_id=new_teacher_id
            )
            
            messages.success(request, 'Teacher assignment updated successfully!')
    
    return redirect('manage_teacher_batches')

def exam_management(request):
    """Main exam management page"""
    streams = Stream.objects.all()
    courses = Course.objects.all()
    exams_list = exam.objects.select_related('courseid__stream').all()
    
    context = {
        'streams': streams,
        'courses': courses,
        'exams': exams_list,
    }
    return render(request, 'exam_management.html', context)

def create_exam(request):
    """Create a new exam"""
    if request.method == 'POST':
        try:
            course_id = request.POST.get('course_id')
            exam_code = request.POST.get('exam_code')
            total_score = request.POST.get('total_score')
            duration = request.POST.get('duration')
            
            # Check if exam code already exists
            if exam.objects.filter(examcode=exam_code).exists():
                messages.error(request, 'Exam code already exists!')
                return redirect('exam_management')
            
            course = get_object_or_404(Course, id=course_id)
            
            exam.objects.create(
                courseid=course,
                totalscore=total_score,
                examcode=exam_code,
                duration=duration
            )
            
            messages.success(request, 'Exam created successfully!')
            return redirect('exam_management')
        except Exception as e:
            messages.error(request, f'Error creating exam: {str(e)}')
            return redirect('exam_management')
    return redirect('exam_management')

def get_exam_questions(request):
    """Get all questions for an exam"""
    exam_id = request.GET.get('exam_id')
    exam_obj = get_object_or_404(exam, id=exam_id)
    
    questions = []
    exam_questions = tbl_examquestion.objects.filter(
        examid=exam_obj
    ).select_related('questionid')
    
    for eq in exam_questions:
        question = eq.questionid
        options = tbl_option.objects.filter(questionid=question)
        
        questions.append({
            'id': question.id,
            'question_text': question.question,
            'options': [
                {
                    'option_text': opt.option,
                    'is_correct': opt.answerstatus
                }
                for opt in options
            ]
        })
    
    return JsonResponse({'success': True, 'questions': questions})

def get_question_details(request):
    """Get details of a specific question"""
    question_id = request.GET.get('question_id')
    exam_id = request.GET.get('exam_id')
    
    question = get_object_or_404(tbl_question, id=question_id)
    options = tbl_option.objects.filter(questionid=question)
    
    data = {
        'question_text': question.question,
        'options': [
            {
                'option_text': opt.option,
                'is_correct': opt.answerstatus
            }
            for opt in options
        ]
    }
    
    return JsonResponse({'success': True, **data})

@csrf_exempt
@require_POST
def add_question(request):
    """Add a new question to an exam"""
    try:
        exam_id = request.POST.get('exam_id')
        question_text = request.POST.get('question').strip()
        options = request.POST.getlist('options[]')
        correct_option = int(request.POST.get('correct_option', 0))
        
        exam_obj = get_object_or_404(exam, id=exam_id)
        
        # Check if question already exists in this exam
        existing_questions = tbl_examquestion.objects.filter(
            examid=exam_obj
        ).select_related('questionid')
        
        for eq in existing_questions:
            if eq.questionid.question.lower() == question_text.lower():
                return JsonResponse({
                    'success': False, 
                    'error': 'This question already exists in this exam!'
                })
        
        # Create question
        new_question = tbl_question.objects.create(question=question_text)
        
        # Create options - ensure only one is marked as correct
        for i, option_text in enumerate(options):
            is_correct = (i == correct_option)
            tbl_option.objects.create(
                questionid=new_question,
                option=option_text.strip(),
                answerstatus=is_correct
            )
        
        # Link question to exam
        tbl_examquestion.objects.create(
            questionid=new_question,
            examid=exam_obj
        )
        
        return JsonResponse({'success': True, 'question_id': new_question.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def update_question(request):
    """Update an existing question"""
    try:
        question_id = request.POST.get('question_id')
        exam_id = request.POST.get('exam_id')
        question_text = request.POST.get('question').strip()
        options_data = json.loads(request.POST.get('options', '[]'))
        correct_index = int(request.POST.get('correct_index', 0))
        
        # Get question
        question = get_object_or_404(tbl_question, id=question_id)
        
        # Check if updated question text already exists in this exam (excluding current question)
        exam_obj = get_object_or_404(exam, id=exam_id)
        existing_questions = tbl_examquestion.objects.filter(
            examid=exam_obj
        ).exclude(questionid=question).select_related('questionid')
        
        for eq in existing_questions:
            if eq.questionid.question.lower() == question_text.lower():
                return JsonResponse({
                    'success': False, 
                    'error': 'This question already exists in this exam!'
                })
        
        question.question = question_text
        question.save()
        
        # Delete existing options
        tbl_option.objects.filter(questionid=question).delete()
        
        # Create new options - ensure only one is marked as correct
        for i, option_data in enumerate(options_data):
            is_correct = (i == correct_index)
            tbl_option.objects.create(
                questionid=question,
                option=option_data['text'].strip(),
                answerstatus=is_correct
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def delete_question(request):
    """Delete a question"""
    try:
        question_id = request.POST.get('question_id')
        exam_id = request.POST.get('exam_id')
        
        # Get the exam-question link
        exam_obj = get_object_or_404(exam, id=exam_id)
        question = get_object_or_404(tbl_question, id=question_id)
        
        # Delete the link
        tbl_examquestion.objects.filter(
            questionid=question,
            examid=exam_obj
        ).delete()
        
        # Also delete the question and its options if not used in other exams
        other_links = tbl_examquestion.objects.filter(questionid=question).count()
        if other_links == 0:
            question.delete()  # This will cascade delete options
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def delete_exam(request):
    """Delete an exam"""
    try:
        exam_id = request.POST.get('exam_id')
        exam_obj = get_object_or_404(exam, id=exam_id)
        
        # Get all questions linked to this exam
        exam_questions = tbl_examquestion.objects.filter(examid=exam_obj)
        question_ids = exam_questions.values_list('questionid', flat=True)
        
        # Delete exam-question links
        exam_questions.delete()
        
        # Delete questions that are not linked to any other exams
        for qid in question_ids:
            if not tbl_examquestion.objects.filter(questionid_id=qid).exists():
                tbl_question.objects.filter(id=qid).delete()
        
        # Delete the exam
        exam_obj.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    

    # 

def manage_students(request):
    """Display all enrolled students with basic information"""
    # Get filter parameters - handle them properly
    course_id = request.GET.get('course', '')
    batch_id = request.GET.get('batch', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset - get all active enrollments with related data
    enrollments = tbl_student_enrolment.objects.filter(
        is_active_student='yes'
    ).select_related(
        'studentid',
        'studentid__login',
        'enrolled_batchid',
        'enrolled_batchid__course',
        'enrolled_batchid__course__stream'
    ).order_by('-enrollment_date')
    
    # Debug prints (remove in production)
    print(f"Course ID: {course_id}")
    print(f"Batch ID: {batch_id}")
    print(f"Status: {status_filter}")
    print(f"Search: {search_query}")
    
    # Apply filters only if they have values
    if course_id and course_id.strip():
        enrollments = enrollments.filter(enrolled_batchid__course_id=course_id)
        print(f"Applied course filter: {course_id}")
    
    if batch_id and batch_id.strip():
        enrollments = enrollments.filter(enrolled_batchid_id=batch_id)
        print(f"Applied batch filter: {batch_id}")
    
    if status_filter and status_filter.strip():
        if status_filter == 'ongoing':
            enrollments = enrollments.filter(course_status='active')
            print("Applied ongoing filter")
        elif status_filter == 'completed':
            enrollments = enrollments.filter(course_status='completed')
            print("Applied completed filter")
    
    if search_query and search_query.strip():
        enrollments = enrollments.filter(
            Q(studentid__first_name__icontains=search_query) |
            Q(studentid__last_name__icontains=search_query) |
            Q(studentid__login__email__icontains=search_query) |
            Q(studentid__phno__icontains=search_query)
        )
        print(f"Applied search filter: {search_query}")
    
    # Calculate progress for each enrollment
    for enrollment in enrollments:
        from teacherapp.models import tbl_lessons, tbl_assignment
        
        total_lessons = tbl_lessons.objects.filter(batch=enrollment.enrolled_batchid).count()
        total_assignments = tbl_assignment.objects.filter(batch=enrollment.enrolled_batchid).count()
        
        submitted_assignments = tbl_assignmentstudent.objects.filter(
            student=enrollment.studentid,
            assignment__batch=enrollment.enrolled_batchid
        ).count()
        
        total_items = total_lessons + total_assignments
        completed_items = submitted_assignments
        
        if total_items > 0:
            enrollment.progress = int((completed_items / total_items) * 100)
        else:
            enrollment.progress = 0
        
        enrollment.status_display = 'Completed' if enrollment.course_status == 'completed' else 'Ongoing'
    
    # Get filter data
    courses = Course.objects.all()
    batches = Batch.objects.all()
    
    # Statistics
    total_students = tbl_Student.objects.filter(status='Active').count()
    active_enrollments = tbl_student_enrolment.objects.filter(is_active_student='yes').count()
    completed_courses = tbl_student_enrolment.objects.filter(course_status='completed').count()
    
    context = {
        'enrollments': enrollments,
        'courses': courses,
        'batches': batches,
        'total_students': total_students,
        'active_enrollments': active_enrollments,
        'completed_courses': completed_courses,
        'selected_course': course_id,
        'selected_batch': batch_id,
        'selected_status': status_filter,
        'search_query': search_query,
    }
    return render(request, 'admin_manage_students.html', context)


def student_detail(request, student_id):
    """Display detailed information about a specific student"""
    # Get student basic info
    student = get_object_or_404(
        tbl_Student.objects.select_related('login'),
        id=student_id
    )
    
    # Get all enrollments for this student
    enrollments = tbl_student_enrolment.objects.filter(
        studentid=student,
        is_active_student='yes'
    ).select_related(
        'enrolled_batchid',
        'enrolled_batchid__course',
        'enrolled_batchid__course__stream'
    ).order_by('-enrollment_date')
    
    # Fixed enrollment amount (as per your requirement)
    ENROLLMENT_FEE = 1000
    
    # Initialize payment summary variables
    total_paid = 0
    total_pending = 0
    completed_payments = 0
    pending_payments = 0
    
    # Get payment details for each enrollment and calculate summaries
    for enrollment in enrollments:
        # Get all payments for this enrollment
        enrollment_payments = tbl_payment.objects.filter(
            student_enrol_id=enrollment
        ).order_by('-paymentdate')
        
        enrollment.payments = enrollment_payments
        
        # Calculate total paid for this enrollment
        enrollment.total_paid = float(enrollment_payments.filter(
            paymentstatus='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0)
        
        # Get course total amount (as float)
        course = enrollment.enrolled_batchid.course
        enrollment.course_total = float(course.rate)
        
        # Calculate pending amount for this enrollment
        enrollment.pending_amount = max(0, enrollment.course_total - enrollment.total_paid)
        
        # Determine if fully paid
        enrollment.is_fully_paid = enrollment.pending_amount <= 0.01
        
        # Get latest payment for display
        enrollment.latest_payment = enrollment_payments.first()
        
        # Add to overall totals
        total_paid += enrollment.total_paid
        total_pending += enrollment.pending_amount
        
        # Count payment statuses
        completed_payments += enrollment_payments.filter(paymentstatus='completed').count()
        pending_payments += enrollment_payments.filter(paymentstatus='pending').count()
        
        # Calculate progress for this course
        from teacherapp.models import tbl_lessons, tbl_assignment
        
        total_lessons = tbl_lessons.objects.filter(batch=enrollment.enrolled_batchid).count()
        total_assignments = tbl_assignment.objects.filter(batch=enrollment.enrolled_batchid).count()
        
        submitted_assignments = tbl_assignmentstudent.objects.filter(
            student=student,
            assignment__batch=enrollment.enrolled_batchid
        ).count()
        
        total_items = total_lessons + total_assignments
        completed_items = submitted_assignments
        
        if total_items > 0:
            enrollment.progress = int((completed_items / total_items) * 100)
        else:
            enrollment.progress = 0
        
        # Get assignment scores
        assignment_scores = tbl_assignmentstudent.objects.filter(
            student=student,
            assignment__batch=enrollment.enrolled_batchid,
            assigned_marks__isnull=False
        ).values_list('assigned_marks', flat=True)
        
        if assignment_scores:
            enrollment.avg_score = float(sum(assignment_scores)) / len(assignment_scores)
        else:
            enrollment.avg_score = 0
        
        # ===== NEW CODE: Calculate quiz average from exam results =====
        # Get all exam results for this enrollment
        exam_results = tbl_student_examresult.objects.filter(
            student_enrol_id=enrollment
        ).select_related('examid')
        
        if exam_results.exists():
            total_percentage = 0
            exam_count = 0
            
            for result in exam_results:
                # Get the exam's total score
                exam_total = result.examid.totalscore
                if exam_total and exam_total > 0:
                    # Calculate percentage for this exam
                    percentage = (result.total_score_obtained / exam_total) * 100
                    total_percentage += percentage
                    exam_count += 1
            
            # Calculate average percentage
            if exam_count > 0:
                enrollment.quiz_avg = total_percentage / exam_count
            else:
                enrollment.quiz_avg = None
        else:
            enrollment.quiz_avg = None
        # ===== END OF NEW CODE =====
    
    # Get all payments for history
    payments = tbl_payment.objects.filter(
        student_enrol_id__studentid=student
    ).select_related('student_enrol_id__enrolled_batchid__course').order_by('-paymentdate')
    
    # Get recent activity (last 30 days)
    from django.utils import timezone
    from datetime import timedelta
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    recent_submissions = tbl_assignmentstudent.objects.filter(
        student=student,
        submitteddate__gte=thirty_days_ago
    ).count()
    
    recent_doubts = tbl_doubt.objects.filter(
        student_enrolment_id__studentid=student,
        date_submitted__gte=thirty_days_ago
    ).count()
    
    # Get last login
    last_login = student.login.last_login if hasattr(student.login, 'last_login') else None
    
    # Format totals as float
    total_paid = float(total_paid)
    total_pending = float(total_pending)
    
    context = {
        'student': student,
        'enrollments': enrollments,
        'payments': payments,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'completed_payments': completed_payments,
        'pending_payments': pending_payments,
        'recent_submissions': recent_submissions,
        'recent_doubts': recent_doubts,
        'last_login': last_login,
        'registration_date': student.created_at,
        'enrollment_fee': ENROLLMENT_FEE,
    }
    return render(request, 'student_detail.html', context)

def student_payments(request, student_id):
    """View all payments for a student"""
    student = get_object_or_404(tbl_Student, id=student_id)
    
    payments = tbl_payment.objects.filter(
        student_enrol_id__studentid=student
    ).select_related(
        'student_enrol_id__enrolled_batchid__course'
    ).order_by('-paymentdate')
    
    # Payment statistics
    total_paid = payments.filter(paymentstatus='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_payments = payments.filter(paymentstatus='pending').count()
    completed_payments = payments.filter(paymentstatus='completed').count()
    
    context = {
        'student': student,
        'payments': payments,
        'total_paid': total_paid,
        'pending_payments': pending_payments,
        'completed_payments': completed_payments,
    }
    return render(request, 'student_payments.html', context)


def student_progress(request, student_id, enrollment_id):
    """Detailed progress for a specific course enrollment"""
    student = get_object_or_404(tbl_Student, id=student_id)
    enrollment = get_object_or_404(
        tbl_student_enrolment,
        id=enrollment_id,
        studentid=student
    )
    
    from teacherapp.models import tbl_lessons, tbl_assignment
    
    # Get all lessons for this batch
    lessons = tbl_lessons.objects.filter(batch=enrollment.enrolled_batchid).order_by('modulenumber')
    
    # Get all assignments for this batch
    assignments = tbl_assignment.objects.filter(batch=enrollment.enrolled_batchid).order_by('-uploaddate')
    
    # Get submissions
    submissions = tbl_assignmentstudent.objects.filter(
        student=student,
        assignment__in=assignments
    ).select_related('assignment')
    
    submission_dict = {s.assignment_id: s for s in submissions}
    
    # Calculate statistics
    total_assignments = assignments.count()
    submitted_count = submissions.count()
    graded_count = submissions.filter(assigned_marks__isnull=False).count()
    
    if graded_count > 0:
        avg_score = submissions.filter(assigned_marks__isnull=False).aggregate(Avg('assigned_marks'))['assigned_marks__avg']
    else:
        avg_score = 0
    
    context = {
        'student': student,
        'enrollment': enrollment,
        'lessons': lessons,
        'assignments': assignments,
        'submission_dict': submission_dict,
        'total_assignments': total_assignments,
        'submitted_count': submitted_count,
        'graded_count': graded_count,
        'avg_score': avg_score,
    }
    return render(request, 'student_progress.html', context)


def export_students_csv(request):
    """Export student data to CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student ID', 'Full Name', 'Email', 'Phone', 'Gender',
        'Course', 'Batch', 'Enrollment Date', 'Status', 'Progress %'
    ])
    
    enrollments = tbl_student_enrolment.objects.filter(
        is_active_student='yes'
    ).select_related(
        'studentid',
        'enrolled_batchid',
        'enrolled_batchid__course'
    )
    
    for enrollment in enrollments:
        writer.writerow([
            enrollment.studentid.id,
            f"{enrollment.studentid.first_name} {enrollment.studentid.last_name}",
            enrollment.studentid.email,
            enrollment.studentid.phno,
            enrollment.studentid.gender,
            enrollment.enrolled_batchid.course.coursename,
            enrollment.enrolled_batchid.batchname,
            enrollment.enrollment_date,
            enrollment.course_status,
            '0'  # Progress calculation would go here
        ])
    
    return response

from django.http import HttpResponse
from reportlab.pdfgen import canvas




from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics import renderPDF
from django.db.models import Sum
from datetime import datetime

def export_report_pdf(request):

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="NovaLearn_Report.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # =====================================
    # COLORS
    # =====================================
    pink = colors.HexColor("#E91E63")
    soft_pink = colors.HexColor("#FCE4EC")
    dark = colors.HexColor("#222222")
    silver = colors.HexColor("#B0B0B0")

    # =====================================
    # BORDER FRAME
    # =====================================
    p.setStrokeColor(pink)
    p.setLineWidth(3)
    p.rect(15, 15, width-30, height-30)

    p.setStrokeColor(silver)
    p.setLineWidth(1)
    p.rect(25, 25, width-50, height-50)

    # =====================================
    # HEADER BADGE / LOGO
    # =====================================
    p.setFillColor(pink)
    p.circle(width/2, height-80, 28, fill=1)

    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width/2, height-88, "N")

    # =====================================
    # TITLE
    # =====================================
    p.setFillColor(dark)
    p.setFont("Helvetica-Bold", 26)
    p.drawCentredString(width/2, height-140, "NovaLearn")

    p.setFont("Helvetica", 18)
    p.drawCentredString(width/2, height-165, "Analytics Report")

    # Tagline
    p.setFillColor(colors.grey)
    p.setFont("Helvetica-Oblique", 11)
    p.drawCentredString(
        width/2,
        height-185,
        "Professional Academic Performance Summary"
    )

    # =====================================
    # DATE
    # =====================================
    p.setFillColor(dark)
    p.setFont("Helvetica", 10)
    p.drawCentredString(
        width/2,
        height-210,
        f"Generated on {datetime.now().strftime('%d %B %Y, %I:%M %p')}"
    )

    # =====================================
    # FETCH DATA
    # =====================================
    total_students = tbl_Student.objects.count()
    total_teachers = tbl_teacher.objects.count()
    total_courses = Course.objects.count()
    total_batches = Batch.objects.count()
    total_enrollments = tbl_student_enrolment.objects.count()

    total_revenue = tbl_payment.objects.aggregate(
        total=Sum("amount")
    )["total"] or 0

    pass_count = tbl_final.objects.filter(final_mark__gte=40).count()
    fail_count = tbl_final.objects.filter(final_mark__lt=40).count()

    # =====================================
    # METRIC BOXES
    # =====================================
    y = height - 290

    data = [
        ("Total Students", total_students),
        ("Total Teachers", total_teachers),
        ("Total Courses", total_courses),
        ("Total Revenue", f"₹ {total_revenue}"),
        ("Total Enrollments", total_enrollments),
        ("Passed Students", pass_count),
        ("Failed Students", fail_count),
        ("Total Batches", total_batches),
    ]

    x_positions = [45, 300]
    row = 0

    for i in range(len(data)):

        x = x_positions[i % 2]

        if i % 2 == 0 and i != 0:
            row += 1

        box_y = y - (row * 55)

        # box
        p.setFillColor(soft_pink)
        p.roundRect(x, box_y, 220, 40, 8, fill=1, stroke=0)

        # label
        p.setFillColor(dark)
        p.setFont("Helvetica", 10)
        p.drawString(x+10, box_y+24, data[i][0])

        # value
        p.setFont("Helvetica-Bold", 12)
        p.drawRightString(x+205, box_y+24, str(data[i][1]))

    # =====================================
    # FOOTER CERTIFICATE STYLE
    # =====================================
    p.setStrokeColor(pink)
    p.line(70, 90, 230, 90)
    p.line(width-230, 90, width-70, 90)

    p.setFillColor(colors.grey)
    p.setFont("Helvetica", 9)

    p.drawCentredString(150, 75, "Authorized Signature")
    p.drawCentredString(width-150, 75, "Director Approval")

    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(
        width/2,
        45,
        "Confidential • NovaLearn Internal Use Only"
    )

    p.save()
    return response