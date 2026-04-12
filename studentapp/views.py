from django.shortcuts import render, redirect, get_object_or_404
from adminapp.models import*
from homeapp.models import*
from teacherapp.models import*
from .models import*
from .forms import*
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db import connection
from datetime import date
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import get_template
from io import BytesIO
from django.contrib.auth.hashers import make_password, check_password
import os
from django.db.models import Avg
import mimetypes
import random
import datetime  # Add this import for view_certificate

def student_home(request):
    """Display all courses to students with student info from session"""
    
    # Get student ID from session
    student_id = request.session.get('studentid')
    student = None
    
    if student_id:
        try:
            student = tbl_Student.objects.get(id=student_id)
        except tbl_Student.DoesNotExist:
            pass
    
    # Get all active streams and courses
    streams = Stream.objects.filter(status=1).order_by('stream_name')
    courses = Course.objects.select_related('stream').all().order_by('-id')
    
    context = {
        'courses': courses,
        'streams': streams,
        'student': student,
        'student_id': student_id,
    }
    return render(request, 'studenthome.html', context)



def course_detail(request, course_id):
    """Display course details with reviews"""
    course = Course.objects.select_related('stream').get(id=course_id)
    
    # Get all reviews for this course (including unapproved if you want to show all)
    reviews = tbl_course_review.objects.filter(
        course=course
    ).select_related('student', 'batch').order_by('-created_at')
    
    # Calculate average rating
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Calculate rating counts for each star
    review_counts = {
        5: reviews.filter(rating=5).count(),
        4: reviews.filter(rating=4).count(),
        3: reviews.filter(rating=3).count(),
        2: reviews.filter(rating=2).count(),
        1: reviews.filter(rating=1).count(),
    }
    
    context = {
        'course': course,
        'reviews': reviews,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'review_counts': review_counts,
    }
    return render(request, 'course_detail.html', context)



############################################################

# Fixed enrollment amount - not in model
ENROLLMENT_AMOUNT = 1000.00  # Fixed initial enrollment amount

def payment_details(request, batch_id):
    """Display payment details and history for a batch"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, "Please login to view payment details")
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = get_object_or_404(Batch.objects.select_related('course__stream'), id=batch_id)
        
        # Get enrollment
        enrollment = get_object_or_404(
            tbl_student_enrolment,
            studentid=student,
            enrolled_batchid=batch,
            is_active_student='yes'
        )
        
        # Get all payments for this enrollment
        payments = tbl_payment.objects.filter(
            student_enrol_id=enrollment
        ).order_by('-paymentdate')
        
        # Calculate totals using course rate
        total_fee = batch.course.rate  # Get course fee from course model
        total_paid = sum(payment.amount for payment in payments if payment.paymentstatus == 'completed')
        balance = total_fee - total_paid
        payment_percentage = (total_paid / total_fee) * 100 if total_fee > 0 else 0
        
        context = {
            'batch': batch,
            'enrollment': enrollment,
            'payments': payments,
            'total_paid': total_paid,
            'total_fee': total_fee,
            'balance': balance,
            'payment_percentage': payment_percentage,
            'fixed_amount': ENROLLMENT_AMOUNT,
        }
        
        return render(request, 'payment_details.html', context)
        
    except tbl_Student.DoesNotExist:
        messages.error(request, "Student not found")
        return redirect('student_home')
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('my_courses')


def make_payment(request, batch_id):
    """Show payment page for balance amount"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, "Please login to make payment")
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = get_object_or_404(Batch.objects.select_related('course'), id=batch_id)
        
        # Get enrollment
        enrollment = get_object_or_404(
            tbl_student_enrolment,
            studentid=student,
            enrolled_batchid=batch,
            is_active_student='yes'
        )
        
        # Get total paid
        payments = tbl_payment.objects.filter(
            student_enrol_id=enrollment,
            paymentstatus='completed'
        )
        total_paid = sum(payment.amount for payment in payments)
        
        # Calculate balance using course rate
        total_fee = batch.course.rate
        balance = total_fee - total_paid
        payment_percentage = (total_paid / total_fee) * 100 if total_fee > 0 else 0
        
        if balance <= 0:
            messages.info(request, "No balance amount to pay. You have fully paid for this course.")
            return redirect('payment_details', batch_id=batch_id)
        
        context = {
            'batch': batch,
            'enrollment': enrollment,
            'amount': balance,
            'total_paid': total_paid,
            'total_fee': total_fee,
            'payment_percentage': payment_percentage,
        }
        
        return render(request, 'make_payment.html', context)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('payment_details', batch_id=batch_id)


def process_balance_payment(request, batch_id):
    """Process balance payment"""
    if request.method == 'POST':
        student_id = request.session.get('studentid')
        
        if not student_id:
            messages.error(request, "Please login to process payment")
            return redirect('student_login')
        
        try:
            student = tbl_Student.objects.get(id=student_id)
            batch = get_object_or_404(Batch, id=batch_id)
            amount = float(request.POST.get('amount', 0))
            payment_mode = request.POST.get('payment_mode', 'card')
            
            # Get enrollment
            enrollment = get_object_or_404(
                tbl_student_enrolment,
                studentid=student,
                enrolled_batchid=batch,
                is_active_student='yes'
            )
            
            # Create payment record
            payment = tbl_payment.objects.create(
                student_enrol_id=enrollment,
                paymentdate=date.today(),
                payment_mode=payment_mode,
                paymentstatus='completed',
                amount=amount
            )
            
            messages.success(request, f'Payment of ₹ {amount} completed successfully!')
            return redirect('payment_details', batch_id=batch_id)
            
        except Exception as e:
            messages.error(request, f"Payment failed: {str(e)}")
            return redirect('make_payment', batch_id=batch_id)
    
    return redirect('payment_details', batch_id=batch_id)


