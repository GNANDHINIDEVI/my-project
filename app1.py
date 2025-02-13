from flask import Flask, render_template, request, redirect, url_for, flash,session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash  # To hash and check passwords
import random
import smtplib  # Email library
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'SUPERKEY'

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Gnandy1611@localhost/timetable'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models

class User(db.Model):  # Model for users (for login and registration)
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20),nullable=False,default='professor')

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(100), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    slot_time = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    professor = db.Column(db.String(100), nullable=False)

class Professor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    time_slot = db.Column(db.String(100), nullable=False)
    subjects = db.Column(db.String(200), nullable=False)  # comma-separated subjects
    hours = db.Column(db.Integer, nullable=False)

class LeaveApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    professor_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    slot_time = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")

class LabHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(100), nullable=False)
    lab_subject = db.Column(db.String(100), nullable=False)
    lab_hour_count = db.Column(db.Integer, nullable=False)

# Role-Based Access Control Decorators
def admin_required(func):
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Access denied. Admins only.")
            return redirect(url_for('home'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

def professor_required(func):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'professor':
            flash("Access denied.")
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role  # Store role in session
            flash("Login successful!")
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'professor':
                return redirect(url_for('professor_dashboard'))
            else:
                flash("Role not recognized. Please contact admin.")
                return redirect(url_for('login'))
        else:
            flash("Invalid credentials. Please try again.")

    return render_template('login.html')

@app.route('/admin_dashboard')
@admin_required  # Access only for admin
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/professor_dashboard')
@professor_required  # Access only for professor
def professor_dashboard():
    return render_template('professor_dashboard.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash("You have been logged out.")
    return redirect(url_for('login'))



# Routes
@app.route('/home')
def home():
    if 'user_id' not in session:  # Check if user is logged in
        return redirect(url_for('login'))  # Redirect to login if not logged in
    return render_template('home.html')  # Show the page if logged in


@app.route('/input_professors', methods=['GET', 'POST'])
def input_professors():
     if 'user_id' not in session:
        return redirect(url_for('login'))
    
     if request.method == 'POST':
         name = request.form['name']
         time_slot = request.form['time_slot']
         subjects = request.form['subjects'].split(',')
         hours_per_week = int(request.form['hours'])
 
         # Save to database
         professor = Professor(name=name, time_slot=time_slot, subjects=subjects, hours=hours_per_week)
         db.session.add(professor)
         db.session.commit()

         flash("Professor added successfully!")
         return redirect(url_for('input_professors'))

    # Fetch professors from the database
     professors = Professor.query.all()
     return render_template('input_professors.html', professors=professors)

@app.route('/input_classes', methods=['GET', 'POST'])
def input_classes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get 'classes' from session or initialize it if it doesn't exist
    classes = session.get('classes', [])
    
    if request.method == 'POST':
        class_name = request.form['class_name']
        subjects = request.form['subjects'].split(',')
        hours_subjects = request.form['hours_subjects'].split(',')

        if len(subjects) != len(hours_subjects):
            flash("The number of subjects must match the number of hours provided.")
            return redirect(url_for('input_classes'))

        # Create a dictionary with subject and hours
        subjects_dict = {subject.strip(): int(hours.strip()) for subject, hours in zip(subjects, hours_subjects)}
        classes.append({"name": class_name, "subjects": subjects_dict})
        session['classes'] = classes  # Save back to session
        session.modified = True
        flash("Class added successfully!")
        return redirect(url_for('input_classes'))

    return render_template('input_classes.html', classes=classes)

    
@app.route('/input_lab_hours', methods=['GET', 'POST'])
def input_lab_hours():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Fetch 'classes' from session or initialize an empty list
    classes = session.get('classes', [])
    
    if request.method == 'POST':
        class_name = request.form['class_name']
        lab_subject = request.form['lab_subject']
        lab_hours_count = int(request.form['lab_hours'])  # Number of lab hours

        # Save lab hours to the database
        lab_hours = LabHours(class_name=class_name, lab_subject=lab_subject, lab_hour_count=lab_hours_count)
        db.session.add(lab_hours)
        db.session.commit()

        flash("Lab hours added successfully!")
        return redirect(url_for('input_lab_hours'))
    
    # Fetch existing lab hours from the database
    lab_hours_data = LabHours.query.all()

    # Pass 'classes' and 'lab_hours_data' to the template
    return render_template('input_lab_hours.html', lab_hours=lab_hours_data, classes=classes)

# Routes
@app.route('/generate_timetable', methods=['GET', 'POST'])
def generate_timetable():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    slots_per_day = 5

    # Fetch classes from session
    classes = session.get("classes", [])
    if not classes:
        flash("No classes found. Please add classes before generating the timetable.")
        return redirect(url_for("input_classes"))

    # Initialize timetable dictionary
    timetable = {cls["name"]: [["" for _ in range(slots_per_day)] for _ in range(len(days))] for cls in classes}
    professors = Professor.query.all()
    lab_hours = LabHours.query.all()

    # Allocate lab hours first
    for lab in lab_hours:
        class_name = lab.class_name
        lab_subject = lab.lab_subject
        remaining_hours = lab.lab_hour_count

        if class_name not in timetable:
            flash(f"Class {class_name} is not found in the timetable. Skipping lab allocation.")
            continue

        while remaining_hours > 0:
            day = random.randint(0, len(days) - 1)
            slot = random.randint(0, slots_per_day - 1)

            if timetable[class_name][day][slot] == "":
                timetable[class_name][day][slot] = f"Lab ({lab_subject})"
                remaining_hours -= 1

    # Allocate subject hours
    for cls in classes:
        class_name = cls["name"]
        subjects = cls["subjects"]

        if class_name not in timetable:
            flash(f"Class {class_name} is not found in the timetable. Skipping subject allocation.")
            continue

        for subject, required_hours in subjects.items():
            while required_hours > 0:
                day = random.randint(0, len(days) - 1)
                slot = random.randint(0, slots_per_day - 1)

                if timetable[class_name][day][slot] == "":
                    available_professors = [prof for prof in professors if subject in prof.subjects and prof.hours > 0]

                    if available_professors:
                        professor = random.choice(available_professors)
                        timetable[class_name][day][slot] = f"{subject} ({professor.name})"
                        professor.hours -= 1
                        required_hours -= 1

    session["timetable"] = timetable
    flash("Timetable generated successfully!")
    return render_template("generate_timetable.html", timetable=timetable, days=days, slots_per_day=slots_per_day)

@app.route('/save_timetable', methods=['POST'])
def save_timetable():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    timetable = session.get('timetable')
    if not timetable:
        flash("Generate the timetable before saving.")
        return redirect(url_for('generate_timetable'))

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    for class_name, schedule in timetable.items():
        for day_idx, day_schedule in enumerate(schedule):
            for slot_idx, lecture in enumerate(day_schedule):
                if lecture:
                    subject_professor = lecture.split(" (")
                    subject = subject_professor[0]
                    professor = subject_professor[1][:-1] if len(subject_professor) > 1 else ""
                    slot_time = f"{8 + slot_idx}:40-{8 + slot_idx + 1}:30"

                    entry = Timetable(
                        class_name=class_name,
                        day=days[day_idx],
                        slot_time=slot_time,
                        subject=subject,
                        professor=professor
                    )
                    db.session.add(entry)

    db.session.commit()
    flash("Timetable saved successfully!")
    return redirect(url_for('home'))

@app.route('/view_saved_timetables')
def view_timetable_from_db():
    # Filter to show only generated timetables (assuming you have a status or field for generated timetables)
    timetables = Timetable.query.filter_by(status='Generated').all()
    
    return render_template('view_saved_timetables.html', timetables=timetables)

@app.route('/apply_leave', methods=['GET', 'POST'])
def apply_leave():
    if request.method == 'POST':
        professor_name = request.form['professor_name']
        date = request.form['date']
        slot_time = request.form['slot_time']
        reason = request.form['reason']

        leave = LeaveApplication(
            professor_name=professor_name,
            date=date,
            slot_time=slot_time,
            reason=reason,
            status="Pending"
        )
        db.session.add(leave)
        db.session.commit()
        flash("Leave application submitted!")
        return redirect(url_for('apply_leave'))
    
    # Fetch professors from the database
    professors = Professor.query.all()
    return render_template('apply_leave.html', professors=[prof.name for prof in professors])

@app.route('/approve_leaves', methods=['GET', 'POST'])
def approve_leaves():
    if request.method == 'POST':
        for leave in LeaveApplication.query.filter_by(status="Pending").all():
            action = request.form.get(f'action_{leave.id}')
            alternate_professor_name = request.form.get(f'alternate_professor_{leave.id}')
            available_hours = request.form.get(f'available_hours_{leave.id}')

            if action == 'Approve':
                leave.status = 'Approved'
                db.session.commit()

                # Allocate alternate professor
                allocate_alternate_professor(leave, alternate_professor_name, int(available_hours))

            elif action == 'Reject':
                leave.status = 'Rejected'
                db.session.commit()

        flash("Leave requests processed!")
        return redirect(url_for('approve_leaves'))

    leaves = LeaveApplication.query.filter_by(status="Pending").all()

    # Get available professors (those who are not on leave)
    available_professors = Professor.query.filter(Professor.hours > 0).all()

    return render_template('approve_leaves.html', leaves=leaves, available_professors=available_professors)

def allocate_alternate_professor(leave):
    # Find the vacant slot in the timetable
    timetable_entry = Timetable.query.filter_by(
        professor=leave.professor_name, day=leave.date.strftime("%A"), slot_time=leave.slot_time
    ).first()

    if timetable_entry:
        # Find another professor who can take this subject and is available
        subject = timetable_entry.subject
        available_professor = None

        # Fetch professors from the database
        professors_db = Professor.query.all()

        for prof in professors_db:
            if prof.name != leave.professor_name and subject in prof.subjects and prof.hours > 0:
                # Check if professor is not already scheduled in this time slot
                existing_entry = Timetable.query.filter_by(
                    professor=prof.name, day=leave.date.strftime("%A"), slot_time=leave.slot_time
                ).first()
                if not existing_entry:
                    available_professor = prof
                    break

        if available_professor:
            # Update the timetable with the new professor
            timetable_entry.professor = available_professor.name
            available_professor.hours -= 1
            db.session.commit()

            # Notify the professor on leave
            subject_message = f"Leave Approved: {subject} Class on {leave.date}"
            body_message = f"Dear {leave.professor_name},\n\nYour leave request for {leave.date} has been approved. {available_professor.name} has been assigned to your class: {subject} at {leave.slot_time}.\n\nThank you!"
            send_email(get_professor_email(leave.professor_name), subject_message, body_message)

            # Notify the replacement professor
            subject_message = f"New Assignment: {subject} Class on {leave.date}"
            body_message = f"Dear {available_professor.name},\n\nYou have been assigned to take {subject} for {leave.professor_name} on {leave.date} at {leave.slot_time}.\n\nThank you!"
            send_email(get_professor_email(available_professor.name), subject_message, body_message)

            flash(f"{available_professor.name} assigned to {timetable_entry.subject} on {leave.date}")
        else:
            flash(f"No available professor found to take {timetable_entry.subject} on {leave.date}")
    return redirect(url_for('approve_leaves'))

def send_email(to_email, subject, body):
    """Function to send email"""
    sender_email = "gnandy16112001@gmail.com"  # Replace with your actual email address
    password = "esfe ubmn xnwj rrdn"  # Replace with your email password
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, to_email, msg.as_string())

def get_professor_email(professor_name):
    professor = Professor.query.filter_by(name=professor_name).first()
    if professor:
        return professor.email
    return None  # Return None if email is not found


# Your Flask app code here

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Creates all tables defined in models
    app.run(debug=True)

