# save this as app.py
#run on browser-> http://127.0.0.1:5000 (lab) or http://10.5.55.178:5000 or http://10.5.52.126:5000 (LAB)
#yellow->function, blue->variable, green->module or class
import io
import os
import json
import urllib.parse
from flask import Flask, request, render_template, send_file, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask import render_template, redirect, url_for
from multiprocessing import Process, Queue
import subprocess
from datetime import datetime
from flask import session, jsonify, flash
from sqlalchemy import func,and_
from functools import wraps
from flask import abort
import requests
import base64
#from FlaskWebsite.models.user import User 



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database1.db'  # sqlite:///database.db
app.secret_key = 'mayeesha'

#Generate a random secret key
secret_key = os.urandom(24)
app.config['SECRET_KEY'] = secret_key
# Initialize Flask-Migrate with your Flask app and SQLAlchemy db
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Create the dictionary to track ongoing requests for each user
ongoing_requests = {}  # Need to define it here, outside of any route function


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    files = db.relationship('FileEntry', backref='user', lazy=True)

class FileEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(20))
    data = db.Column(db.LargeBinary)  # Stores the file data as a Large Binary Object
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)  #Added this field to get most recent file


    def __init__(self, filename, user, category, data):
        self.filename = filename
        self.user = user
        self.category = category
        self.data = data
        self.upload_date = datetime.utcnow()  # Sets the upload date when creating a new record


class UserRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_ids = db.Column(db.String(255))  # Comma-separated list of file IDs
    status = db.Column(db.String(255))  # Added the 'status' field

 # Establish a relationship with the User model
    user = db.relationship('User', backref='requests', foreign_keys=[user_id])

def add_file_id(self, file_id):
        if not self.file_ids:
            self.file_ids = str(file_id)
        else:
            self.file_ids += ',' + str(file_id)

class ResultFiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # New column
    request_id = db.Column(db.Integer, db.ForeignKey('user_request.id'), nullable=False)
    result_filename = db.Column(db.String(255)) 
    result_path = db.Column(db.String(255))  # Store the result file paths as a comma-separated list
    #result_path = db.Column(db.LargeBinary)  # Stores the file data as a Large Binary Object
    result_date = db.Column(db.DateTime, default=datetime.utcnow)  

     # Establish a relationship with the User model
    user = db.relationship('User', backref='results', foreign_keys=[user_id])
    # Establish a relationship with the UserRequest model
    request = db.relationship('UserRequest', backref='results', foreign_keys=[request_id])

def __init__(self, user_id, request_id, result_filename, result_path):
        self.user_id = user_id
        self.request_id = request_id
        self.result_filename = result_filename
        self.result_path = result_path

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

#the form data is used to authenticate users against the existing User table.
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# @login_manager.unauthorized_handler
# def no_auth_cb():
#     return redirect(url_for('/'))

@app.route('/')
@login_required
def index():
    user = current_user
    files = FileEntry.query.filter_by(user=user).all()

    files_data = [{'id': file.id, 'filename': file.filename} for file in files]

    return json.dumps(files_data), 200, {'Content-Type': 'application/json'}

# @app.route('/login', methods=['GET', 'POST']) #http://10.5.52.126:5000/login
# def login():
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()

#         if user and check_password_hash(user.password_hash, form.password.data):
#             login_user(user)
#             print("User logged in:", user.username)  # Added this line for debugging
#             return redirect(url_for('upload_form'))
#     return render_template('login.html', form=form)

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

@app.route('/register', methods=['GET', 'POST']) #in the browser http://10.5.52.126:5000/register
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# @app.route('/profile')
# @login_required
# def profile():
#     user = current_user

#     # Get all user requests in descending order of request_date
#     requests = UserRequest.query.filter_by(user=user).order_by(UserRequest.request_date.desc()).all()

#     # Create a list to store session data (request number, date, and time)
#     sessions_data = []

#     for index, request in enumerate(requests):
#         # Generate a unique request number (using session ID + index)
#         request_number = f"{request.id}-{index + 1}"
        
#         # Append session data (request number, date, and time) to the list
#         sessions_data.append({
#             'request_number': request_number,
#             'date': request.request_date.strftime('%Y-%m-%d'),
#             'time': request.request_date.strftime('%H:%M:%S'),
#         })