def batch_exams(request, batch_id):
    """Display exams for a batch with eligibility check and certificate status"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, "Please login to view exams")
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = get_object_or_404(Batch.objects.select_related('course'), id=batch_id)
        
        # Check enrollment
        enrollment = get_object_or_404(
            tbl_student_enrolment,
            studentid=student,
            enrolled_batchid=batch,
            is_active_student='yes'
        )
        
        # Check eligibility: 2 assignments submitted and payment completed
        submitted_assignments = tbl_assignmentstudent.objects.filter(
            student=student,
            assignment__batch=batch
        ).count()
        
        # Check payment status
        payments = tbl_payment.objects.filter(
            student_enrol_id=enrollment,
            paymentstatus='completed'
        )
        total_paid = sum(payment.amount for payment in payments)
        is_paid = total_paid >= batch.course.rate  # Fully paid
        
        is_eligible = submitted_assignments >= 2 and is_paid
        
        # Get exams for this course
        exams = exam.objects.filter(courseid=batch.course)
        
        # Get question count for each exam
        for exam_item in exams:
            exam_item.question_count = tbl_examquestion.objects.filter(examid=exam_item).count()
        
        # Track completed exams (using session for now since we don't have student_exam model)
        completed_exams = request.session.get(f'completed_exams_{student_id}_{batch_id}', [])
        
        # Mock exam results (in real scenario, you'd store these in database)
        exam_results = []
        for exam_id in completed_exams:
            exam_result = request.session.get(f'exam_result_{student_id}_{batch_id}_{exam_id}')
            if exam_result:
                exam_results.append(exam_result)
        
        # ===== Check if certificate is available (final mark exists) =====
        certificate_available = False
        final_mark = None
        total_marks = None
        percentage = None
        grade = None
        user_has_reviewed = False
        
        try:
            # Check if final mark exists in tbl_final
            final_result = tbl_final.objects.get(student_enrolment_id=enrollment)
            final_mark = final_result.final_mark
            
            # Calculate total possible marks (assignments + exams)
            assignments = tbl_assignment.objects.filter(batch=batch)
            total_assignment_marks = sum(assignment.totalmarks for assignment in assignments)
            
            exam_results_db = tbl_student_examresult.objects.filter(student_enrol_id=enrollment)
            total_exam_marks = sum(result.examid.totalscore for result in exam_results_db)
            
            total_marks = total_assignment_marks + total_exam_marks
            
            # Calculate percentage
            percentage = (final_mark / total_marks * 100) if total_marks > 0 else 0
            percentage = round(percentage, 2)
            
            # Determine grade based on percentage
            if percentage >= 90:
                grade = 'A+'
            elif percentage >= 80:
                grade = 'A'
            elif percentage >= 70:
                grade = 'B+'
            elif percentage >= 60:
                grade = 'B'
            elif percentage >= 50:
                grade = 'C'
            elif percentage >= 40:
                grade = 'D'
            else:
                grade = 'F'
            
            certificate_available = True
            
            # Check if user has already reviewed this course
            try:
                review = tbl_course_review.objects.get(
                    student=student,
                    course=batch.course
                )
                user_has_reviewed = True
            except tbl_course_review.DoesNotExist:
                user_has_reviewed = False
                
        except tbl_final.DoesNotExist:
            # No final mark yet, certificate not available
            certificate_available = False
        except Exception as e:
            print(f"Error checking certificate: {str(e)}")
            certificate_available = False
        # ===== END OF CERTIFICATE CHECK =====
        
        context = {
            'batch': batch,
            'enrollment': enrollment,
            'exams': exams,
            'is_eligible': is_eligible,
            'submitted_assignments_count': submitted_assignments,
            'payment_status': 'Completed' if is_paid else 'Pending',
            'completed_exams': completed_exams,
            'exam_results': exam_results,
            # Certificate variables
            'certificate_available': certificate_available,
            'final_mark': final_mark,
            'total_marks': total_marks,
            'percentage': percentage,
            'grade': grade,
            'user_has_reviewed': user_has_reviewed,
        }
        
        return render(request, 'batch_exams.html', context)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('batch_classes', batch_id=batch_id)


def exam_instructions(request, batch_id, exam_id):
    """Show exam instructions before starting"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = get_object_or_404(Batch, id=batch_id)
        exam_item = get_object_or_404(exam, id=exam_id)
        
        # Check enrollment
        enrollment = get_object_or_404(
            tbl_student_enrolment,
            studentid=student,
            enrolled_batchid=batch
        )
        
        # Check if exam already completed
        completed_exams = request.session.get(f'completed_exams_{student_id}_{batch_id}', [])
        if exam_id in completed_exams:
            messages.warning(request, "You have already taken this exam")
            return redirect('batch_exams', batch_id=batch_id)
        
        # Get total questions that will appear in exam (20 or less)
        total_questions_in_bank = tbl_examquestion.objects.filter(examid=exam_item).count()
        total_questions = min(20, total_questions_in_bank)  # Show 20 questions or less if not enough
        
        # Calculate time per question
        time_per_question = (exam_item.duration * 60) // total_questions if total_questions > 0 else 0
        
        context = {
            'batch': batch,
            'exam': exam_item,
            'total_questions': total_questions,  # This will show 20
            'time_per_question': time_per_question,
        }
        
        return render(request, 'exam_instructions.html', context)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('batch_exams', batch_id=batch_id)


