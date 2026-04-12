from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from adminapp.models import *
from homeapp.models import *
from teacherapp.models import *
from studentapp.models import *
from .forms import AssignmentForm
from datetime import date
from django.db.models import Sum, Avg, Q
from django.contrib.auth.hashers import make_password, check_password
import os
from django.views.decorators.csrf import csrf_exempt
import json
import mimetypes


def teacherbatch(request):
    # Check if teacher is logged in
    if 'teacher_id' not in request.session:
        return redirect('login')
    
    try:
        # Get teacher from session
        teacher_id = request.session['teacher_id']
        teacher = tbl_teacher.objects.get(id=teacher_id)
        
        # DEBUG: Echo teacher ID to check
        print(f"DEBUG: Teacher ID from session: {teacher_id}")
        print(f"DEBUG: Teacher object: {teacher}")
        
        # Get assigned batches with related data
        assigned_batches = tbl_teacherbatch.objects.filter(
            teacher=teacher
        ).select_related(
            'batch',
            'batch__course',
            'batch__course__stream'
        ).order_by('batch__course__stream__stream_name', 'batch__batchname')
        
        # DEBUG: Check raw SQL query
        print(f"DEBUG: SQL Query: {assigned_batches.query}")
        
        # Count total batches
        total_batches = assigned_batches.count()
        
        # DEBUG: Print count
        print(f"DEBUG: Total batches found: {total_batches}")
        
        # Prepare batch data for template
        batch_list = []
        for assignment in assigned_batches:
            batch_data = {
                'batch': assignment.batch,
                'course': assignment.batch.course,
                'stream': assignment.batch.course.stream,
                'assignment_id': assignment.id,
            }
            batch_list.append(batch_data)
            # DEBUG: Print each batch found
            print(f"DEBUG: Found batch - ID: {assignment.batch.id}, Name: {assignment.batch.batchname}")
        
        context = {
            'teacher': teacher,
            'teacher_id': teacher_id,  # Add teacher_id to context for template
            'batch_list': batch_list,
            'total_batches': total_batches,
            'assigned_batches': assigned_batches,
        }
        
        return render(request, 'teacherbatch.html', context)
        
    except tbl_teacher.DoesNotExist:
        messages.error(request, "Teacher profile not found!")
        return redirect('login')
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('login')
    


#....recoredclassmng ........

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import tbl_lessons
from adminapp.models import Batch


def manage_recorded_classes(request):
    # Get batch_id from session

    batch_id = request.session.get('batch_id')
    
    if batch_id:
        # Get lessons only for the logged-in teacher's batch
        lessons = tbl_lessons.objects.filter(batch_id=batch_id).order_by('-id')
        batch = Batch.objects.get(id=batch_id)
    else:
        # If no batch_id in session, show error or redirect
        messages.error(request, 'Please select a batch first')
        lessons = tbl_lessons.objects.none()
        batch = None
    
    return render(request, 'mngrecordedclasses.html', {
        'lessons': lessons,
        'batch': batch,
    })

def add_lesson_page(request):
    """Render the add lesson form page"""
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('manage_recorded_classes')
    
    # Get batch for display
    batch = Batch.objects.get(id=batch_id)
    
    return render(request, 'add_lesson.html', {
        'batch': batch,
    })
def add_lesson(request):
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('manage_recorded_classes')
    
    if request.method == 'POST':
        try:
            modulenumber = request.POST.get('modulenumber')
            moduletitle = request.POST.get('moduletitle')
            lessontitle = request.POST.get('lessontitle')
            pdfnotes = request.FILES.get('pdfnotes')
            videos = request.FILES.get('videos')
            
            # Validate required fields
            if not all([modulenumber, moduletitle, lessontitle]):
                messages.error(request, 'Please fill all required fields')
                return redirect('manage_recorded_classes')
            
            # Get batch from session
            batch = Batch.objects.get(id=batch_id)
            
            # Create the lesson
            lesson = tbl_lessons.objects.create(
                batch=batch,
                modulenumber=modulenumber,
                moduletitle=moduletitle,
                lessontitle=lessontitle,
                pdfnotes=pdfnotes,
                videos=videos
            )
            
            messages.success(request, f'Lesson "{lessontitle}" added successfully!')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('manage_recorded_classes')

