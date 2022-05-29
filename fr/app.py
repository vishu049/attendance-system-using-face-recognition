from flask import Flask, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message
from flask_mysqldb import MySQL
import time
from datetime import date
import random
import MySQLdb.cursors
import re
import cv2
import face_recognition
import os
import numpy as np
from datetime import datetime
import pickle

app = Flask(__name__)

app.secret_key = 'roger that'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'fr'

mysql = MySQL(app)

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'attendenceid01@gmail.com'
app.config['MAIL_PASSWORD'] = 'Strive@1'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/stdashboard', methods=['GET', 'POST'])
def stdashboard():
    msg = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM class")
    classdata = cur.fetchall()
    timestamp = time.strftime('%H:%M')
    return render_template('st_dashboard.html', msg=msg, classdata=classdata,timestamp=timestamp)

@app.route('/success')
def success():
    subject_id = request.args['subject_id']
    return render_template('success.html', subject_id=subject_id)

@app.route('/viewattendance', methods=['GET', 'POST'])
def viewattendance():
    if request.method == 'POST' and 'class' in request.form:
        class_id = request.form['class']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM class WHERE id = %s", (class_id,))
        classdata = cur.fetchone()
        cur.execute("SELECT * FROM users WHERE usertype = '2'")
        students = cur.fetchall()
        return render_template('view_attendance.html', classdata=classdata, students=students)

@app.route('/criteriamail/<string:studentmail>')
def criteriamail(studentmail):
    student_mail = studentmail
    msg = Message('Hello',sender ='attendenceid01@gmail.com',recipients = [student_mail])
    msg.body = 'You have low attendance. Kindly attend classes prpoerly to achieve 75% attendance'
    mail.send(msg)
    alt = 'Mail sent successfully'
    return redirect(url_for('trdashboard', msg1=alt))


@app.route('/trdashboard', methods=['GET', 'POST'])
def trdashboard():
    msg = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM class")
    classdata = cur.fetchall()
    if request.method == 'GET' and request.args.get('msg1'):
        msg1 = request.args['msg1'] 
        return render_template('tr_dashboard.html', msg=msg, msg1=msg1, classdata=classdata)
    return render_template('tr_dashboard.html', msg=msg, classdata=classdata)
@app.route('/createclass', methods=['GET', 'POST'])
def createclass():
    if request.method == 'POST' and 'subject' in request.form and 'starttime' in request.form and 'endtime' in request.form:
        subject = request.form['subject']
        starttime = request.form['starttime']
        endtime = request.form['endtime']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO class(subject, starttime, endtime, creation_date) VALUES(%s, %s, %s, %s)", (subject, starttime, endtime, date.today()))
        mysql.connection.commit()
        msg = 'Class Created Successfully'
        return redirect(url_for('trdashboard', msg1=msg))
    return render_template('create_class.html')