def take_exam(request, batch_id, exam_id):
    """Take the exam with shuffled questions - 20 random questions from total"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = get_object_or_404(Batch, id=batch_id)
        exam_item = get_object_or_404(exam, id=exam_id)
        
        # Check if exam already completed
        completed_exams = request.session.get(f'completed_exams_{student_id}_{batch_id}', [])
        if exam_id in completed_exams:
            messages.warning(request, "You have already taken this exam")
            return redirect('batch_exams', batch_id=batch_id)
        
        # Check if exam is already in progress and has stored questions
        session_key = f'exam_questions_{student_id}_{exam_id}'
        stored_questions = request.session.get(session_key)
        
        if stored_questions and not request.GET.get('refresh', False):
            # Use stored questions if they exist (prevents reshuffling on refresh)
            selected_question_ids = stored_questions
        else:
            # Get all questions for this exam
            all_exam_questions = tbl_examquestion.objects.filter(examid=exam_item).select_related('questionid')
            all_question_ids = list(all_exam_questions.values_list('questionid__id', flat=True))
            
            # Select 20 random questions (or all if less than 20)
            num_questions = min(20, len(all_question_ids))
            selected_question_ids = random.sample(all_question_ids, num_questions)
            
            # Store in session to maintain same questions on refresh
            request.session[session_key] = selected_question_ids
        
        # Shuffle the selected questions
        random.shuffle(selected_question_ids)
        
        # Prepare questions with options
        questions_data = []
        for qid in selected_question_ids:
            question = get_object_or_404(tbl_question, id=qid)
            options = list(tbl_option.objects.filter(questionid=question))
            random.shuffle(options)  # Shuffle options
            
            questions_data.append({
                'question': question,
                'options': options,
            })
        
        # Get any previously selected answers (if returning to exam)
        answers_key = f'exam_answers_{student_id}_{exam_id}'
        selected_answers = request.session.get(answers_key, {})
        
        # Store total questions count in session
        request.session[f'exam_total_{student_id}_{exam_id}'] = len(questions_data)
        
        context = {
            'batch': batch,
            'exam': exam_item,
            'questions': questions_data,
            'total_questions': len(questions_data),
            'question_range': range(1, len(questions_data) + 1),
            'marks_per_question': 1,  # Each question carries 1 mark
            'selected_options': selected_answers,
        }
        
        return render(request, 'take_exam.html', context)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('batch_exams', batch_id=batch_id)


def submit_exam(request, batch_id, exam_id):
    """Submit exam and calculate results"""
    if request.method == 'POST':
        student_id = request.session.get('studentid')
        
        if not student_id:
            return redirect('student_login')
        
        try:
            student = tbl_Student.objects.get(id=student_id)
            batch = get_object_or_404(Batch, id=batch_id)
            exam_item = get_object_or_404(exam, id=exam_id)
            
            # Get enrollment
            enrollment = get_object_or_404(
                tbl_student_enrolment,
                studentid=student,
                enrolled_batchid=batch,
                is_active_student='yes'
            )
            
            # Get stored question IDs
            question_ids = request.session.get(f'exam_questions_{student_id}_{exam_id}', [])
            total_questions = len(question_ids)
            
            # Process answers
            score = 0
            correct_count = 0
            wrong_count = 0
            unattempted = 0
            
            detailed_results = []
            
            for idx, question_id in enumerate(question_ids):
                question = get_object_or_404(tbl_question, id=question_id)
                selected_option_id = request.POST.get(f'question_{question_id}')
                
                # Get all options for this question
                options = tbl_option.objects.filter(questionid=question)
                correct_option = options.filter(answerstatus=True).first()
                
                is_correct = False
                selected_option = None
                selected_option_text = None
                correct_option_text = None
                
                if selected_option_id:
                    selected_option = get_object_or_404(tbl_option, id=selected_option_id)
                    selected_option_text = selected_option.option
                    if selected_option.answerstatus:
                        is_correct = True
                        score += 1  # 1 mark per question
                        correct_count += 1
                    else:
                        wrong_count += 1
                else:
                    unattempted += 1
                
                # Get correct option text
                if correct_option:
                    correct_option_text = correct_option.option
                
                # Store only serializable data
                detailed_results.append({
                    'question_id': question.id,
                    'question_text': question.question,
                    'selected_option_id': int(selected_option_id) if selected_option_id else None,
                    'selected_option_text': selected_option_text,
                    'correct_option_id': correct_option.id if correct_option else None,
                    'correct_option_text': correct_option_text,
                    'is_correct': is_correct,
                })
            
            # Calculate percentage
            percentage = (score / total_questions) * 100 if total_questions > 0 else 0
            
            # ===== Save to tbl_student_examresult =====
            # Check if result already exists
            existing_result = tbl_student_examresult.objects.filter(
                student_enrol_id=enrollment,
                examid=exam_item
            ).first()
            
            if existing_result:
                # Update existing result
                existing_result.total_score_obtained = score
                existing_result.save()
            else:
                # Create new result
                tbl_student_examresult.objects.create(
                    student_enrol_id=enrollment,
                    examid=exam_item,
                    total_score_obtained=score
                )
            # ===== END OF SAVE =====
            
            # Store result in session - only serializable data
            result_key = f'exam_result_{student_id}_{batch_id}_{exam_id}'
            result_data = {
                'exam_id': exam_id,
                'score': score,
                'total_questions': total_questions,
                'percentage': percentage,
                'correct_count': correct_count,
                'wrong_count': wrong_count,
                'unattempted': unattempted,
                'detailed_results': detailed_results,
                'submitted_at': str(timezone.now()),
            }
            request.session[result_key] = result_data
            
            # Mark exam as completed
            completed_key = f'completed_exams_{student_id}_{batch_id}'
            completed_exams = request.session.get(completed_key, [])
            if exam_id not in completed_exams:
                completed_exams.append(exam_id)
            request.session[completed_key] = completed_exams
            
            # Store answers for reference (optional)
            answers_dict = {}
            for key, value in request.POST.items():
                if key.startswith('question_'):
                    answers_dict[key] = value
            request.session[f'exam_answers_{student_id}_{exam_id}'] = answers_dict
            
            # Clear exam questions from session
            if f'exam_questions_{student_id}_{exam_id}' in request.session:
                del request.session[f'exam_questions_{student_id}_{exam_id}']
            
            messages.success(request, f"Exam submitted successfully! Your score: {score}/{total_questions}")
            return redirect('view_exam_result', batch_id=batch_id, exam_id=exam_id)
            
        except Exception as e:
            messages.error(request, f"Error submitting exam: {str(e)}")
            return redirect('take_exam', batch_id=batch_id, exam_id=exam_id)
    
    return redirect('batch_exams', batch_id=batch_id)


def view_exam_result(request, batch_id, exam_id):
    """View exam result"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        batch = get_object_or_404(Batch, id=batch_id)
        exam_item = get_object_or_404(exam, id=exam_id)
        
        # Get result from session
        result_key = f'exam_result_{student_id}_{batch_id}_{exam_id}'
        result_data = request.session.get(result_key)
        
        if not result_data:
            messages.error(request, "Result not found")
            return redirect('batch_exams', batch_id=batch_id)
        
        # Reconstruct detailed results with actual model instances for display
        detailed_results = []
        for item in result_data['detailed_results']:
            question = get_object_or_404(tbl_question, id=item['question_id'])
            
            selected_option = None
            if item['selected_option_id']:
                try:
                    selected_option = get_object_or_404(tbl_option, id=item['selected_option_id'])
                except:
                    selected_option = None
            
            correct_option = None
            if item['correct_option_id']:
                try:
                    correct_option = get_object_or_404(tbl_option, id=item['correct_option_id'])
                except:
                    correct_option = None
            
            detailed_results.append({
                'question': question,
                'selected_option': selected_option,
                'correct_option': correct_option,
                'is_correct': item['is_correct'],
            })
        
        context = {
            'batch': batch,
            'exam': exam_item,
            'score': result_data['score'],
            'total_questions': result_data['total_questions'],
            'percentage': result_data['percentage'],
            'correct_count': result_data['correct_count'],
            'wrong_count': result_data['wrong_count'],
            'unattempted': result_data['unattempted'],
            'detailed_results': detailed_results,
            'marks_per_question': 1,
            'time_taken': exam_item.duration,
        }
        
        return render(request, 'exam_result.html', context)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('batch_exams', batch_id=batch_id)
    
