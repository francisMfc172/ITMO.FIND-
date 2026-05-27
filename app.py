import random
import string
import os 
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'png', 'jpg', 'jpeg', 'pptx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__)
app.secret_key = "itmo-find-secret-key-123"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///itmo.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    join_code = db.Column(db.String(8), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    members = db.relationship('Enrollment', backref='class_ref', lazy=True)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    filename = db.Column(db.String(300), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Homework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(1000), nullable=True)
    due_date = db.Column(db.String(50), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    questions = db.relationship('Question', backref='test', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
def generate_join_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Welcome back, " + user.username + "!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == 'teacher':
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
    else:
        enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
        classes = [Class.query.get(e.class_id) for e in enrollments]
    return render_template("dashboard.html", classes=classes)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/create-class", methods=['GET', 'POST'])
@login_required
def create_class():
    if current_user.role != 'teacher':
        flash("Only teachers can create classes.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        join_code = generate_join_code()
        new_class = Class(name=name, subject=subject, join_code=join_code, teacher_id=current_user.id)
        db.session.add(new_class)
        db.session.commit()
        flash("Class created! Join code: " + join_code, "success")
        return redirect(url_for("dashboard"))
    return render_template("create_class.html")

@app.route("/join-class", methods=["GET", "POST"])
@login_required
def join_class():
    if current_user.role != "student":
        flash("Only students can join classes.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        join_code = request.form.get("join_code")
        class_ = Class.query.filter_by(join_code=join_code).first()
        if not class_:
            flash("Invalid join code. Try again.", "danger")
            return redirect(url_for("join_class"))
        already = Enrollment.query.filter_by(user_id=current_user.id, class_id=class_.id).first()
        if already:
            flash("You are already in this class.", "info")
            return redirect(url_for("dashboard"))
        enrollment = Enrollment(user_id=current_user.id, class_id=class_.id)
        db.session.add(enrollment)
        db.session.commit()
        flash("You joined " + class_.name + "!", "success")
        return redirect(url_for("dashboard"))
    return render_template("join_class.html")

@app.route("/class/<int:class_id>")
@login_required
def view_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    enrollments = Enrollment.query.filter_by(class_id=class_id).all()
    members = [User.query.get(e.user_id) for e in enrollments]
    teacher = User.query.get(class_.teacher_id)
    books = Book.query.filter_by(class_id=class_id).all()
    homeworks = Homework.query.filter_by(class_id=class_id).all()
    tests = Test.query.filter_by(class_id=class_id).all()
    return render_template("view_class.html", class_=class_, members=members, teacher=teacher, books=books, homeworks=homeworks, tests=tests)


@app.route("/class/<int:class_id>/add-book", methods=["GET", "POST"])
@login_required
def add_book(class_id):
    if current_user.role != "teacher":
        flash("Only teachers can add books.", "danger")
        return redirect(url_for("view_class", class_id=class_id))
    class_ = Class.query.get_or_404(class_id)
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Please select a file to upload.", "danger")
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash("File type not allowed. Use PDF, Word, PowerPoint or images.", "danger")
            return redirect(request.url)
        filename = secure_filename(file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        new_book = Book(title=title, description=description, filename=filename, class_id=class_id, uploaded_by=current_user.id)
        db.session.add(new_book)
        db.session.commit()
        flash("Book uploaded successfully!", "success")
        return redirect(url_for("view_class", class_id=class_id))
    return render_template("add_book.html", class_=class_)

@app.route("/class/<int:class_id>/add-homework", methods=["GET", "POST"])
@login_required
def add_homework(class_id):
    if current_user.role != "teacher":
        flash("Only teachers can add homework.", "danger")
        return redirect(url_for("view_class", class_id=class_id))
    class_ = Class.query.get_or_404(class_id)
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        new_homework = Homework(title=title, description=description, due_date=due_date, class_id=class_id, created_by=current_user.id)
        db.session.add(new_homework)
        db.session.commit()
        flash("Homework added successfully!", "success")
        return redirect(url_for("view_class", class_id=class_id))
    return render_template("add_homework.html", class_=class_)

@app.route("/class/<int:class_id>/create-test", methods=["GET", "POST"])
@login_required
def create_test(class_id):
    if current_user.role != "teacher":
        flash("Only teachers can create tests.", "danger")
        return redirect(url_for("view_class", class_id=class_id))
    class_ = Class.query.get_or_404(class_id)
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        new_test = Test(title=title, description=description, class_id=class_id, created_by=current_user.id)
        db.session.add(new_test)
        db.session.flush()
        i = 1
        while request.form.get(f"question_{i}"):
            q_text = request.form.get(f"question_{i}")
            opt_a = request.form.get(f"q{i}_a")
            opt_b = request.form.get(f"q{i}_b")
            opt_c = request.form.get(f"q{i}_c")
            opt_d = request.form.get(f"q{i}_d")
            correct = request.form.get(f"q{i}_correct")
            q = Question(test_id=new_test.id, question_text=q_text, option_a=opt_a, option_b=opt_b, option_c=opt_c, option_d=opt_d, correct_answer=correct)
            db.session.add(q)
            i += 1
        db.session.commit()
        flash("Test created successfully!", "success")
        return redirect(url_for("view_class", class_id=class_id))
    return render_template("create_test.html", class_=class_)

@app.route("/test/<int:test_id>/take", methods=["GET", "POST"])
@login_required
def take_test(test_id):
    test = Test.query.get_or_404(test_id)
    already = TestResult.query.filter_by(user_id=current_user.id, test_id=test_id).first()
    if already:
        flash("You have already taken this test. Score: " + str(already.score) + "/" + str(already.total), "info")
        return redirect(url_for("view_class", class_id=test.class_id))
    if request.method == "POST":
        score = 0
        total = len(test.questions)
        for q in test.questions:
            answer = request.form.get(f"q_{q.id}")
            if answer == q.correct_answer:
                score += 1
        result = TestResult(user_id=current_user.id, test_id=test_id, score=score, total=total)
        db.session.add(result)
        db.session.commit()
        flash("Test submitted! Your score: " + str(score) + "/" + str(total), "success")
        return redirect(url_for("view_class", class_id=test.class_id))
    return render_template("take_test.html", test=test)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port = 8000)