#     return render_template('profile.html', sessions_data=sessions_data, user=current_user)

@app.route('/user_requests', methods=['GET'])
@login_required
def user_requests():
    # Retrieve requests made by the current user
    user_requests = UserRequest.query.filter_by(user_id=current_user.id).all()

    # Render a template to display user requests
    return render_template('ReqList.html', user_requests=user_requests)


@app.route('/request-details/<int:request_id>')
@login_required
def request_details(request_id):
    # Retrieve the specific request based on the ID
    request = UserRequest.query.get(request_id)

    # Handle the case when the request is not found or doesn't belong to the user
    if not request or request.user_id != current_user.id:
        abort(404)  # Return a 404 error page

    # Split the file_ids string into a list of file IDs
    file_ids = request.file_ids.split(',') if request.file_ids else []

    # Fetch files associated with the request
    files = FileEntry.query.filter(FileEntry.id.in_(file_ids)).all()
    # Check if the result exists for the current request
    result = ResultFiles.query.filter_by(request_id=request_id).first()
    # Check if the logged-in user is the owner of the request
    is_owner = request.user_id == current_user.id

    return render_template('req_details.html', request=request, files=files)

@app.route('/view-result/<int:result_id>')
@login_required
def view_result(result_id):
    # Retrieve the specific result based on the ID
    result = ResultFiles.query.get(result_id)

 # Check if the result exists and if the logged-in user is the owner of the request
    if result and result.request.user_id == current_user.id:
        # You can add additional logic here if needed
        return render_template('resultlist.html', result=result)
    else:
        abort(404)  # Return a 404 error page if the result is not found or doesn't belong to the user

# @app.route('/logout')
# @login_required
# def logout():
#     user_id = current_user.id
#     logout_user()
#     if user_id in ongoing_requests:
#         del ongoing_requests[user_id]  # Removes the ongoing request for the logged-out user
#     return redirect(url_for('login'))  # Redirect to the login page after logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/api/files')
def api_files():
    files = FileEntry.query.all()
    files_data = [{'id': file.id, 'filename': file.filename} for file in files]
    return json.dumps(files_data), 200, {'Content-Type': 'application/json'}

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    files = request.files.getlist('file')
    if not files:
        return "No selected files!"

    category = request.form.get('category')
    if not category:
        return "No selected category!"

    # Create a list to store the file IDs associated with this request
    file_ids = []

    for file in files:
        if file.filename == '':
            continue

        print(f"Processing file: {file.filename}")  # Added this line for debugging

        # Create a new FileEntry and associate it with the current user
        new_file = FileEntry(filename=file.filename, user=current_user, category=category, data=file.read())

        db.session.add(new_file)
        db.session.commit()

        # Append the file's ID to the list
        file_ids.append(str(new_file.id))

    # Update the file_ids field in the UserRequest model and set the status to "Pending"
    user_request = UserRequest(user=current_user, file_ids=','.join(file_ids), status="Pending")
    db.session.add(user_request)
    db.session.commit()

    # Redirect the user to the list of their requests
    return redirect(url_for('user_requests'))

@app.route('/update_status/<int:request_id>', methods=['POST'])
#@login_required
def update_status(request_id):
    user_request = UserRequest.query.get(request_id) #checks if the specified request_id exists in the UserRequest table.
    if not user_request:
        return "Request not found!", 404

    # Parse the JSON data from the request
    data = request.get_json() #If the request with the given ID is found, it parses the JSON data from the POST request using request.get_json().

    # Check if the 'status' field is present in the JSON data
    if 'status' in data:
        new_status = data['status']
        user_request.status = new_status
        db.session.commit()

        # Added a print statement to log the status update
        print(f"Status updated to '{new_status}' for request ID {request_id}")

        return f"Status updated to '{new_status}'"
    else:
        return "Invalid data. 'status' field is missing in the request.", 400


# Function to generate a unique request number for each session
def generate_unique_request_number():
    if 'request_number' not in session:
        # Query the database to get the maximum existing user_request_id
        max_request_id = db.session.query(func.max(UserRequest.id)).scalar()

        # Increment the maximum request_id by 1 to generate a new unique request number
        if max_request_id is not None:
            new_request_number = max_request_id + 1
        else:
            # Handle the case when there are no existing request numbers
            new_request_number = 1

        # Store the new request number in the session
        session['request_number'] = new_request_number

    # Get the current request number from the session and increment it
    request_number = session['request_number']
    session['request_number'] += 1

    return request_number