def enroll_course(request, course_id):

    from django.contrib import messages

    student_id = request.session.get('studentid')

    if not student_id:
        messages.error(request, "Please login to enroll in courses")
        return redirect('student_login')

    try:
        student = tbl_Student.objects.get(id=student_id)
        course = get_object_or_404(Course, id=course_id)
    except tbl_Student.DoesNotExist:
        messages.error(request, "Student not found")
        return redirect('student_home')

    # ✅ Already enrolled check
    existing_enrollment = tbl_student_enrolment.objects.filter(
        studentid=student,
        enrolled_batchid__course=course,
        is_active_student='yes'
    ).exists()

    if existing_enrollment:
        messages.warning(
            request,
            f"You are already enrolled in {course.coursename}"
        )

        # ✅ reload SAME courses page
        return redirect('student_home')

    # NORMAL FLOW
    if request.method == 'POST':
        form = EnrollmentForm(request.POST, course_id=course_id)

        if form.is_valid():
            selected_batch = form.cleaned_data['batch']

            request.session['enroll_course_id'] = course_id
            request.session['enroll_batch_id'] = selected_batch.id

            return redirect('process_payment')

        else:
            messages.error(request, "Please select a batch")

    else:
        form = EnrollmentForm(course_id=course_id)

    available_batches = Batch.objects.filter(
        course=course,
        status='Open'
    ).exists()

    context = {
        'form': form,
        'course': course,
        'student': student,
        'available_batches': available_batches,
        'fixed_amount': ENROLLMENT_AMOUNT,
    }

    return render(request, 'enroll_course.html', context)
