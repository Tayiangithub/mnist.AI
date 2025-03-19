from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
import hashlib
import time
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client.file_integrity_checker
users_collection = db.users
files_collection = db.files


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        if users_collection.find_one({"email": email}):
            return "User already exists!"

        users_collection.insert_one({"username": username, "email": email, "password": hashed_password})
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({"email": email})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials!"

    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file_path = request.form['file_path']

        if not os.path.exists(file_path):
            flash('Invalid file path!')
        elif os.path.isdir(file_path):  # If it's a directory, add all files inside it
            try:
                files_added = 0
                for root, _, files in os.walk(file_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        file_hash = compute_hash(full_path)
                        files_collection.insert_one({
                            'user_id': session['user_id'],
                            'filepath': full_path,
                            'hash': file_hash,
                            'status': 'unchanged'
                        })
                        files_added += 1

                if files_added > 0:
                    flash(f'{files_added} files from the directory added for monitoring!')
                else:
                    flash('No files found in the selected directory!')
            except PermissionError:
                flash('Permission denied: Cannot access some files in the directory!')
        else:  # If it's a single file
            try:
                file_hash = compute_hash(file_path)
                files_collection.insert_one({
                    'user_id': session['user_id'],
                    'filepath': file_path,
                    'hash': file_hash,
                    'status': 'unchanged'
                })
                flash('File added for monitoring!')
            except PermissionError:
                flash('Permission denied: Cannot access the specified file!')

    monitored_files = list(files_collection.find({'user_id': session['user_id']}))
    logs = list(db.logs.find())

    return render_template('dashboard.html', files=monitored_files, logs=logs)



def compute_hash(file_path):
    if not os.path.isfile(file_path):
        return None
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except PermissionError:
        flash('Permission denied for this file. Cannot compute hash.')
        return None

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


def compute_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def add_files_to_monitor(path):
    if os.path.isfile(path):
        file_hash = compute_hash(path)
        files_collection.update_one(
            {"filepath": path, "user_id": session['user_id']},
            {"$set": {"hash": file_hash, "status": "unchanged"}},
            upsert=True
        )
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                file_hash = compute_hash(file_path)
                files_collection.update_one(
                    {"filepath": file_path, "user_id": session['user_id']},
                    {"$set": {"hash": file_hash, "status": "unchanged"}},
                    upsert=True
                )


def periodic_scan():
    while True:
        time.sleep(30)  # Scan every 30 seconds

        for file_record in files_collection.find():
            file_path = file_record['filepath']

            if not os.path.isfile(file_path):
                files_collection.update_one(
                    {"_id": file_record['_id']},
                    {"$set": {"status": "file missing"}}
                )
                continue

            try:
                current_hash = compute_hash(file_path)

                if current_hash != file_record['hash']:
                    files_collection.update_one(
                        {"_id": file_record['_id']},
                        {"$set": {"status": "modified", "hash": current_hash}}
                    )
                else:
                    files_collection.update_one(
                        {"_id": file_record['_id']},
                        {"$set": {"status": "unchanged"}}
                    )

            except PermissionError:
                files_collection.update_one(
                    {"_id": file_record['_id']},
                    {"$set": {"status": "permission denied"}}
                )


def log_event(file_path, event_type):
    db.logs.insert_one({
        "filepath": file_path,
        "event_type": event_type,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    })



if __name__ == '__main__':
    scan_thread = threading.Thread(target=periodic_scan)
    scan_thread.daemon = True
    scan_thread.start()
    app.run(debug=True)
