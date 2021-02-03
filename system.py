from flask import Flask, render_template, request, url_for, redirect, session, flash
from flask_mysqldb import MySQL
import re
import os
import hashlib
import random
from datetime import date
import html


App = Flask(__name__)

App.config['SECRET_KEY'] = "abcdef12356AAFF"

App.config['MYSQL_HOST'] = '127.0.0.1'
App.config['MYSQL_USER'] = 'root'
App.config['MYSQL_PASSWORD'] = ''
App.config['MYSQL_DB'] = 'quiz_system_db'

conn = MySQL (App)

@App.route("/")
@App.route("/index")
@App.route("/home")
def index():
    return render_template("index.html", title = "Home")

@App.route("/login", methods = ["GET", "POST"])
def login():

    if check_login():
        return redirect(session.get("role"))

    if request.form:
        email = secure(request.form["email"])
        password = hashing(request.form["password"])

        try:
            cur = conn.connection.cursor()
            cur.execute(f"SELECT u.id, u.name, u.email, r.name as role, count(e.id) as quiz from users AS u, roles AS r, exam AS e WHERE u.email = '{email}' and u.password = '{password}' and u.role_id = r.id and u.id = e.user_id")
            check = cur.fetchone()
            cur.close()
            conn.connection.commit()
            if check:
                session["login"] = True
                session["id"] = check[0]
                session["name"] = check[1]
                session["email"] = check[2]
                session["role"] = check[3]
                session["quiz"] = check[4]
                if check[3] == "teacher":
                    return redirect(url_for("teacher"))
                else:
                    return redirect(url_for("student"))
            else:
                return render_template("login.html", title = "login", fail = "Process faild, check your infomration and try again.")
        
        except Exception as e:
            print(e.args)
            return render_template("login.html", title = "login")    
    
    return render_template("login.html", title = "login")


@App.route("/signup", methods = ["GET", "POST"])
def signup():

    if check_login():
        return redirect(session.get("role"))

    if request.args.get("email") and request.method == "GET":
        print("get")
        return render_template("signup.html", email = secure(request.args.get("email")))    
    
    if request.form:
        name = secure(request.form["fname"])+" "+secure(request.form["lname"])
        email = secure(request.form["email"])
        role = int(request.form["role"])
        if request.form["password"] == request.form["vpassword"]:
            password = hashing(request.form["password"])
        else:
            return render_template("signup.html", title = "Sign up", fail = "Process faild, check your infomration and try again.")


        try:
            cur = conn.connection.cursor()
            check = cur.execute(f"INSERT INTO users(`name`, `email`, `password`, `role_id`) VALUES ('{name}', '{email}', '{password}', {role})")
            cur.close()
            conn.connection.commit()
            if check:
                return render_template("signup.html", title = "Sign up", success = "User registerd successfully, you can login now.")
            else:
                return render_template("signup.html", title = "Sign up", fail = "Process faild, check your infomration and try again.")
        except Exception as e:
            print(e.args)
            error = "Process faild, check your infomration and try again."
            if e.args[0] == 1062:
                error = "Email already exist."
            return render_template("signup.html", title = "Sign up", error = error)    
    
    return render_template("signup.html", title = "Sign up")

@App.route("/signout")
def signout():
    session.clear()
    return redirect("index")

@App.route("/teacher")
def teacher():
    if not teacher_required():
        return redirect("index")
    try:
        cur = conn.connection.cursor()
        cur.execute(f"SELECT e.id, e.name, e.url, e.time, e.ended, count(q.question) as question FROM `exam` as e, questions as q WHERE e.user_id = {session.get('id')} and e.id = q.exam_id GROUP BY e.id LIMIT 3")
        quizez = cur.fetchall()
        cur.close()
        conn.connection.commit()
        return render_template("profile/teacher/teacher.html", title = "Dashboard", dashboard = "active", quiz = "", settings = "",data = session, quizes = quizez)
    except Exception as e:
        print(e.args)

    return render_template("profile/teacher/teacher.html", title = "Dashboard", dashboard = "active", quiz = "", settings = "", data = session)

@App.route("/quiz")
def quiz():
    if not teacher_required():
        return redirect("index")

    try:
        cur = conn.connection.cursor()
        cur.execute(f"SELECT e.id, e.name, e.url, e.time, e.ended, count(q.question) as question FROM `exam` as e, questions as q WHERE e.user_id = {session.get('id')} and e.id = q.exam_id GROUP BY e.id")
        quizez = cur.fetchall()
        cur.close()
        conn.connection.commit()
        return render_template("profile/teacher/quiz.html", title = "Quiz", dashboard = "", quiz = "active", settings = "",data = session, quizes = quizez)
    except Exception as e:
        print(e.args)
    return render_template("profile/teacher/quiz.html", title = "Quiz", dashboard = "", quiz = "active", settings = "")

