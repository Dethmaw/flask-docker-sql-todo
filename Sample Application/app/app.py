
import re  
import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors

app = Flask(__name__) 

app.secret_key = 'abcdefgh'
  
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'cs353hw4db'
  
mysql = MySQL(app)  

@app.route('/')

@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s AND password = % s', (username, password, ))
        user = cursor.fetchone()
        if user:              
            session['loggedin'] = True
            session['userid'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return redirect(url_for('tasks'))
        else:
            message = 'Please enter correct email / password !'
    return render_template('login.html', message = message)


@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s', (username, ))
        account = cursor.fetchone()
        if account:
            message = 'Choose a different username!'
  
        elif not username or not password or not email:
            message = 'Please fill out the form!'

        else:
            cursor.execute('INSERT INTO User (id, username, email, password) VALUES (NULL, % s, % s, % s)', (username, email, password,))
            mysql.connection.commit()
            message = 'User successfully created!'

    elif request.method == 'POST':

        message = 'Please fill all the fields!'
    return render_template('register.html', message = message)

@app.route('/tasks', methods =['GET', 'POST'])
def tasks():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('SELECT * FROM Task WHERE user_id = %s AND status = "Todo" ORDER BY deadline', (session['userid'],))
    todo_tasks = cursor.fetchall()
    
    cursor.execute('SELECT * FROM Task WHERE user_id = %s AND status = "Done" ORDER BY done_time DESC', (session['userid'],))
    done_tasks = cursor.fetchall()

    return render_template('tasks.html', todo_tasks=todo_tasks, done_tasks=done_tasks)

@app.route('/edit_task/<int:task_id>', methods =['GET', 'POST'])
def edit_task(task_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Task WHERE id = %s', (task_id,))
    task = cursor.fetchone()
    if task['user_id'] != session['userid']:
        return redirect(url_for('tasks'))
    if request.method == 'POST' and 'title' in request.form and 'description' in request.form and 'deadline' in request.form:
        title = request.form['title']
        description = request.form['description']
        deadline = request.form['deadline']
        cursor.execute('UPDATE Task SET title = %s, description = %s, deadline = %s WHERE id = %s', (title, description, deadline, task_id))
        mysql.connection.commit()
        return redirect(url_for('tasks'))
    return render_template('edit_task.html', task=task)


@app.route('/delete_task/<int:task_id>', methods =['GET', 'POST'])
def delete_task(task_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Task WHERE id = %s', (task_id,))
    task = cursor.fetchone()
    if task['user_id'] != session['userid']:
        return redirect(url_for('tasks'))
    cursor.execute('DELETE FROM Task WHERE id = %s', (task_id,))
    mysql.connection.commit()
    return redirect(url_for('tasks'))

@app.route('/create_task', methods =['GET', 'POST'])
def create_task():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST' and 'title' in request.form and 'description' in request.form and 'deadline' in request.form:
        title = request.form['title']
        description = request.form['description']
        deadline = request.form['deadline']
        task_type = request.form['task_type']
        status = 'Todo'

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO Task (title, description, status, deadline, user_id, task_type, creation_time) VALUES (%s, %s, %s, %s, %s, %s, NOW())', (title, description, status, deadline, session['userid'], task_type))
        mysql.connection.commit()
        return redirect(url_for('tasks'))
    return render_template('create_task.html')

@app.route('/update_task_status/<int:task_id>', methods=['POST'])
def update_task_status(task_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Task WHERE id = %s', (task_id,))
    task = cursor.fetchone()

    if task['user_id'] != session['userid']:
        return redirect(url_for('tasks'))

    status = request.form['status']

    cursor.execute('UPDATE Task SET status = %s, done_time = NOW() WHERE id = %s', (status, task_id,))
    mysql.connection.commit()

    return redirect(url_for('tasks'))


@app.route('/analysis', methods=['GET'])
def analysis():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Query 1: List the title and latency of the tasks that were completed after their deadlines.
    query1 = '''
    SELECT title, TIMESTAMPDIFF(MINUTE, deadline, done_time) AS latency
    FROM Task
    WHERE user_id = %s AND status = "Done" AND done_time > deadline
    ORDER BY latency DESC;
    '''
    cursor.execute(query1, (session['userid'],))
    late_tasks = cursor.fetchall()

    # Query 2: Calculate the average task completion time.
    query2 = '''
    SELECT AVG(TIMESTAMPDIFF(MINUTE, creation_time, done_time)) AS avg_completion_time
    FROM Task
    WHERE user_id = %s AND status = "Done";
    '''
    cursor.execute(query2, (session['userid'],))
    avg_completion_time = cursor.fetchone()['avg_completion_time']

    # Query 3: Count the number of completed tasks per task type in descending order.
    query3 = '''
    SELECT task_type, COUNT(*) as count
    FROM Task
    WHERE user_id = %s AND status = "Done"
    GROUP BY task_type
    ORDER BY count DESC;
    '''
    cursor.execute(query3, (session['userid'],))
    tasks_per_type = cursor.fetchall()

    # Query 4: List the title and deadline of uncompleted tasks in increasing order of deadlines.
    query4 = '''
    SELECT title, deadline
    FROM Task
    WHERE user_id = %s AND status = "Todo"
    ORDER BY deadline;
    '''
    cursor.execute(query4, (session['userid'],))
    upcoming_tasks = cursor.fetchall()

    # Query 5: List the title and task completion time of the top 2 completed tasks that took the most time.
    query5 = '''
    SELECT title, TIMESTAMPDIFF(MINUTE, creation_time, done_time) AS completion_time
    FROM Task
    WHERE user_id = %s AND status = "Done"
    ORDER BY completion_time DESC
    LIMIT 2;
    '''
    cursor.execute(query5, (session['userid'],))
    top2_longest_tasks = cursor.fetchall()

    return render_template('analysis.html', late_tasks=late_tasks, avg_completion_time=avg_completion_time, tasks_per_type=tasks_per_type, upcoming_tasks=upcoming_tasks, top2_longest_tasks=top2_longest_tasks)

@app.route('/logout')
def logout():
    if 'loggedin' in session:
        session.pop('loggedin', None)
        session.pop('userid', None)
        session.pop('username', None)
        session.pop('email', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
    