def process_payment(request):
    """Step 2: Process payment with fixed amount 1000 (set in view, not in model)"""
    
    # Check if student is logged in
    student_id = request.session.get('studentid')
    if not student_id:
        messages.error(request, "Please login to continue")
        return redirect('student_login')
    
    # Get enrollment details from session
    course_id = request.session.get('enroll_course_id')
    batch_id = request.session.get('enroll_batch_id')
    
    if not course_id or not batch_id:
        messages.error(request, "Enrollment session expired. Please start over.")
        return redirect('student_home')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        course = Course.objects.get(id=course_id)
        batch = Batch.objects.get(id=batch_id)
    except (tbl_Student.DoesNotExist, Course.DoesNotExist, Batch.DoesNotExist):
        messages.error(request, "Invalid enrollment details")
        return redirect('student_home')
    
    # Fixed amount - set in view, not in model
    amount = ENROLLMENT_AMOUNT
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Simulate payment processing
            payment_mode = "card"
            
            # Create enrollment record
            enrollment = tbl_student_enrolment.objects.create(
                studentid=student,
                enrolled_batchid=batch,
                course_status='active',
                enrollment_date=timezone.now(),
                is_active_student='yes'
            )
            
            # Create payment record with amount from view
            payment = tbl_payment.objects.create(
                student_enrol_id=enrollment,
                paymentdate=date.today(),
                payment_mode="card",
                paymentstatus='completed',
                amount=amount
            )
            
            # Clear session data
            del request.session['enroll_course_id']
            del request.session['enroll_batch_id']
            
            messages.success(request, f'Successfully enrolled in {course.coursename}')
            return redirect('student_home')
        else:
            messages.error(request, "Please correct the payment details")
    else:
        form = PaymentForm()
    
    context = {
        'form': form,
        'course': course,
        'batch': batch,
        'student': student,
        'amount': amount,
    }
    return render(request, 'payment_page.html', context)


def payment_success(request, enrollment_id):
    """Step 3: Show payment and enrollment success"""
    
    enrollment = get_object_or_404(
        tbl_student_enrolment.objects.select_related(
            'studentid', 
            'enrolled_batchid__course'
        ), 
        id=enrollment_id
    )
    
    # Get payment details
    payment = get_object_or_404(
        tbl_payment, 
        student_enrol_id=enrollment_id
    )
    
    context = {
        'enrollment': enrollment,
        'payment': payment,
    }
    return render(request, 'payment_success.html', context)


def my_courses(request):
    """Display student's enrolled courses"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, "Please login to view your courses")
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
    except tbl_Student.DoesNotExist:
        messages.error(request, "Student not found")
        return redirect('student_home')
    
    # Get all active enrollments with payment details
    enrollments = tbl_student_enrolment.objects.filter(
        studentid=student,
        is_active_student='yes'
    ).select_related(
        'enrolled_batchid__course__stream'
    ).order_by('-enrollment_date')
    
    # Get payment details for each enrollment
    for enrollment in enrollments:
        try:
            enrollment.payment = tbl_payment.objects.filter(student_enrol_id=enrollment.id)
        except tbl_payment.DoesNotExist:
            enrollment.payment = None
    
    context = {
        'student': student,
        'enrollments': enrollments,
    }
    return render(request, 'my_courses.html', context)


def batch_classes(request, batch_id):
    """Display lessons and assignments for a batch with doubts"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, "Please login to access classes")
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
    except tbl_Student.DoesNotExist:
        messages.error(request, "Student not found")
        return redirect('student_home')
    
    # Get batch details
    batch = get_object_or_404(Batch.objects.select_related('course__stream'), id=batch_id)
    
    # Check if student is enrolled in this batch
    enrollment = get_object_or_404(
        tbl_student_enrolment, 
        studentid=student, 
        enrolled_batchid=batch,
        is_active_student='yes'
    )
    
    # Get lessons for this batch
    lessons = tbl_lessons.objects.filter(batch=batch).order_by('modulenumber')
    
    # Get doubts for each lesson
    for lesson in lessons:
        lesson.doubts = tbl_doubt.objects.filter(
            lesson_id=lesson,
            student_enrolment_id__enrolled_batchid=batch
        ).select_related(
            'student_enrolment_id__studentid'
        ).order_by('-date_submitted')
        lesson.doubt_count = lesson.doubts.count()
    
    # Get assignments for this batch
    assignments = tbl_assignment.objects.filter(batch=batch).order_by('-uploaddate')
    
    # Check for submitted assignments
    submitted_assignments = tbl_assignmentstudent.objects.filter(
        student=student,
        assignment__in=assignments
    ).values_list('assignment_id', flat=True)
    
    # Add overdue status to assignments
    today = date.today()
    for assignment in assignments:
        assignment.is_overdue = assignment.duedate < today
    
    # Get submission details for each assignment
    assignment_submissions = {}
    for assignment in assignments:
        try:
            submission = tbl_assignmentstudent.objects.get(
                student=student,
                assignment=assignment
            )
            assignment_submissions[assignment.id] = submission
        except tbl_assignmentstudent.DoesNotExist:
            assignment_submissions[assignment.id] = None
    
    context = {
        'batch': batch,
        'enrollment': enrollment,
        'lessons': lessons,
        'assignments': assignments,
        'submitted_assignments': submitted_assignments,
        'assignment_submissions': assignment_submissions,
    }
    
    return render(request, 'batch_classes.html', context)


