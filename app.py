from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
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




# Session management for login state
from flask import session, redirect, url_for

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Dummy login: set session['user_id']
        session['user_id'] = 1
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/interactive')
def interactive():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('interactive.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        return upload_file()
    return render_template('upload.html')

@app.route('/analytics')
def analytics():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('analytics.html')

@app.route('/settings')
def settings():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('settings.html')

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