def edit_lesson(request, lesson_id):
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('manage_recorded_classes')
    
    lesson = get_object_or_404(tbl_lessons, id=lesson_id, batch_id=batch_id)
    
    if request.method == 'POST':
        try:
            lesson.modulenumber = request.POST.get('modulenumber')
            lesson.moduletitle = request.POST.get('moduletitle')
            lesson.lessontitle = request.POST.get('lessontitle')
            
            # Update files only if new ones are uploaded
            pdfnotes = request.FILES.get('pdfnotes')
            if pdfnotes:
                lesson.pdfnotes = pdfnotes
            
            videos = request.FILES.get('videos')
            if videos:
                lesson.videos = videos
            
            lesson.save()
            messages.success(request, f'Lesson "{lesson.lessontitle}" updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('manage_recorded_classes')
    
    # If GET request, show edit form
    return render(request, 'edit_lesson.html', {
        'lesson': lesson,
    })


def delete_lesson(request, lesson_id):
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('manage_recorded_classes')
    
    lesson = get_object_or_404(tbl_lessons, id=lesson_id, batch_id=batch_id)
    
    if request.method == 'POST':
        try:
            lesson_title = lesson.lessontitle
            lesson.delete()
            messages.success(request, f'Lesson "{lesson_title}" deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('manage_recorded_classes')



from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


def set_batch_session(request, batch_id):
    """
    Simple view to set batch_id in session and redirect to manage recorded classes
    """
    try:
        # Get the batch
        batch = Batch.objects.get(id=batch_id)
        
        # Set batch_id and batch_name in session
        request.session['batch_id'] = batch.id
        request.session['batch_name'] = batch.batchname
        
        # Save the session explicitly
        request.session.modified = True
        
        # Redirect to manage recorded classes page
        return redirect('manage_recorded_classes')
        
    except Batch.DoesNotExist:
        # If batch doesn't exist, redirect back to dashboard
        return redirect('teacherdashboard')
    
def manage_assignments(request):
    """Display all assignments for the current batch"""
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    try:
        batch = Batch.objects.get(id=batch_id)
        assignments = tbl_assignment.objects.filter(batch_id=batch_id).order_by('-uploaddate')
        
        # Add days_left property to each assignment for template
        for assignment in assignments:
            today = date.today()
            assignment.days_left = (assignment.duedate - today).days
        
        return render(request, 'manage_assignments.html', {
            'assignments': assignments,
            'batch': batch,
        })
        
    except Batch.DoesNotExist:
        return redirect('teacherdashboard')


def add_assignment_page(request):
    """Render the add assignment form page"""
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    batch = Batch.objects.get(id=batch_id)
    
    # Initialize form with current batch selected
    form = AssignmentForm(initial={'batch': batch})
    
    return render(request, 'add_assignment.html', {
        'batch': batch,
        'form': form,
    })


def add_assignment(request):
    """Handle assignment form submission with file upload"""
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    if request.method == 'POST':
        try:
            batch = Batch.objects.get(id=batch_id)
            
            # Handle file upload (optional)
            assignment_file = request.FILES.get('assignmentupload')
            
            # Create assignment with file
            assignment = tbl_assignment.objects.create(
                batch=batch,
                uploaddate=request.POST.get('uploaddate'),
                duedate=request.POST.get('duedate'),
                totalmarks=request.POST.get('totalmarks'),
                assignmentupload=assignment_file,
                created_at=date.today()
            )
            
            file_message = f" with file: {assignment_file.name}" if assignment_file else " without file"
            messages.success(request, f'Assignment created successfully{file_message}!')
            return redirect('manage_assignments')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('add_assignment_page')
    
    return redirect('add_assignment_page')


def edit_assignment(request, assignment_id):
    """Edit existing assignment with file upload"""
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    assignment = get_object_or_404(tbl_assignment, id=assignment_id, batch_id=batch_id)
    
    if request.method == 'POST':
        try:
            # Update fields
            assignment.uploaddate = request.POST.get('uploaddate')
            assignment.duedate = request.POST.get('duedate')
            assignment.totalmarks = request.POST.get('totalmarks')
            
            # Handle file upload - only update if new file is provided
            new_file = request.FILES.get('assignmentupload')
            if new_file:
                # Delete old file if it exists
                if assignment.assignmentupload:
                    if os.path.isfile(assignment.assignmentupload.path):
                        os.remove(assignment.assignmentupload.path)
                
                # Assign new file
                assignment.assignmentupload = new_file
            
            assignment.save()
            
            messages.success(request, 'Assignment updated successfully!')
            return redirect('manage_assignments')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('edit_assignment', assignment_id=assignment_id)
    
    # If GET request, show edit form
    return render(request, 'edit_assignment.html', {
        'assignment': assignment,
    })


def delete_assignment(request, assignment_id):
    """Delete assignment and its associated file"""
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    assignment = get_object_or_404(tbl_assignment, id=assignment_id, batch_id=batch_id)
    
    if request.method == 'POST':
        try:
            # Delete the file from filesystem if it exists
            if assignment.assignmentupload:
                if os.path.isfile(assignment.assignmentupload.path):
                    os.remove(assignment.assignmentupload.path)
            
            # Delete the database record
            assignment.delete()
            messages.success(request, 'Assignment deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return redirect('manage_assignments')


def download_assignment(request, assignment_id):
    """Download assignment file"""
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    assignment = get_object_or_404(tbl_assignment, id=assignment_id, batch_id=batch_id)
    
    if assignment.assignmentupload:
        import mimetypes
        from django.http import FileResponse
        import os
        
        file_path = assignment.assignmentupload.path
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Type'] = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    
    messages.error(request, 'File not found')
    return redirect('manage_assignments')

def manage_doubts(request):
    """Display all doubts for lessons in the current batch"""
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    try:
        batch = Batch.objects.get(id=batch_id)
        
        # Get all lessons for this batch with doubt counts
        lessons = tbl_lessons.objects.filter(batch=batch).order_by('modulenumber')
        
        # Get doubts for each lesson
        for lesson in lessons:
            lesson.doubts = tbl_doubt.objects.filter(
                lesson_id=lesson
            ).select_related(
                'student_enrolment_id__studentid'
            ).order_by('-date_submitted')
            lesson.doubt_count = lesson.doubts.count()
            lesson.pending_count = lesson.doubts.filter(answer__isnull=True).count()
        
        # Get overall stats
        total_doubts = tbl_doubt.objects.filter(lesson_id__batch=batch).count()
        answered_doubts = tbl_doubt.objects.filter(
            lesson_id__batch=batch,
            answer__isnull=False
        ).exclude(answer='').count()
        pending_doubts = total_doubts - answered_doubts
        
        context = {
            'batch': batch,
            'lessons': lessons,
            'total_doubts': total_doubts,
            'answered_doubts': answered_doubts,
            'pending_doubts': pending_doubts,
        }
        
        return render(request, 'manage_doubts.html', context)
        
    except Batch.DoesNotExist:
        messages.error(request, 'Batch not found')
        return redirect('teacherdashboard')


def lesson_doubts(request, lesson_id):
    """View doubts for a specific lesson"""
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    # Get the lesson
    lesson = get_object_or_404(tbl_lessons, id=lesson_id, batch_id=batch_id)
    
    # Get doubts for this lesson
    doubts = tbl_doubt.objects.filter(
        lesson_id=lesson
    ).select_related(
        'student_enrolment_id__studentid'
    ).order_by('-date_submitted')
    
    # Separate answered and unanswered
    unanswered_doubts = doubts.filter(answer__isnull=True) | doubts.filter(answer='')
    answered_doubts = doubts.exclude(answer__isnull=True).exclude(answer='')
    
    context = {
        'lesson': lesson,
        'batch': lesson.batch,
        'unanswered_doubts': unanswered_doubts,
        'answered_doubts': answered_doubts,
        'total_count': doubts.count(),
        'unanswered_count': unanswered_doubts.count(),
        'answered_count': answered_doubts.count(),
    }
    
    return render(request, 'lesson_doubts.html', context)


def answer_doubt(request, doubt_id):
    """Answer a specific doubt"""
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    # Get the doubt
    doubt = get_object_or_404(
        tbl_doubt.objects.select_related(
            'lesson_id',
            'student_enrolment_id__studentid'
        ),
        id=doubt_id,
        lesson_id__batch_id=batch_id
    )
    
    if request.method == 'POST':
        answer_text = request.POST.get('answer')
        
        if answer_text:
            doubt.answer = answer_text
            doubt.answer_submitted = timezone.now()
            doubt.save()
            
            messages.success(request, 'Answer submitted successfully!')
            return redirect('lesson_doubts', lesson_id=doubt.lesson_id.id)
        else:
            messages.error(request, 'Please provide an answer')
    
    context = {
        'doubt': doubt,
        'lesson': doubt.lesson_id,
        'batch': doubt.lesson_id.batch,
        'student': doubt.student_enrolment_id.studentid,
    }
    return render(request, 'answer_doubt.html', context)


def doubt_detail(request, doubt_id):
    """View details of a specific doubt"""
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    # Get the doubt
    doubt = get_object_or_404(
        tbl_doubt.objects.select_related(
            'student_enrolment_id__studentid',
            'lesson_id',
            'student_enrolment_id__enrolled_batchid'
        ),
        id=doubt_id,
        lesson_id__batch_id=batch_id
    )
    
    context = {
        'doubt': doubt,
        'lesson': doubt.lesson_id,
        'batch': doubt.lesson_id.batch,
        'student': doubt.student_enrolment_id.studentid,
    }
    return render(request, 'doubt_detail.html', context)


def delete_doubt(request, doubt_id):
    """Delete a doubt"""
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    if request.method == 'POST':
        doubt = get_object_or_404(
            tbl_doubt,
            id=doubt_id,
            lesson_id__batch_id=batch_id
        )
        lesson_id = doubt.lesson_id.id
        doubt.delete()
        messages.success(request, 'Doubt deleted successfully!')
        return redirect('lesson_doubts', lesson_id=lesson_id)
    
    return redirect('manage_doubts')


def ajax_answer_doubt(request):
    """AJAX endpoint to answer a doubt without page reload"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        doubt_id = request.POST.get('doubt_id')
        answer_text = request.POST.get('answer')
        
        if not doubt_id or not answer_text:
            return JsonResponse({'status': 'error', 'message': 'Missing data'})
        
        try:
            doubt = tbl_doubt.objects.get(id=doubt_id)
            doubt.answer = answer_text
            doubt.answer_submitted = timezone.now()
            doubt.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Answer submitted successfully',
                'answer': answer_text,
                'answer_date': doubt.answer_submitted.strftime('%d %b %Y, %I:%M %p')
            })
        except tbl_doubt.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Doubt not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def get_lesson_doubts_api(request, lesson_id):
    """API endpoint to get doubts for a lesson (for AJAX refresh)"""
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        return JsonResponse({'status': 'error', 'message': 'No batch selected'})
    
    try:
        lesson = tbl_lessons.objects.get(id=lesson_id, batch_id=batch_id)
        doubts = tbl_doubt.objects.filter(lesson_id=lesson).select_related(
            'student_enrolment_id__studentid'
        ).order_by('-date_submitted')
        
        doubts_data = []
        for doubt in doubts:
            doubts_data.append({
                'id': doubt.id,
                'description': doubt.description,
                'date_submitted': doubt.date_submitted.strftime('%d %b %Y, %I:%M %p'),
                'student_name': doubt.student_enrolment_id.studentid.name,
                'student_initial': doubt.student_enrolment_id.studentid.name[0].upper(),
                'answer': doubt.answer,
                'answer_submitted': doubt.answer_submitted.strftime('%d %b %Y, %I:%M %p') if doubt.answer_submitted else None,
                'has_answer': bool(doubt.answer)
            })
        
        return JsonResponse({
            'status': 'success',
            'doubts': doubts_data,
            'total': len(doubts_data),
            'unanswered': sum(1 for d in doubts_data if not d['has_answer'])
        })
        
    except tbl_lessons.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Lesson not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def bulk_answer_doubts(request, lesson_id):
    """Answer multiple doubts at once"""
    # Get batch_id from session
    batch_id = request.session.get('batch_id')
    
    if not batch_id:
        messages.error(request, 'Please select a batch first')
        return redirect('teacherdashboard')
    
    lesson = get_object_or_404(tbl_lessons, id=lesson_id, batch_id=batch_id)
    
    if request.method == 'POST':
        doubt_ids = request.POST.getlist('doubt_ids')
        common_answer = request.POST.get('common_answer')
        
        if not doubt_ids:
            messages.error(request, 'No doubts selected')
            return redirect('lesson_doubts', lesson_id=lesson_id)
        
        if not common_answer:
            messages.error(request, 'Please provide an answer')
            return redirect('lesson_doubts', lesson_id=lesson_id)
        
        # Update all selected doubts
        updated = tbl_doubt.objects.filter(
            id__in=doubt_ids,
            lesson_id=lesson
        ).update(
            answer=common_answer,
            answer_submitted=timezone.now()
        )
        
        messages.success(request, f'{updated} doubt(s) answered successfully!')
        return redirect('lesson_doubts', lesson_id=lesson_id)
    
    return redirect('lesson_doubts', lesson_id=lesson_id)

# 

def teacher_profile(request):
    # Get teacher ID from session
    teacher_id = request.session.get('teacher_id')
    
    if not teacher_id:
        messages.error(request, 'Please login to access your profile')
        return redirect('login_view')  # Make sure this matches your login URL name
    
    try:
        teacher = tbl_teacher.objects.select_related('login').get(id=teacher_id)
        
        if request.method == 'POST':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # For plain text passwords (current system)
            if teacher.login.password != current_password:
                messages.error(request, 'Current password is incorrect')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match')
            elif len(new_password) < 6:
                messages.error(request, 'Password must be at least 6 characters long')
            else:
                # Update password - still plain text
                teacher.login.password = new_password  # Direct assignment for plain text
                teacher.login.save()
                messages.success(request, 'Password updated successfully!')
                
            return redirect('teacher_profile')
        
        context = {
            'teacher': teacher
        }
        return render(request, 'teacher_profile.html', context)
        
    except tbl_teacher.DoesNotExist:
        messages.error(request, 'Teacher not found')
        return redirect('login_view')
    
def teacher_students(request):
    """Display students for teacher's batches with course and batch filter"""
    
    teacher_id = request.session.get('teacher_id')
    
    if not teacher_id:
        messages.error(request, 'Please login to access this page')
        return redirect('login_view')
    
    try:
        teacher = tbl_teacher.objects.get(id=teacher_id)
        
        # Get all batches assigned to this teacher
        teacher_batches = tbl_teacherbatch.objects.filter(
            teacher=teacher
        ).select_related('batch', 'batch__course')
        
        # Get filter parameters
        course_id = request.GET.get('course')
        batch_id = request.GET.get('batch')
        search_query = request.GET.get('search', '')
        
        # Get unique courses from teacher's batches
        courses = []
        for tb in teacher_batches:
            if tb.batch.course not in courses:
                courses.append(tb.batch.course)
        
        # Filter batches based on selected course
        batches = []
        if course_id:
            batches = [tb.batch for tb in teacher_batches if tb.batch.course_id == int(course_id)]
        else:
            batches = [tb.batch for tb in teacher_batches]
        
        # Get all students enrolled in these batches
        enrollments = tbl_student_enrolment.objects.filter(
            enrolled_batchid__in=batches,
            is_active_student='yes'
        ).select_related(
            'studentid',
            'studentid__login',
            'enrolled_batchid',
            'enrolled_batchid__course'
        ).order_by('enrolled_batchid__course__coursename', 'studentid__first_name')
        
        # Apply batch filter if selected
        if batch_id:
            enrollments = enrollments.filter(enrolled_batchid_id=batch_id)
        
        # Apply search filter
        if search_query:
            enrollments = enrollments.filter(
                Q(studentid__first_name__icontains=search_query) |
                Q(studentid__last_name__icontains=search_query) |
                Q(studentid__login__email__icontains=search_query)
            )
        
        context = {
            'teacher': teacher,
            'enrollments': enrollments,
            'courses': courses,
            'batches': batches,
            'selected_course': course_id,
            'selected_batch': batch_id,
            'search_query': search_query,
            'total_students': enrollments.count(),
            'total_batches': len(batches),
        }
        
        return render(request, 'teacher_students.html', context)
        
    except tbl_teacher.DoesNotExist:
        messages.error(request, 'Teacher not found')
        return redirect('login_view')


def student_assignments_page(request, student_id, batch_id):
    """Page showing all assignments submitted by a student"""
    
    teacher_id = request.session.get('teacher_id')
    
    if not teacher_id:
        messages.error(request, 'Please login to access this page')
        return redirect('login_view')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = Batch.objects.get(id=batch_id)
        
        # Verify teacher is assigned to this batch
        if not tbl_teacherbatch.objects.filter(teacher_id=teacher_id, batch=batch).exists():
            messages.error(request, 'You are not authorized to view this student')
            return redirect('teacher_students')
        
        # Get enrollment
        enrollment = tbl_student_enrolment.objects.get(
            studentid=student,
            enrolled_batchid=batch,
            is_active_student='yes'
        )
        
        # Get all assignments for this batch
        assignments = tbl_assignment.objects.filter(batch=batch).order_by('-uploaddate')
        
        # Create a list of assignments with submission data
        assignment_list = []
        for assignment in assignments:
            try:
                submission = tbl_assignmentstudent.objects.get(
                    student=student,
                    assignment=assignment
                )
                assignment_list.append({
                    'assignment': assignment,
                    'submitted': True,
                    'submission': submission
                })
            except tbl_assignmentstudent.DoesNotExist:
                assignment_list.append({
                    'assignment': assignment,
                    'submitted': False,
                    'submission': None
                })
        
        context = {
            'student': student,
            'batch': batch,
            'enrollment': enrollment,
            'assignment_list': assignment_list,
        }
        return render(request, 'student_assignments_page.html', context)
        
    except tbl_student_enrolment.DoesNotExist:
        messages.error(request, 'Student not enrolled in this batch')
        return redirect('teacher_students')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('teacher_students')


@csrf_exempt
def save_assignment_marks(request):
    """Save marks for an assignment submission"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            submission_id = data.get('submission_id')
            marks = data.get('marks')
            
            print(f"Received submission_id: {submission_id}, marks: {marks}")  # Debug print
            
            # Get the submission
            submission = tbl_assignmentstudent.objects.get(id=submission_id)
            
            # Verify teacher is authorized
            teacher_id = request.session.get('teacher_id')
            if not tbl_teacherbatch.objects.filter(
                teacher_id=teacher_id, 
                batch=submission.assignment.batch
            ).exists():
                return JsonResponse({'success': False, 'error': 'Unauthorized'})
            
            # Save marks
            submission.assigned_marks = marks
            submission.save()
            
            print(f"Marks saved successfully")  # Debug print
            
            return JsonResponse({
                'success': True,
                'message': 'Marks saved successfully'
            })
            
        except tbl_assignmentstudent.DoesNotExist:
            print(f"Submission not found with id: {submission_id}")  # Debug print
            return JsonResponse({'success': False, 'error': 'Submission not found'})
        except Exception as e:
            print(f"Error: {str(e)}")  # Debug print
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def student_exam_marks_page(request, student_id, batch_id):
    """Page showing exam marks for a student"""
    
    teacher_id = request.session.get('teacher_id')
    
    if not teacher_id:
        messages.error(request, 'Please login to access this page')
        return redirect('login_view')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = Batch.objects.get(id=batch_id)
        
        # Verify teacher is assigned to this batch
        if not tbl_teacherbatch.objects.filter(teacher_id=teacher_id, batch=batch).exists():
            messages.error(request, 'You are not authorized to view this student')
            return redirect('teacher_students')
        
        # Get enrollment
        enrollment = tbl_student_enrolment.objects.get(
            studentid=student,
            enrolled_batchid=batch,
            is_active_student='yes'
        )
        
        # Get exam results for this enrollment
        exam_results = tbl_student_examresult.objects.filter(
            student_enrol_id=enrollment
        ).select_related('examid')
        
        # Calculate percentage for each result
        total_percentage = 0
        for result in exam_results:
            exam_total = result.examid.totalscore
            if exam_total > 0:
                result.percentage = (result.total_score_obtained / exam_total) * 100
                total_percentage += result.percentage
            else:
                result.percentage = 0
        
        avg_percentage = total_percentage / len(exam_results) if exam_results else 0
        
        context = {
            'student': student,
            'batch': batch,
            'enrollment': enrollment,
            'exam_results': exam_results,
            'avg_percentage': round(avg_percentage, 2),
        }
        return render(request, 'student_exam_marks_page.html', context)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('teacher_students')


def student_payment_page(request, student_id, batch_id):
    """Page showing payment status for a student"""
    
    teacher_id = request.session.get('teacher_id')
    
    if not teacher_id:
        messages.error(request, 'Please login to access this page')
        return redirect('login_view')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = Batch.objects.get(id=batch_id)
        
        # Verify teacher is assigned to this batch
        if not tbl_teacherbatch.objects.filter(teacher_id=teacher_id, batch=batch).exists():
            messages.error(request, 'You are not authorized to view this student')
            return redirect('teacher_students')
        
        # Get enrollment
        enrollment = tbl_student_enrolment.objects.get(
            studentid=student,
            enrolled_batchid=batch,
            is_active_student='yes'
        )
        
        # Get all payments for this enrollment
        payments = tbl_payment.objects.filter(
            student_enrol_id=enrollment
        ).order_by('-paymentdate')
        
        # Calculate totals
        total_course_fee = float(batch.course.rate)
        total_paid = float(payments.filter(paymentstatus='completed').aggregate(Sum('amount'))['amount__sum'] or 0)
        balance = total_course_fee - total_paid
        payment_percentage = (total_paid / total_course_fee) * 100 if total_course_fee > 0 else 0
        
        # Determine status
        if balance <= 0:
            payment_status = 'Fully Paid'
            status_class = 'success'
        elif total_paid > 0:
            payment_status = 'Partially Paid'
            status_class = 'warning'
        else:
            payment_status = 'No Payment'
            status_class = 'danger'
        
        context = {
            'student': student,
            'batch': batch,
            'enrollment': enrollment,
            'payments': payments,
            'total_fee': total_course_fee,
            'total_paid': total_paid,
            'balance': balance,
            'payment_percentage': round(payment_percentage, 2),
            'payment_status': payment_status,
            'status_class': status_class,
        }
        return render(request, 'student_payment_page.html', context)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('teacher_students')
    
def student_final_score_page(request, student_id, batch_id):
    """Page showing final score calculation for a student"""
    
    teacher_id = request.session.get('teacher_id')
    
    if not teacher_id:
        messages.error(request, 'Please login to access this page')
        return redirect('login_view')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = Batch.objects.get(id=batch_id)
        
        # Verify teacher is assigned to this batch
        if not tbl_teacherbatch.objects.filter(teacher_id=teacher_id, batch=batch).exists():
            messages.error(request, 'You are not authorized to view this student')
            return redirect('teacher_students')
        
        # Get enrollment
        enrollment = tbl_student_enrolment.objects.get(
            studentid=student,
            enrolled_batchid=batch,
            is_active_student='yes'
        )
        
        # Get all assignments for this batch
        assignments = tbl_assignment.objects.filter(batch=batch).order_by('uploaddate')
        
        # Calculate assignment marks
        assignment_list = []
        total_assignment_marks = 0
        total_assignment_obtained = 0
        assignment_counter = 1
        
        for assignment in assignments:
            try:
                submission = tbl_assignmentstudent.objects.get(
                    student=student,
                    assignment=assignment
                )
                obtained = submission.assigned_marks if submission.assigned_marks else 0
                assignment_list.append({
                    'name': f"Assignment {assignment_counter}",
                    'total': assignment.totalmarks,
                    'obtained': obtained,
                    'submitted': True,
                    'graded': submission.assigned_marks is not None
                })
                if submission.assigned_marks:
                    total_assignment_obtained += submission.assigned_marks
                total_assignment_marks += assignment.totalmarks
            except tbl_assignmentstudent.DoesNotExist:
                assignment_list.append({
                    'name': f"Assignment {assignment_counter}",
                    'total': assignment.totalmarks,
                    'obtained': 0,
                    'submitted': False,
                    'graded': False
                })
                total_assignment_marks += assignment.totalmarks
            assignment_counter += 1
        
        # Get exam results
        exam_results = tbl_student_examresult.objects.filter(
            student_enrol_id=enrollment
        ).select_related('examid')
        
        exam_list = []
        total_exam_marks = 0
        total_exam_obtained = 0
        
        for result in exam_results:
            exam_list.append({
                'name': result.examid.examcode,
                'total': result.examid.totalscore,
                'obtained': result.total_score_obtained
            })
            total_exam_obtained += result.total_score_obtained
            total_exam_marks += result.examid.totalscore
        
        # Calculate overall score
        total_marks = total_assignment_marks + total_exam_marks
        total_obtained = total_assignment_obtained + total_exam_obtained
        overall_percentage = (total_obtained / total_marks * 100) if total_marks > 0 else 0
        
        # Check if final mark already exists
        try:
            final_mark = tbl_final.objects.get(student_enrolment_id=enrollment)
            final_exists = True
        except tbl_final.DoesNotExist:
            final_mark = None
            final_exists = False
        
        context = {
            'student': student,
            'batch': batch,
            'enrollment': enrollment,
            'assignment_list': assignment_list,
            'exam_list': exam_list,
            'total_assignment_marks': total_assignment_marks,
            'total_assignment_obtained': total_assignment_obtained,
            'total_exam_marks': total_exam_marks,
            'total_exam_obtained': total_exam_obtained,
            'total_marks': total_marks,
            'total_obtained': total_obtained,
            'overall_percentage': round(overall_percentage, 2),
            'final_exists': final_exists,
            'final_mark': final_mark.final_mark if final_mark else None,
        }
        return render(request, 'student_final_score_page.html', context)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('teacher_students')

@csrf_exempt
def save_final_mark(request):
    """Save final mark for a student"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            enrollment_id = data.get('enrollment_id')
            final_mark = data.get('final_mark')
            
            print(f"Received enrollment_id: {enrollment_id}, final_mark: {final_mark}")
            
            if not enrollment_id or final_mark is None:
                return JsonResponse({'success': False, 'error': 'Missing required data'})
            
            # Get enrollment
            enrollment = tbl_student_enrolment.objects.get(id=enrollment_id)
            
            # Verify teacher is authorized
            teacher_id = request.session.get('teacher_id')
            if not tbl_teacherbatch.objects.filter(
                teacher_id=teacher_id, 
                batch=enrollment.enrolled_batchid
            ).exists():
                return JsonResponse({'success': False, 'error': 'Unauthorized'})
            
            # Check if final mark already exists
            final, created = tbl_final.objects.update_or_create(
                student_enrolment_id=enrollment,
                defaults={'final_mark': final_mark}
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Final mark saved successfully',
                'final_mark': final_mark
            })
            
        except tbl_student_enrolment.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Enrollment not found'})
        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})