@app.route('/stattendance/<int:subject_id>')
def stattendance(subject_id):
    path = 'images'
    images = []
    mylist = []
    classNames = []
    mylist = os.listdir(path)
    for cl in mylist:
        curImg = cv2.imread(f'{path}/{cl}')
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])
    
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encoded_face = face_recognition.face_encodings(img)[0]
        encodeList.append(encoded_face)
    encoded_face_train =  encodeList
    
    cap  = cv2.VideoCapture(0)
    while True:
        success, img = cap.read()
        imgS = cv2.resize(img, (0,0), None, 0.25,0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        faces_in_frame = face_recognition.face_locations(imgS)
        encoded_faces = face_recognition.face_encodings(imgS, faces_in_frame)
        for encode_face, faceloc in zip(encoded_faces,faces_in_frame):
            matches = face_recognition.compare_faces(encoded_face_train, encode_face)
            faceDist = face_recognition.face_distance(encoded_face_train, encode_face)
            matchIndex = np.argmin(faceDist)
            print(matchIndex)
            if matches[matchIndex]:
                name = classNames[matchIndex].upper().lower()
                y1,x2,y2,x1 = faceloc
                # since we scaled down by 4 times
                y1, x2,y2,x1 = y1*4,x2*4,y2*4,x1*4
                cv2.rectangle(img,(x1,y1),(x2,y2),(0,255,0),2)
                cv2.rectangle(img, (x1,y2-35),(x2,y2), (0,255,0), cv2.FILLED)
                cv2.putText(img,name, (x1+6,y2-5), cv2.FONT_HERSHEY_COMPLEX,1,(255,255,255),2)
                ## Attendance row insert in database
                print(name)
                setattendance(name, subject_id)
                break
        cv2.imshow('webcam', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()
    return redirect(url_for('success', subject_id=subject_id))

@app.route('/manualsuccess')
def manualsuccess():
    return render_template('manual_success.html')

@app.route('/manual/<int:subject_id>')
def manual(subject_id):
    user_email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (user_email,))
    userdata = cur.fetchone()
    user_id = userdata[0]
    username = userdata[1]
    cur.execute("INSERT INTO attendance(user_id, username, date, subject_id) VALUES(%s, %s, %s, %s)", (user_id, username, date.today(), subject_id))
    mysql.connection.commit()
    msg = Message('Hello',sender ='attendenceid01@gmail.com',recipients = ['attendenceid01@gmail.com'])
    msg.body = username + ' has taken attendance manually on ' + str(date.today())
    mail.send(msg)
    return redirect(url_for('manualsuccess'))




@app.route('/login', methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND pwd = %s", (email, password))
        data = cur.fetchone()
        if data:
            session['email'] = email
            session['loggedin'] = True
            if data[2] == '2':
                return redirect(url_for('stdashboard'))
            else:
                return redirect(url_for('trdashboard'))
    return render_template('login.html')

@app.route('/signup', methods =['GET', 'POST'])
def signup():
    msg=''
    if request.method == 'POST' and 'username' in request.form and 'usertype' in request.form and 'phone' in request.form and 'email' in request.form and 'password' in request.form:
        username = request.form['username']
        usertype = request.form['usertype']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(username, usertype, phone, email, pwd) VALUES(%s, %s, %s, %s, %s)", (username, usertype, phone, email, password))
        mysql.connection.commit()
        msg = 'You are now registered and can log in'
        return render_template('signup.html', msg=msg)
    return render_template('signup.html')

def setattendance(name, subject_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s ", (name,))
    user = cur.fetchone()
    if user:
        user_id = user[0]
        cur.execute("SELECT * FROM attendance WHERE user_id = %s AND subject_id = %s AND date = %s", (user_id, subject_id, date.today()))
        data = cur.fetchone()
        if data == None:
            username = name
            todays_date = date.today()
            cur.execute("INSERT INTO attendance(user_id, username, date, subject_id) VALUES(%s, %s, %s, %s)", (user_id, username, todays_date, subject_id))
            mysql.connection.commit()
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if user:
                user_email = user[4]
                msg = Message('Hello',sender ='attendenceid01@gmail.com',recipients = [user_email])
                msg.body = 'Hello Flask message sent from Flask-Mail'
                mail.send(msg)
            cv2.destroyAllWindows()
app.jinja_env.globals.update(setattendance=setattendance)

def getsubjectname(abbr):
    if abbr == 'h':
        return 'Hindi'
    elif abbr == 'm':
        return 'Maths'
    elif abbr == 'e':
        return 'English'
    elif abbr == 's':
        return 'Science'
    elif abbr == 'c':
        return 'Computer'
    elif abbr == 'g':
        return 'General Knowledge'
app.jinja_env.globals.update(getsubjectname=getsubjectname)

def checkattendancepercentage(classid,class_creation_date,student_id):
    tddate = date.today()
    format = '%Y-%m-%d'
    class_creation_date = datetime.strptime(class_creation_date, format)
    class_creation_date = class_creation_date.date()
    total_days = (tddate - class_creation_date).days
    total_days = total_days + 1
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM attendance")
    data = cur.fetchall()
    attednded_days = 0
    for row in data:
        if row[1] == student_id and row[4] == classid:
            attednded_days += 1
    percentage = (attednded_days/total_days)*100
    return percentage
app.jinja_env.globals.update(checkattendancepercentage=checkattendancepercentage)


