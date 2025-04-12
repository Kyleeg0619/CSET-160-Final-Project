import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
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
    
@app.route('/tests')
def tests():
    with engine.begin() as conn:
        tests = conn.execute(text('SELECT * FROM tests')).all()
        print(tests)
        return render_template('tests.html', tests=tests)

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
                        return redirect(url_for('student'))

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

@app.route('/student')
def student():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']

    with engine.begin() as conn:
        tests = conn.execute(text('SELECT * FROM tests WHERE id NOT IN (SELECT test_id FROM scores WHERE username = :username)'),{'username':username}).fetchall()
        score = conn.execute(text('SELECT * FROM scores WHERE username = :username'), {'username': username}).fetchall()
    
    return render_template('student.html', tests = tests, score=score)

@app.route('/take_test_action', methods=['POST'])
def take_test_action():
    test_id = request.form['test_id']
    action = request.form['action']

    if action == 'take_test':
        return redirect(url_for('take_test', test_id=test_id))
    
@app.route('/take_test/<int:test_id>', methods=['GET','POST'])
def take_test(test_id):
    with engine.begin() as conn:
        test = conn.execute(text('SELECT * FROM tests WHERE id = :test_id'), {'test_id':test_id}).fetchone()
        questions = conn.execute(text('SELECT * FROM questions WHERE test_id = :test_id'),{'test_id':test_id}).fetchall()

        return render_template('take_test.html',test=test,questions=questions)

@app.route('/handle_test_action', methods=['POST'])
def handle_test_action():
    if 'username' not in session:
        return redirect(url_for('login'))

    test_id = request.form['test_id']
    action = request.form['action']

    if action == 'delete':
        with engine.begin() as conn:
            conn.execute(text('DELETE FROM questions WHERE test_id = :test_id'), {'test_id': test_id})
            conn.execute(text('DELETE FROM tests WHERE id = :test_id AND username = :username'),
                         {'test_id': test_id, 'username': session['username']})
        return redirect(url_for('teacher'))

    elif action == 'modify':
        # You can redirect to a modify page here and pass the test_id
        return redirect(url_for('modify', test_id=test_id))

    return redirect(url_for('teacher'))  # Fallback

@app.route('/modify/<int:test_id>', methods=['GET','POST'])
def modify(test_id):
    with engine.begin() as conn:
        test = conn.execute(text('SELECT * FROM tests WHERE id = :test_id AND username = :username'), {'test_id':test_id,'username':session['username']}).fetchone()
        questions = conn.execute(text('SELECT * FROM questions WHERE test_id = :test_id'),{'test_id':test_id}).fetchall()

        if not test:
            return 'Test not found or you don\'t have permission.',403
    return render_template('modify_test.html',test=test,questions=questions)

@app.route('/submit_modifications/<int:test_id>', methods=['POST'])
def submit_modifications(test_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    new_title = request.form['title']

    with engine.begin() as conn:
        # Update the test title
        conn.execute(text('UPDATE tests SET title = :title WHERE id = :test_id AND username = :username'),
                     {'title': new_title, 'test_id': test_id, 'username': session['username']})

        # Update each question
        for i in range(1, 11):
            question_text = request.form.get(f'q{i}')
            answer_text = request.form.get(f'a{i}')
            question_id = request.form.get(f'qid{i}')

            if question_id:
                conn.execute(text('''
                    UPDATE questions
                    SET question_text = :qtext, answer = :atext
                    WHERE id = :qid AND test_id = :test_id
                '''), {'qtext': question_text, 'atext': answer_text, 'qid': question_id, 'test_id': test_id})

    return redirect(url_for('teacher'))

@app.route('/submit_test/<int:test_id>', methods=['POST'])
def submit_test(test_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    score = 0
    with engine.begin() as conn:
        questions = conn.execute(text('SELECT id, answer FROM questions WHERE test_id = :test_id'), {'test_id': test_id}).fetchall()
        title = conn.execute(text('SELECT title FROM tests WHERE id = :test_id'),{'test_id':test_id}).fetchone()
        for idx, question in enumerate(questions, start=1):
            user_answer = request.form.get(f'a{idx}', '').strip().lower()
            correct_answer = question.answer.strip().lower()
            if user_answer == correct_answer:
                score += 1

        # Optional: store the score
        conn.execute(text('INSERT INTO scores (username, test_id, title, score) VALUES (:username, :test_id, :title, :score)'),
                     {'username': session['username'], 'test_id': test_id, 'title':title, 'score': score})

    return redirect(url_for('student'))


if __name__ == '__main__':
    app.run(debug=True)