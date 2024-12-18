from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import ast
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import io
import csv
from flask import send_file
from sqlalchemy import func
from dateutil.relativedelta import relativedelta
from datetime import datetime
import humanize

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test_platform.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

db = SQLAlchemy(app)

@app.template_filter('eval')
def eval_filter(s):
    try:
        return ast.literal_eval(s)
    except:
        return []

# Models
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    test_results = db.relationship('TestResult', backref='student', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(500), nullable=False)
    options = db.Column(db.String(1000), nullable=False)  # Store as JSON string

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    answers = db.Column(db.String(1000), nullable=False)  # Store as JSON string
    date_taken = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please log in first.')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_test', methods=['POST'])
def start_test():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    
    if not first_name or not last_name:
        flash('Please enter both first and last name')
        return redirect(url_for('index'))
    
    student = Student(first_name=first_name, last_name=last_name)
    db.session.add(student)
    db.session.commit()
    
    session['student_id'] = student.id
    return redirect(url_for('test'))

@app.route('/test')
def test():
    if 'student_id' not in session:
        return redirect(url_for('index'))
    questions = Question.query.all()
    return render_template('test.html', questions=questions)

@app.route('/submit_test', methods=['POST'])
def submit_test():
    if 'student_id' not in session:
        return redirect(url_for('index'))
    
    answers = request.get_json()
    questions = Question.query.all()
    score = 0
    results = []
    
    for q in questions:
        student_answer = answers.get(str(q.id))
        is_correct = student_answer == q.correct_answer
        if is_correct:
            score += 1
        results.append({
            'question': q.question_text,
            'student_answer': student_answer,
            'correct_answer': q.correct_answer,
            'is_correct': is_correct
        })
    
    test_result = TestResult(
        student_id=session['student_id'],
        score=score,
        answers=str(results)
    )
    db.session.add(test_result)
    db.session.commit()
    
    return jsonify({
        'score': score,
        'total': len(questions),
        'results': results
    })

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['admin_logged_in'] = True
            flash('Successfully logged in!')
            return redirect(url_for('admin'))
        flash('Invalid username or password')
        return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Successfully logged out.')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin():
    results = TestResult.query.order_by(TestResult.date_taken.desc()).all()
    return render_template('admin.html', results=results)

@app.route('/add_question', methods=['GET', 'POST'])
@admin_required
def add_question():
    if request.method == 'POST':
        question_text = request.form.get('question')
        correct_answer = request.form.get('correct_answer')
        options = request.form.getlist('options[]')
        
        new_question = Question(
            question_text=question_text,
            correct_answer=correct_answer,
            options=str(options)
        )
        db.session.add(new_question)
        db.session.commit()
        flash('Question added successfully!')
        return redirect(url_for('manage_questions'))
    
    return render_template('add_question.html')

@app.route('/manage_questions')
@admin_required
def manage_questions():
    questions = Question.query.all()
    for question in questions:
        question.options = ast.literal_eval(question.options)
    return render_template('manage_questions.html', questions=questions)

@app.route('/edit_question/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_question(id):
    question = Question.query.get_or_404(id)
    
    if request.method == 'POST':
        question.question_text = request.form.get('question')
        question.correct_answer = request.form.get('correct_answer')
        question.options = str(request.form.getlist('options[]'))
        
        db.session.commit()
        flash('Question updated successfully!')
        return redirect(url_for('manage_questions'))
    
    return render_template('edit_question.html', question=question)

@app.route('/delete_question/<int:id>')
@admin_required
def delete_question(id):
    question = Question.query.get_or_404(id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully!')
    return redirect(url_for('manage_questions'))

# New admin routes
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Get statistics
    total_students = Student.query.count()
    total_questions = Question.query.count()
    total_tests = TestResult.query.count()
    
    # Calculate average score
    avg_score = db.session.query(func.avg(TestResult.score)).scalar() or 0
    avg_score = (avg_score / total_questions * 100) if total_questions > 0 else 0
    
    # Get performance data for chart
    recent_results = TestResult.query.order_by(TestResult.date_taken.desc()).limit(10).all()
    performance_labels = [result.date_taken.strftime('%Y-%m-%d') for result in recent_results]
    performance_data = [(result.score / total_questions * 100) for result in recent_results]
    
    # Get recent activities
    recent_activities = []
    recent_tests = TestResult.query.order_by(TestResult.date_taken.desc()).limit(5).all()
    for test in recent_tests:
        recent_activities.append({
            'description': f"Test Completed",
            'details': f"{test.student.first_name} {test.student.last_name} scored {test.score}/{total_questions}",
            'time_ago': humanize.naturaltime(datetime.utcnow() - test.date_taken)
        })
    
    return render_template('admin_dashboard.html',
                         total_students=total_students,
                         total_questions=total_questions,
                         total_tests=total_tests,
                         avg_score=avg_score,
                         performance_labels=performance_labels,
                         performance_data=performance_data,
                         recent_activities=recent_activities)

@app.route('/admin/analytics')
@admin_required
def analytics():
    return render_template('analytics.html')

@app.route('/admin/manage_students')
@admin_required
def manage_students():
    students = Student.query.all()
    return render_template('manage_students.html', students=students)

@app.route('/admin/system_settings')
@admin_required
def system_settings():
    return render_template('system_settings.html')

@app.route('/admin/import_questions', methods=['GET', 'POST'])
@admin_required
def import_questions():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # Read CSV file
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                
                questions_added = 0
                for row in csv_input:
                    question = Question(
                        question_text=row['question_text'],
                        options=str(row['options'].split('|')),
                        correct_answer=row['correct_answer']
                    )
                    db.session.add(question)
                    questions_added += 1
                
                db.session.commit()
                flash(f'Successfully imported {questions_added} questions!')
                return redirect(url_for('manage_questions'))
            except Exception as e:
                flash(f'Error importing questions: {str(e)}')
                return redirect(request.url)
    
    return render_template('import_questions.html')

@app.route('/admin/export_results')
@admin_required
def export_results():
    # Create CSV file
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Student Name', 'Score', 'Date Taken', 'Questions', 'Answers'])
    
    # Write data
    results = TestResult.query.order_by(TestResult.date_taken.desc()).all()
    for result in results:
        writer.writerow([
            f"{result.student.first_name} {result.student.last_name}",
            result.score,
            result.date_taken.strftime('%Y-%m-%d %H:%M:%S'),
            len(ast.literal_eval(result.answers)),
            result.answers
        ])
    
    # Create response
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=test_results.csv'}
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
