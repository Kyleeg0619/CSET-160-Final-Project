import datetime
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine, text
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mySuperSecretKey1234567890'

# *** Connect Database ***
conn_str = "mysql+pymysql://root:Ky31ik3$m0s$;@localhost/accountsdb"
engine = create_engine(conn_str, echo=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/accounts')
def accounts():
    with engine.begin() as conn:
        accounts = conn.execute(text('SELECT * FROM accounts')).all()
        print(accounts)

        return render_template('accounts.html',accounts=accounts)

@app.route('/register', methods=['GET','POST'])
def register():
    msg = ''
    if request.method == 'POST':
        status = request.form['status']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        with engine.begin() as conn:
            existing = conn.execute(text('SELECT * FROM accounts WHERE username = :username'),{'username':username}).fetchone()

            if existing:
                msg = 'Account already exists'
            else:
                conn.execute(text('INSERT INTO accounts (username,password,education_status) VALUES (:username,:password,:status)'), {'username':username,'password':hashed_password,'status':status})
                msg = 'You have successfully signed up! You can now log in.'
    return render_template('register.html',msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    account = None  # Ensure 'account' is initialized
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with engine.begin() as conn:
            result = conn.execute(text('SELECT * FROM accounts WHERE username = :username'), {'username': username}).fetchall()

            if result:
                account = result[0]  # Fetch the first row (since fetchall() returns a list of rows)

                # Access tuple values by index
                if account and check_password_hash(account[1], password):  # account[1] is the password field
                    session['loggedin'] = True
                    session['username'] = account[0]  # account[0] is the username field

                    if account[2] == 'Teacher':  # account[2] is the education_status field
                        return redirect(url_for('teacher'))
                    else:
                        return redirect(url_for('index'))

    return render_template('login.html', msg=msg, account=account)

@app.route('/create_test', methods=['GET', 'POST'])
def create_test():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        questions = [request.form.get(f'q{i}') for i in range(1, 11)]
        answers = [request.form.get(f'a{i}') for i in range(1, 11)]

        from datetime import datetime

        with engine.begin() as conn:
            result = conn.execute(
                text('INSERT INTO tests (title, username, created_at) VALUES (:title, :username, :created_at)'),
                {
                    'title': title,
                    'username': session['username'],
                    'created_at': datetime.now()
                }
            )
            test_id = result.lastrowid

            for q, a in zip(questions, answers):
                conn.execute(
                    text('INSERT INTO questions (test_id, question_text, answer) VALUES (:test_id, :q, :a)'),
                    {'test_id': test_id, 'q': q, 'a': a}
                )
        print("Inserted test:", title)
        print("Questions:", questions)
        print("Answers:", answers)

        return redirect(url_for('teacher'))

    return render_template('create_test.html')

@app.route('/teacher')
def teacher():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']

    with engine.begin() as conn:
        # Ensure results are returned as dictionaries or Row objects
        tests = conn.execute(text('SELECT * FROM tests WHERE username = :username'), {'username': username}).fetchall()
    
    return render_template('teacher.html', tests=tests)


if __name__ == '__main__':
    app.run(debug=True)