def submit_assignment(request, batch_id, assignment_id):
    """Submit an assignment"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, "Please login to submit assignment")
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        assignment = get_object_or_404(tbl_assignment, id=assignment_id, batch_id=batch_id)
        batch = get_object_or_404(Batch, id=batch_id)
    except tbl_Student.DoesNotExist:
        messages.error(request, "Student not found")
        return redirect('student_home')
    except tbl_assignment.DoesNotExist:
        messages.error(request, "Assignment not found")
        return redirect('batch_classes', batch_id=batch_id)
    
    # Check if already submitted
    if tbl_assignmentstudent.objects.filter(student=student, assignment=assignment).exists():
        messages.error(request, 'You have already submitted this assignment.')
        return redirect('batch_classes', batch_id=batch_id)
    
    # Get today's date for comparison
    today = date.today()
    
    # Check if overdue
    if assignment.duedate < today:
        messages.error(request, 'Assignment submission deadline has passed.')
        return redirect('batch_classes', batch_id=batch_id)
    
    # Calculate days left for display
    days_left = (assignment.duedate - today).days
    
    if request.method == 'POST':
        form = AssignmentSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.student = student
            submission.assignment = assignment
            submission.submitteddate = timezone.now()
            submission.save()
            
            messages.success(request, 'Assignment submitted successfully!')
            return redirect('batch_classes', batch_id=batch_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AssignmentSubmissionForm()
    
    context = {
        'form': form,
        'assignment': assignment,
        'batch': batch,
        'student': student,
        'today': today,
        'days_left': days_left,
    }
    
    return render(request, 'submit_assignment.html', context)


def download_assignment_file(request, assignment_id):
    """Download teacher's assignment file"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, "Please login to download files")
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        assignment = get_object_or_404(tbl_assignment, id=assignment_id)
        
        # Check if student is enrolled in this batch
        enrollment = tbl_student_enrolment.objects.get(
            studentid=student,
            enrolled_batchid=assignment.batch,
            is_active_student='yes'
        )
        
        if assignment.assignmentupload:
            file_path = assignment.assignmentupload.path
            if os.path.exists(file_path):
                response = FileResponse(open(file_path, 'rb'))
                response['Content-Type'] = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response
            else:
                messages.error(request, 'File not found on server')
        else:
            messages.error(request, 'No file attached to this assignment')
        
        return redirect('batch_classes', batch_id=assignment.batch.id)
        
    except tbl_Student.DoesNotExist:
        messages.error(request, 'Student not found')
        return redirect('student_login')
    except tbl_student_enrolment.DoesNotExist:
        messages.error(request, 'You are not enrolled in this batch')
        return redirect('my_courses')
    except Exception as e:
        messages.error(request, f'Error downloading file: {str(e)}')
        return redirect('my_courses')


@csrf_exempt
def ask_doubt(request):
    """Handle doubt submission via AJAX"""
    if request.method == 'POST':
        student_id = request.session.get('studentid')
        
        if not student_id:
            return JsonResponse({'status': 'error', 'message': 'Please login first'})
        
        try:
            student = tbl_Student.objects.get(id=student_id)
            lesson_id = request.POST.get('lesson_id')
            enrollment_id = request.POST.get('enrollment_id')
            description = request.POST.get('description')
            
            if not description:
                return JsonResponse({'status': 'error', 'message': 'Please enter your doubt'})
            
            if not lesson_id:
                return JsonResponse({'status': 'error', 'message': 'Lesson not specified'})
            
            if not enrollment_id:
                return JsonResponse({'status': 'error', 'message': 'Enrollment not found'})
            
            # Get enrollment and lesson
            enrollment = tbl_student_enrolment.objects.get(
                id=enrollment_id, 
                studentid=student,
                is_active_student='yes'
            )
            lesson = tbl_lessons.objects.get(id=lesson_id)
            
            # Check if lesson belongs to the student's batch
            if lesson.batch.id != enrollment.enrolled_batchid.id:
                return JsonResponse({'status': 'error', 'message': 'Invalid lesson for this batch'})
            
            # Create doubt
            doubt = tbl_doubt.objects.create(
                description=description,
                student_enrolment_id=enrollment,
                lesson_id=lesson,
                date_submitted=timezone.now()
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Doubt submitted successfully',
                'doubt_id': doubt.id
            })
            
        except tbl_student_enrolment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Enrollment not found or inactive'})
        except tbl_lessons.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lesson not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


def mark_lesson_viewed(request, lesson_id):
    """Mark a lesson as viewed (optional - if you want to track progress)"""
    if request.method == 'POST':
        student_id = request.session.get('studentid')
        
        if not student_id:
            return JsonResponse({'status': 'error', 'message': 'Not logged in'})
        
        try:
            student = tbl_Student.objects.get(id=student_id)
            lesson = get_object_or_404(tbl_lessons, id=lesson_id)
            
            # You can create a LessonProgress model if needed
            # For now, just return success
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


def cancel_enrollment(request, enrollment_id):
    """Cancel/withdraw from a course"""
    if request.method == 'POST':
        student_id = request.session.get('studentid')
        
        if not student_id:
            messages.error(request, "Please login")
            return redirect('student_login')
        
        enrollment = get_object_or_404(
            tbl_student_enrolment, 
            id=enrollment_id, 
            studentid_id=student_id
        )
        
        # Soft delete - mark as inactive
        enrollment.is_active_student = 'no'
        enrollment.save()
        
        course_name = enrollment.enrolled_batchid.course.coursename
        messages.success(request, f'Successfully withdrawn from {course_name}')
    
    return redirect('my_courses')


