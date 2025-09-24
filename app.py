
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-strong-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    income = db.Column(db.Float, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)


# Signup route and logic
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        age = request.form.get('age')
        income = request.form.get('income')
        password = request.form.get('password')
        if not password:
            return render_template('signup.html', error='Password is required.')
        # Check if user already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template('signup.html', error='Email already registered.')
        password_hash = generate_password_hash(password) if password else None
        user = User(name=name, email=email, age=int(age), income=float(income), password_hash=password_hash)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')





# Session management for login state
from flask import session, redirect, url_for

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template('login.html', error='Email not found. Please sign up first.')
        if not check_password_hash(user.password_hash, password):
            return render_template('login.html', error='Incorrect password.')
        session['user_id'] = user.id
        return redirect(url_for('dashboard'))
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    return render_template('dashboard.html')

@app.route('/interactive')
def interactive():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    return render_template('interactive.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    if request.method == 'POST':
        return upload_file()
    return render_template('upload.html')

@app.route('/analytics')
def analytics():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    return render_template('analytics.html')


# Update profile
@app.route('/update_profile', methods=['POST'])
def update_profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    name = request.form.get('name')
    email = request.form.get('email')
    age = request.form.get('age')
    income = request.form.get('income')
    # Check for duplicate email (if changed)
    if email != user.email and User.query.filter_by(email=email).first():
        return render_template('settings.html', user=user, error='Email already registered.')
    user.name = name
    user.email = email
    user.age = int(age) if age else user.age
    user.income = float(income) if income else user.income
    db.session.commit()
    return render_template('settings.html', user=user, success='Profile updated successfully.')

# Change password
@app.route('/change_password', methods=['POST'])
def change_password():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    if not check_password_hash(user.password_hash, current_password):
        return render_template('settings.html', user=user, error='Current password is incorrect.')
    if new_password != confirm_password:
        return render_template('settings.html', user=user, error='New passwords do not match.')
    if not new_password:
        return render_template('settings.html', user=user, error='New password cannot be empty.')
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return render_template('settings.html', user=user, success='Password changed successfully.')

# Delete account
@app.route('/delete_account', methods=['POST'])
def delete_account():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    db.session.delete(user)
    db.session.commit()
    session.pop('user_id', None)
    return redirect(url_for('signup'))

@app.route('/settings')
def settings():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    user = User.query.get(session['user_id'])
    return render_template('settings.html', user=user)


@app.route('/profile')
def profile():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/api/users', methods=['POST'])
def add_user():
    data = request.get_json()
    user = User(
        name=data.get('name'),
        email=data.get('email'),
        age=int(data.get('age')),
        income=float(data.get('income'))
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User added', 'user': {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'age': user.age,
        'income': user.income
    }})

@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify({'users': [
        {'id': u.id, 'name': u.name, 'email': u.email, 'age': u.age, 'income': u.income}
        for u in users
    ]})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    if file:
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({'message': f'File {filename} uploaded successfully'})
    return jsonify({'message': 'File upload failed'}), 400

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