@App.route("/quiz/add_quiz", methods=["GET", "POST"])
def add_quiz():
    if not teacher_required():
        return redirect("index")

    if request.method == "POST" and request.files["quiz"]:
        today = date.today()
        file = request.files["quiz"]
        filename = file.filename.split(".")
        filename = secure(filename[0])
        content = str(file.read(), 'utf-8').split("\r\n")
        question = ""
        questions = {}

        for i in content:
            if not i:
                continue
            elif i[0].isnumeric():
                i = html.escape(i)
                questions[i] = []
                question = i
            elif i[0].isalpha():
                i = html.escape(i)
                questions[question].append(i)
        
        if questions:
            try:
                letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                url = today.strftime("%b-%d-%Y")+''.join(random.choice(letters) for i in range(10))
                cur = conn.connection.cursor()
                cur.execute(f"INSERT INTO `exam`(`name`, `ended`, `URL`, `user_id`, `time`) VALUES ('{filename}', 0, '{url}', {session.get('id')}, 5)")
                exam_id = cur.lastrowid
                for question, answers in questions.items():
                    index = None
                    for ans in range(len(answers)):
                        if "[right answer]" in answers[ans]:
                            pos = answers[ans].find("[right answer]")
                            answers[ans] = answers[ans][0:pos-1]
                            index = ans
                    cur.execute(f"INSERT INTO `questions`(`exam_id`,`question` ,`possible_answers`, `right_asnwers`) VALUES ({exam_id}, '{question}', '{secure(str(answers))}', '{secure(answers[index])}')")
                cur.close()
                conn.connection.commit()
                return redirect("../quiz")
            except Exception as e:
                print(e.args)
                return render_template("profile/teacher/add_quiz.html", title = "Add Quiz", fail = "Process faild, please try again.")

    return render_template("profile/teacher/add_quiz.html", title = "Add Quiz")

@App.route("/quiz/delete", methods=["POST"])
def delete_quiz():
    if not teacher_required():
        return redirect("index")

    if request.form["quiz_id"]:
        try:
            cur = conn.connection.cursor()
            id = int(request.form['quiz_id'])
            cur.execute(f"delete from questions where exam_id = {id}")
            cur.execute(f"delete from results where exam_id = {id}")
            cur.execute(f"delete from exam where id = {id}")
            cur.close()
            conn.connection.commit()
        except Exception as e:
            print(e.args)

    return redirect("../quiz")

@App.route("/quiz/update_link", methods=["POST"])
def update_link():
    if not teacher_required():
        return redirect("index")

    if request.form["quiz_id"]:
        try:
            cur = conn.connection.cursor()
            letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            today = date.today()
            url = today.strftime("%b-%d-%Y")+''.join(random.choice(letters) for i in range(10))
            id = int(request.form['quiz_id'])
            cur.execute(f"update exam set url = '{url}' where id = {id}")
            cur.close()
            conn.connection.commit()
        except Exception as e:
            print(e.args)

    return redirect("../quiz")

@App.route("/quiz/view", methods=["GET"])
def view_quiz():
    if not teacher_required():
        return redirect("index")

    try:
        cur = conn.connection.cursor()
        id = int(request.args['id'])
        cur.execute(f"select `question`, `possible_answers`, `right_asnwers` from questions where exam_id = {id}")
        questions = cur.fetchall()
        list_questions = []
        for row in questions:
            answers = re.findall("([A-Z][)][\s][^)]*)(?![)])", row[1])
            data = [row[0], answers, row[2]]
            list_questions.append(data)

        cur.execute(f"SELECT e.name, e.time, e.ended, count(q.question) as question FROM `exam` as e, questions as q WHERE e.user_id = {session.get('id')} and e.id = q.exam_id GROUP BY e.id")
        quiz_data = cur.fetchone()
        cur.close()
        conn.connection.commit()
        return render_template("profile/teacher/view_quiz.html", title = "View Quiz", quiz= quiz_data, questions = list_questions)
    except Exception as e:
        print(e.args)
    return render_template("profile/teacher/view_quiz.html", title = "View Quiz", quiz=[], questions = [])