def get_lesson_doubts(request, lesson_id):
    """API endpoint to get doubts for a specific lesson (for AJAX refresh)"""
    if request.method == 'GET':
        student_id = request.session.get('studentid')
        
        if not student_id:
            return JsonResponse({'status': 'error', 'message': 'Not logged in'})
        
        try:
            student = tbl_Student.objects.get(id=student_id)
            lesson = get_object_or_404(tbl_lessons, id=lesson_id)
            
            # Check if student is enrolled in this batch
            enrollment = tbl_student_enrolment.objects.get(
                studentid=student,
                enrolled_batchid=lesson.batch,
                is_active_student='yes'
            )
            
            # Get doubts for this lesson
            doubts = tbl_doubt.objects.filter(
                lesson_id=lesson
            ).select_related(
                'student_enrolment_id__studentid'
            ).order_by('-date_submitted')
            
            doubts_data = []
            for doubt in doubts:
                doubts_data.append({
                    'id': doubt.id,
                    'description': doubt.description,
                    'date_submitted': doubt.date_submitted.strftime('%d %b %Y, %I:%M %p'),
                    'student_name': doubt.student_enrolment_id.studentid.first_name + ' ' + doubt.student_enrolment_id.studentid.last_name,
                    'student_initial': doubt.student_enrolment_id.studentid.first_name[0].upper() if doubt.student_enrolment_id.studentid.first_name else '?',
                    'answer': doubt.answer,
                    'answer_submitted': doubt.answer_submitted.strftime('%d %b %Y, %I:%M %p') if doubt.answer_submitted else None,
                    'has_answer': bool(doubt.answer)
                })
            
            return JsonResponse({
                'status': 'success',
                'doubts': doubts_data,
                'count': len(doubts_data)
            })
            
        except tbl_student_enrolment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Not enrolled in this batch'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def view_certificate(request, enrollment_id):
    """Display certificate as HTML page for viewing/printing"""
    
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, 'Please login to access certificate')
        return redirect('student_login')
    
    try:
        # Get enrollment details
        enrollment = tbl_student_enrolment.objects.select_related(
            'studentid',
            'enrolled_batchid',
            'enrolled_batchid__course',
            'enrolled_batchid__course__stream'
        ).get(id=enrollment_id, studentid_id=student_id, is_active_student='yes')
        
        # Check if final mark exists in tbl_final
        try:
            final_result = tbl_final.objects.get(student_enrolment_id=enrollment)
            final_mark = final_result.final_mark
            
            # Calculate total possible marks (assignments + exams)
            assignments = tbl_assignment.objects.filter(batch=enrollment.enrolled_batchid)
            total_assignment_marks = sum(assignment.totalmarks for assignment in assignments)
            
            exam_results = tbl_student_examresult.objects.filter(student_enrol_id=enrollment)
            total_exam_marks = sum(result.examid.totalscore for result in exam_results)
            
            total_marks = total_assignment_marks + total_exam_marks
            
            # Calculate percentage based on total marks
            percentage = (final_mark / total_marks * 100) if total_marks > 0 else 0
            
            # Determine grade based on percentage
            if percentage >= 90:
                grade = 'A+'
                grade_description = 'Outstanding'
            elif percentage >= 80:
                grade = 'A'
                grade_description = 'Excellent'
            elif percentage >= 70:
                grade = 'B+'
                grade_description = 'Very Good'
            elif percentage >= 60:
                grade = 'B'
                grade_description = 'Good'
            elif percentage >= 50:
                grade = 'C'
                grade_description = 'Satisfactory'
            elif percentage >= 40:
                grade = 'D'
                grade_description = 'Pass'
            else:
                grade = 'F'
                grade_description = 'Needs Improvement'
            
            # Get completion date
            completion_date = datetime.date.today()
            
            context = {
                'student': enrollment.studentid,
                'course': enrollment.enrolled_batchid.course,
                'stream': enrollment.enrolled_batchid.course.stream,
                'batch': enrollment.enrolled_batchid,
                'final_mark': final_mark,
                'total_marks': total_marks,
                'percentage': round(percentage, 2),
                'grade': grade,
                'grade_description': grade_description,
                'completion_date': completion_date,
                'website_name': 'NOVALEARN',
                'certificate_id': f"CERT-{enrollment.id}-{enrollment.studentid.id}-{completion_date.year}",
            }
            
            return render(request, 'certificate_view.html', context)
            
        except tbl_final.DoesNotExist:
            messages.error(request, 'Certificate not available yet. Final marks not uploaded.')
            return redirect('batch_exams', batch_id=enrollment.enrolled_batchid.id)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('my_courses')