@app.route('/upload-form')  #in the browser http://10.5.52.126:5000/upload-form
@login_required
def upload_form():
    return render_template('index.html')

def require_api_token(func):
    @wraps(func)
    def check_token(*args, **kwargs):
        # Check if the API session token is present in the session
        if 'api_session_token' not in session:
            return jsonify(message="Access denied"), 401  # Unauthorized response

        # Otherwise, allow the user to access the protected route
        return func(*args, **kwargs)
    return check_token

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # Instantiate the LoginForm
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Query the database for the user
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)  # Log in the user using Flask-Login
            flash('Login successful!', 'success')  # Flash a success message
            return redirect(url_for('upload_form'))
        else:
            flash('Invalid username or password. Please try again.', 'error')  # Flash an error message

    return render_template('login.html', form=form)


@app.route('/super_secret')
@require_api_token
def super_secret():
    return jsonify(message="Welcome to the super secret area!")  # Protected resource


@app.route('/download/<int:file_id>')
def download_file(file_id):
    # Query the FileEntry table to retrieve information about the file
    file_entry = FileEntry.query.get(file_id)

    if not file_entry:
        return "File not found!"

    # Set the MIME type based on the file extension
    mimetype = 'application/octet-stream'  # may need to adjust this based on myfile types

    # Set the URL-encoded filename for proper handling of spaces and special characters
    safe_filename = urllib.parse.quote(file_entry.filename)

    return send_file(
        io.BytesIO(file_entry.data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=safe_filename  # Set the filename for the download
    )

@app.route('/download_result/<int:result_id>', methods=['GET'])
@login_required
def download_result(result_id):
    # Retrieve the result based on the ID
    result = ResultFiles.query.get(result_id)

    # Check if the result exists and belongs to the current user
    if not result or result.user_id != current_user.id:
        abort(404)  # Return a 404 error page if the result is not found or doesn't belong to the user

    # Send the result file as an attachment for download
    return send_file(result.result_path, as_attachment=True, download_name=result.result_filename)

# @app.route('/show_result/<int:request_id>/<int:file_id>')
# @login_required
# def show_result(request_id, file_id):
#     request = UserRequest.query.get(request_id)
#     if not request:
#         return "Request not found!"

#     file_entry = FileEntry.query.get(file_id)
#     if not file_entry or file_entry.request_id != request.id:
#         return "File not found or not associated with the specified request!"

#     # Replace this line with logic to display the results for the file
#     result = "Results will be displayed here."

#     return render_template('show_result.html', request=request, file=file_entry, result=result)

#@app.route('/api/most_recent_file', methods=['GET'])
#def get_most_recent_file():
#    try:
        # Query the database to retrieve the most recent file based on upload_date
#        most_recent_file = FileEntry.query.order_by(FileEntry.upload_date.desc()).first()

#        if most_recent_file:
#            # Convert the database record to a dictionary and return it as JSON
#            return jsonify({
#                'filename': most_recent_file.filename,
#                'id' : most_recent_file.id,
#                'upload_date': most_recent_file.upload_date.strftime('%Y-%m-%d %H:%M:%S')
#            })
#        else:
#            return jsonify({'message': 'No files found in the database'}), 404
#    except Exception as e:
#        return jsonify({'message': 'An error occurred'}), 500


@app.route('/api/least_recent_file', methods=['GET'])
def get_least_recent_file():
    try:
        # Query the UserRequest table to retrieve the least recent request
        least_recent_request = UserRequest.query.filter_by(status='Pending').order_by(UserRequest.request_date).first()
        #least_recent_request = UserRequest.query(UserRequest.staus == 'pending').order_by(UserRequest.request_date).first() -> Dr. Nelson
        #least_recent_request = UserRequest.query.order_by(UserRequest.request_date).first()  -> before
       # least_recent_request = UserRequest.query.one()
        print(least_recent_request)
        if least_recent_request:
            # Convert the UserRequest record to a dictionary
            least_recent_request_info = {
                'id':least_recent_request.id,
                'user_id': least_recent_request.user_id,
                'request_date': least_recent_request.request_date.strftime('%Y-%m-%d %H:%M:%S'),
                'file_ids': least_recent_request.file_ids,
                'status': least_recent_request.status,
            }

            return jsonify({'least_recent_request': least_recent_request_info})
        else:
            return jsonify({'message': 'No requests found in the database'}), 404
    except Exception as e:
        # Debugging: Print the exception for troubleshooting
        print(f"An error occurred: {str(e)}")
        return jsonify({'message': 'An error occurred'}), 500



@app.route('/request_transfer', methods=['GET'])
def get_transfer():
    try:
        request_transfer = UserRequest.query.filter_by(status="Running").order_by(UserRequest.request_date).first()
        if request_transfer:
            # Retrieve file info for the running request
            file_info_list = []
            file_ids = request_transfer.file_ids.split(',')
            for file_id in file_ids:
                file_entry = FileEntry.query.get(file_id)
                if file_entry:
                    file_info_list.append({
                        'id': file_entry.id,
                        'filename': file_entry.filename,
                        'request_id': request_transfer.id,
                    })
            request_transfer_info = {
                'request_id': request_transfer.id, #previously 'id': request_transfer.id
                'file_info': file_info_list,  # Include file info list in the response
                

            }
            return jsonify({'request_transfer': request_transfer_info})
        else:
            return jsonify({'message': 'No requests for transfer found in the database'}), 404
    except Exception as e:
        # Debugging: Print the exception for troubleshooting
        print(f"An error occurred: {str(e)}")
        return jsonify({'message': 'An error occurred for request transfer'}), 500

#FOR RESULT
@app.route('/upload_results', methods=['POST'])
def upload_results():
    try:
        result_data = request.json  # workerscript sends JSON data containing result files information
        user_id = result_data.get('user_id')  # Extract user_id from the request data
        request_id = result_data.get('request_id')  # Extract request_id from the request data
        result_files = result_data.get('result_files')  # Extract result files list from the request data
        files_data = result_data.get('files')# added

        # Process files_data (contains filename and base64-encoded content)
        for file_data in files_data:
            filename = file_data.get('filename')
            content_base64 = file_data.get('content')
            # Decode base64 content back to binary data
            file_content = base64.b64decode(content_base64)

            # Create a directory to store the files if it doesn't exist
            os.makedirs("/path/to/your/storage/directory", exist_ok=True)

            # Save the file content to the server
            file_path = os.path.join("/path/to/your/storage/directory", filename)
            with open(file_path, 'wb') as file:
                file.write(file_content)

            # Create a new ResultFiles instance and add it to the database
            new_result_file = ResultFiles(user_id=user_id, request_id=request_id, result_filename=filename, result_path=file_path)
            db.session.add(new_result_file)
        
        # Commit the changes to the database
        db.session.commit()

        return jsonify({'message': 'Result files added to the database and saved to server successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


    
@app.route('/tvla_completed', methods=['POST'])
def tvla_completed():
    try:
# Get request ID from the POST data sent by the worker script
        request_id = request.json.get('request_id')
        
        # Update the status of the request to 'Completed' in the database
        request_entry = UserRequest.query.get(request_id)
        if request_entry:
            request_entry.status = 'Running'
            db.session.commit()
            return jsonify({'message': 'Request status updated to Completed'}), 200
        else:
            return jsonify({'message': 'Request not found in the database'}), 404
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500

    
@app.route('/worker', methods=['POST'])
#@login_required
def worker_endpoint():
    if request.method == 'POST':
        result_data = request.get_json()  # Get data from the request as JSON
        request_id = result_data.get('request_id')
        result_files = result_data.get('result_files')

         # Convert the list to a string using a separator (comma in this case)
        result_files_string = ",".join(result_files)

        # Save result files to the Result table
        result_entry = ResultFiles(request_id=request_id, result_files=result_files_string)
        db.session.add(result_entry)
        db.session.commit()

        # Update the status of the request to 'Completed'
        request_entry = UserRequest.query.get(request_id)
        if request_entry:
            request_entry.status = 'Completed'
            db.session.commit()

        return "Result files saved and request status updated."
     
if __name__ == '__main__':


 # Start the Flask app
    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=5000) #Flask app is set to run on 0.0.0.0, which allows it to accept connections from any IP address on the network.