@App.route("/student")
def student():
    if not student_required():
        return redirect("index")
    data = []
    try:
        cur = conn.connection.cursor()
        cur.execute(f"SELECT result, exam_id FROM results WHERE user_id = {session.get('id')}")
        results = cur.fetchall()
        for result in results:
            cur.execute(f"SELECT e.name, e.time, count(q.question) as question FROM `exam` as e, questions as q WHERE e.id = {result[1]} and q.exam_id = {result[1]} GROUP BY e.id")
            x = list(cur.fetchone())
            x.append(result[0])
            data.append(x)
            
        cur.close()
    except Exception as e:
        print(e.args)

    return render_template("profile/student/student.html", title = "Dashboard", dashboard = "active", settings = "", data = data)

@App.route("/quiz/<string:url>/start")
def start_quiz(url):
    if not student_required():
        return redirect("http://127.0.0.1:5000/index")
    
    url = secure(url)
    quiz = ()
    list_questions = ()
    try:
        cur = conn.connection.cursor()
        cur.execute(f"select result from results where user_id = {session.get('id')} and exam_id = (select id from exam where url = '{url}')")
        check = cur.fetchone()
        if check != None:
            return redirect("http://127.0.0.1:5000/student")
        cur.execute(f"SELECT e.name, e.time, e.ended, count(q.question) as question FROM `exam` as e, questions as q WHERE e.URL = '{url}' and e.id = q.exam_id GROUP BY e.id")
        quiz = cur.fetchone()
        cur.execute(f"select `question`, `possible_answers` from questions where exam_id = (select id from exam where URL = '{url}')")
        questions = cur.fetchall()
        list_questions = []
        for row in questions:
            answers = re.findall("([A-Z][)][\s][^)]*)(?![)])", row[1])
            data = [row[0], answers]
            list_questions.append(data)
        cur.close()
    except Exception as e:
        print(e.args)

    return render_template("profile/student/start_quiz.html", title = "Quiz", dashboard = "", settings = "", quiz=quiz, questions = list_questions)

@App.route("/quiz/<string:url>/finish", methods=["POST"])
def finish_quiz(url):
    if not student_required():
        return redirect("index")
    
    url = secure(url)
    answers = request.form
    try:
        cur = conn.connection.cursor()
        cur.execute(f"select result from results where user_id = {session.get('id')} and exam_id = (select id from exam where url = '{url}')")
        check = cur.fetchone()
        if check != None:
            return redirect("http://127.0.0.1:5000/student")

        cur.execute(f"SELECT right_asnwers FROM questions WHERE exam_id = (select id from exam where URL = '{url}')")
        right_answers = cur.fetchall()
        marks = mark(right_answers, answers)
        cur.execute(f"INSERT into results(result, exam_id, user_id) values({marks}, (select id from exam where URL = '{url}'), {session.get('id')})")
        cur.execute(f"Update exam set ended = ended + 1 WHERE URL = '{url}'")
        cur.close()
        conn.connection.commit()
    except Exception as e:
        print(e.args)

    flash('Quiz recived successfully')
    return redirect("http://127.0.0.1:5000/student")

@App.route("/settings")
def settings():
    #if condition for student or admin
    if teacher_required():
        return render_template("profile/teacher/settings.html", title = "Settings", dashboard = "", quiz = "", settings = "active")

    elif student_required():
        return render_template("profile/student/settings.html", title = "Settings", dashboard = "", settings = "active")
        
    else:
        return redirect("index")

@App.route("/settings/update", methods=["POST"])
def settings_update():
    #if condition for student or admin
    if not teacher_required() and not student_required():
        return redirect("index")

    if request.method == "POST":
        name = secure(request.form["fname"])+" "+secure(request.form["lname"])
        email = secure(request.form["email"])
        if request.form["password"] == request.form["vpassword"]:
            password = hashing(request.form["password"])

        try:
            cur = conn.connection.cursor()
            cur.execute(f"update users set name = '{name}', email = '{email}', password = '{password}' where id = {session.get('id')}")
            cur.close()
            conn.connection.commit()
            session["name"] = name
            session["email"] = email
        except Exception as e:
            print(e.args)
    return redirect("../settings")


def mark(right_answers, all_answers):
    result = 0
    counter = 0
    for answer in all_answers.values():
        if len(right_answers) < counter:
            break
        if answer == right_answers[counter][0]:
            result += 1
        counter += 1
    return result

def secure(value):
    return re.sub('[^A-Za-z0-9@_$. ()-]+', '', value)

def hashing(password):
    salt = os.urandom(32)
    hashed = hashlib.md5(password.encode('utf-8'))
    return hashed.hexdigest()

def check_login():
    if session.get("login"):
        return True
    return False

def teacher_required():
    if session.get("role") == "teacher":
        return True
    return False

def student_required():
    if session.get("role") == "student":
        return True
    return False

if __name__ == "__main__":
    App.run(debug=True)