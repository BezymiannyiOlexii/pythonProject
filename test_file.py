import os
import socket
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, login_user, login_required, current_user, logout_user


app = Flask(__name__)
db = SQLAlchemy()

app.config['SECRET_KEY'] = 'secret-key-goes-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))

#with app.app_context():
#    db.create_all()

@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    user = User.query.filter_by(
        email=email).first()  # if this returns a user, then the email already exists in database

    if user:  # if a user is found, we want to redirect back to signup page so user can try again
        flash('Email address already exists')
        return redirect(url_for('signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    user = User.query.filter_by(email=email).first()
    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('login')) # if the user doesn't exist or password is wrong, reload the page
    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect('/disk')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/')
@login_required
def index():
    return redirect('/login')

@app.route('/upload')
@login_required
def upload():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    HOST = "127.0.0.1"
    PORT = 65431
    uploaded_file = request.files['file']
    raw = uploaded_file.read()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Client Sending flag")
        flag: int = 1
        s.send(flag.to_bytes(1, 'big'))
        print("Client Sending:", uploaded_file.filename)

        s.sendall(len(uploaded_file.filename).to_bytes(4, 'big'))
        s.sendall(uploaded_file.filename.encode('ascii'))
        s.sendall(len(raw).to_bytes(8, 'big'))
        s.sendall(raw)
    print("Received")
    return redirect('/upload')

@app.route('/download')
@login_required
def download_file():

    HOST = "127.0.0.1"
    PORT = 65431
    filename = request.args['name']

    if request.args["action"] == "upl":
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))

            print("Client Sending flag")
            flag: int = 2
            s.send(flag.to_bytes(1, 'big'))

            print('Client Receiving')
            with s:

                s.sendall(len(filename).to_bytes(4, 'big'))
                s.sendall(filename.encode())

                expected_size = b""
                while len(expected_size) < 8:
                    more_size = s.recv(8 - len(expected_size))
                    if not more_size:
                        raise Exception("Short file length received")
                    expected_size += more_size
                expected_size = int.from_bytes(expected_size, 'big')

                packet = b""
                while len(packet) < expected_size:
                    buffer = s.recv(expected_size - len(packet))
                    if not buffer:
                        raise Exception("Incomplete file received")
                    packet += buffer
                filename = '/Users/macbookair/Downloads_python/' + filename
                with open(filename, 'wb') as f:
                    f.write(packet)
        return redirect('/disk')
    elif request.args["action"] == "del":
        os.remove('data/'+filename)
        return redirect('/disk')
    else:
        return redirect('/disk')


@app.route('/disk', methods=['GET'])
@login_required
def disk():
    database_files = os.listdir('data/')
    database_sizes = list()
    for file in database_files:
        file_size = os.path.getsize('data/'+file)
        if file_size > 10**9:
            file_size /= 1024**3
            file_weight = 'Gb'
            size = '%.2f'%file_size+' {}'.format(file_weight)
        elif file_size > 10**6:
            file_size /= 1024**2
            file_weight = 'MB'
            size = '%.2f' % file_size + ' {}'.format(file_weight)
        else:
            file_size /= 1024
            file_weight = 'kB'
            size = '%.2f' % file_size + ' {}'.format(file_weight)

        database_sizes.append(size)
    #print(database_files, database_sizes)
    data = zip(database_files, database_sizes)
    return render_template('disk.html', data=data)


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=4446, debug=True)