def add_course_review(request, course_id, batch_id):
    """Add or edit review for a course"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, 'Please login to add a review')
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        course = get_object_or_404(Course, id=course_id)
        batch = get_object_or_404(Batch, id=batch_id)
        
        # Check if student is enrolled and completed the course
        enrollment = get_object_or_404(
            tbl_student_enrolment,
            studentid=student,
            enrolled_batchid=batch,
            is_active_student='yes'
        )
        
        # Check if final mark exists (course completed)
        try:
            final_result = tbl_final.objects.get(student_enrolment_id=enrollment)
        except tbl_final.DoesNotExist:
            messages.error(request, 'You can only review courses after completion')
            return redirect('batch_exams', batch_id=batch_id)
        
        # Check if review already exists
        existing_review = tbl_course_review.objects.filter(
            student=student,
            course=course
        ).first()
        
        if request.method == 'POST':
            rating = request.POST.get('rating')
            review_text = request.POST.get('review_text')
            
            if not rating or not review_text:
                messages.error(request, 'Please provide both rating and review')
                return redirect('add_course_review', course_id=course_id, batch_id=batch_id)
            
            if existing_review:
                # Update existing review
                existing_review.rating = rating
                existing_review.review_text = review_text
                existing_review.created_at = timezone.now()
                existing_review.save()
                messages.success(request, 'Thank you for updating your review!')
            else:
                # Create new review
                tbl_course_review.objects.create(
                    student=student,
                    course=course,
                    batch=batch,
                    rating=rating,
                    review_text=review_text
                )
                messages.success(request, 'Thank you for your feedback!')
            
            return redirect('batch_exams', batch_id=batch_id)
        
        context = {
            'student': student,
            'course': course,
            'batch': batch,
            'existing_review': existing_review,
        }
        return render(request, 'add_review.html', context)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('batch_exams', batch_id=batch_id)

def student_profile(request):
    """Display and edit student profile"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, 'Please login to access your profile')
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.select_related('login').get(id=student_id)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'update_profile':
                # Update profile information (except email)
                student.first_name = request.POST.get('first_name')
                student.last_name = request.POST.get('last_name')
                student.phno = request.POST.get('phno')
                student.dob = request.POST.get('dob')
                student.gender = request.POST.get('gender')
                student.educational_background = request.POST.get('educational_background')
                
                # Handle profile picture upload
                if 'profile_pic' in request.FILES:
                    student.profile_pic = request.FILES['profile_pic']
                
                student.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('student_profile')
                
            elif action == 'change_password':
                # Change password
                current_password = request.POST.get('current_password')
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')
                
                # Verify current password (plain text comparison)
                if student.login.password != current_password:
                    messages.error(request, 'Current password is incorrect')
                elif new_password != confirm_password:
                    messages.error(request, 'New passwords do not match')
                elif len(new_password) < 6:
                    messages.error(request, 'Password must be at least 6 characters long')
                else:
                    # Update password
                    student.login.password = new_password
                    student.login.save()
                    messages.success(request, 'Password changed successfully!')
                
                return redirect('student_profile')
        
        context = {
            'student': student,
        }
        return render(request, 'student_profile.html', context)
        
    except tbl_Student.DoesNotExist:
        messages.error(request, 'Student not found')
        return redirect('student_home')
    

def attended_exams(request):
    """Display all exams attended by the student with results"""
    student_id = request.session.get('studentid')
    
    if not student_id:
        messages.error(request, 'Please login to view attended exams')
        return redirect('student_login')
    
    try:
        student = tbl_Student.objects.get(id=student_id)
        
        # Get all enrollments for this student
        enrollments = tbl_student_enrolment.objects.filter(
            studentid=student,
            is_active_student='yes'
        ).select_related(
            'enrolled_batchid',
            'enrolled_batchid__course',
            'enrolled_batchid__course__stream'
        ).order_by('-enrollment_date')
        
        # Prepare data for each enrollment
        exam_data = []
        total_exams_attended = 0
        total_score = 0
        total_possible = 0
        
        for enrollment in enrollments:
            # Get all exam results for this enrollment
            exam_results = tbl_student_examresult.objects.filter(
                student_enrol_id=enrollment
            ).select_related('examid')
            
            if exam_results.exists():
                enrollment_data = {
                    'enrollment': enrollment,
                    'course': enrollment.enrolled_batchid.course,
                    'batch': enrollment.enrolled_batchid,
                    'exams': [],
                    'total_obtained': 0,
                    'total_possible': 0,
                    'average_percentage': 0,
                }
                
                for result in exam_results:
                    exam_total = result.examid.totalscore
                    percentage = (result.total_score_obtained / exam_total * 100) if exam_total > 0 else 0
                    
                    exam_info = {
                        'exam': result.examid,
                        'obtained': result.total_score_obtained,
                        'total': exam_total,
                        'percentage': round(percentage, 2),
                        'status': 'Pass' if percentage >= 40 else 'Fail'
                    }
                    
                    enrollment_data['exams'].append(exam_info)
                    enrollment_data['total_obtained'] += result.total_score_obtained
                    enrollment_data['total_possible'] += exam_total
                    
                    total_score += result.total_score_obtained
                    total_possible += exam_total
                    total_exams_attended += 1
                
                # Calculate average for this enrollment
                if enrollment_data['total_possible'] > 0:
                    enrollment_data['average_percentage'] = round(
                        (enrollment_data['total_obtained'] / enrollment_data['total_possible'] * 100), 2
                    )
                
                # Check if certificate is available (final mark exists)
                try:
                    final_mark = tbl_final.objects.get(student_enrolment_id=enrollment)
                    enrollment_data['certificate_available'] = True
                    enrollment_data['final_mark'] = final_mark.final_mark
                except tbl_final.DoesNotExist:
                    enrollment_data['certificate_available'] = False
                    enrollment_data['final_mark'] = None
                
                exam_data.append(enrollment_data)
        
        # Calculate overall statistics
        overall_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0
        
        context = {
            'student': student,
            'exam_data': exam_data,
            'total_exams_attended': total_exams_attended,
            'total_score': total_score,
            'total_possible': total_possible,
            'overall_percentage': round(overall_percentage, 2),
            'enrollment_count': len(exam_data),
        }
        
        return render(request, 'attended_exams.html', context)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('student_home')