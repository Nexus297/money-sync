
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


# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    income = db.Column(db.Float, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    expenses = db.Column(db.Float, nullable=True)
    savings = db.Column(db.Float, nullable=True)
    debts = db.Column(db.Float, nullable=True)
    assets = db.Column(db.Float, nullable=True)
    insurance = db.Column(db.String(256), nullable=True)
    goals = db.Column(db.String(256), nullable=True)
    conversation_state = db.Column(db.String(64), nullable=True)
    conversation_data = db.Column(db.Text, nullable=True)

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename = db.Column(db.String(256), nullable=False)
    mimetype = db.Column(db.String(128), nullable=True)
    size = db.Column(db.Integer, nullable=True)
    upload_time = db.Column(db.DateTime, server_default=db.func.now())

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    state = db.Column(db.String(64), nullable=True)
    data = db.Column(db.Text, nullable=True)

# --- Schema migration helper ---
def ensure_schema():
    # Add missing columns if not present (for SQLite dev only)
    import sqlite3
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///','')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Add columns if missing
    columns = [
        ('expenses', 'REAL'),
        ('savings', 'REAL'),
        ('debts', 'REAL'),
        ('assets', 'REAL'),
        ('insurance', 'TEXT'),
        ('goals', 'TEXT'),
        ('conversation_state', 'TEXT'),
        ('conversation_data', 'TEXT')
    ]
    for col, typ in columns:
        try:
            cur.execute(f'ALTER TABLE user ADD COLUMN {col} {typ}')
        except Exception:
            pass
    # Create Upload and Conversation tables if not exist
    cur.execute('''CREATE TABLE IF NOT EXISTS upload (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        filename TEXT,
        mimetype TEXT,
        size INTEGER,
        upload_time DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS conversation (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        state TEXT,
        data TEXT
    )''')
    conn.commit()
    conn.close()


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


# --- Dialogflow & Chatbot Integration ---
from flask import session
import base64, json

def dialogflow_text_response(text):
    return jsonify({"fulfillmentText": text})

def dialogflow_json_response(data):
    return jsonify(data)

def get_user_by_session():
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)

def update_user_context(user, field, value):
    if not user:
        return
    setattr(user, field, value)
    db.session.commit()

def get_next_required_field(user):
    # Order: income, expenses, savings, debts, assets, insurance, goals
    fields = ['income','expenses','savings','debts','assets','insurance','goals']
    for f in fields:
        if getattr(user, f, None) in (None, '', 0):
            return f
    return None

def generate_personalized_plan(user):
    # Simple plan logic for demo
    plan = f"""
Hi {user.name}, here's your personalized money plan:

1. Budget: Allocate 50% to needs, 30% to wants, 20% to savings.
2. Emergency Fund: Aim for 6 months of expenses ({(user.expenses or 0)*6:.0f}).
3. Investments: Start with SIPs or PPF for long-term growth.
4. Insurance: {user.insurance or 'Consider health/life insurance.'}
5. Debt: Keep debt-to-income below 30%. Current: {user.debts or 0}.
6. Goals: {user.goals or 'Set clear financial goals.'}

Stay consistent and review monthly!
"""
    return plan

def generate_summary(user):
    # Friendly summary for lower-income audiences
    summary = {
        "name": user.name,
        "income": user.income,
        "expenses": user.expenses,
        "savings": user.savings,
        "debts": user.debts,
        "assets": user.assets,
        "insurance": user.insurance,
        "goals": user.goals,
        "recommendations": [
            "Try to save at least 10% of your income.",
            "Build an emergency fund for 3-6 months of expenses.",
            "Avoid new debts if possible.",
            "Review your spending monthly."
        ]
    }
    return summary

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    intent = data.get('queryResult', {}).get('intent', {}).get('displayName')
    params = data.get('queryResult', {}).get('parameters', {})
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    # Map Dialogflow params to user fields
    param_map = {
        'income': 'income',
        'expenses': 'expenses',
        'savings': 'savings',
        'debts': 'debts',
        'assets': 'assets',
        'insurance': 'insurance',
        'goals': 'goals'
    }
    # Save params
    for k, v in params.items():
        if k in param_map and user:
            update_user_context(user, param_map[k], v)
    # Handle file upload (base64 string in params['file'])
    if 'file' in params and user:
        file_b64 = params['file']
        if file_b64:
            file_bytes = base64.b64decode(file_b64)
            filename = f"upload_{user.id}_{int(os.urandom(2).hex(),16)}.bin"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(file_bytes)
            upload = Upload(user_id=user.id, filename=filename, mimetype='application/octet-stream', size=len(file_bytes))
            db.session.add(upload)
            db.session.commit()
    # Step-by-step context
    next_field = get_next_required_field(user) if user else None
    if next_field:
        return dialogflow_text_response(f"Please provide your {next_field}.")
    # Intent handlers
    if intent == 'Future Plan' and user:
        plan = generate_personalized_plan(user)
        return dialogflow_text_response(plan)
    if intent == 'Summary' and user:
        summary = generate_summary(user)
        return dialogflow_json_response(summary)
    return dialogflow_text_response("Thank you! How else can I help?")

# --- Local chat endpoint for frontend ---
@app.route('/chat', methods=['POST'])
def chat():
    user = get_user_by_session()
    if not user:
        return jsonify({'error': 'Not logged in'}), 401
    msg = request.json.get('message')
    # Simulate Dialogflow webhook call
    # For demo, treat message as intent if matches, else as value for next field
    if msg.lower() in ['future plan','plan']:
        plan = generate_personalized_plan(user)
        return jsonify({'reply': plan})
    if msg.lower() in ['summary']:
        summary = generate_summary(user)
        return jsonify({'reply': json.dumps(summary, indent=2)})
    # Otherwise, treat as value for next field
    next_field = get_next_required_field(user)
    if next_field:
        update_user_context(user, next_field, msg)
        return jsonify({'reply': f"Saved your {next_field}. Anything else?"})
    return jsonify({'reply': "I'm here to help! Type 'plan' or 'summary' for more."})

# --- Startup ---
if __name__ == '__main__':
    with app.app_context():
        ensure_schema()
        db.create_all()
    app.run(debug=True)
