"""
=============================================================
TASK MANAGER BACKEND - TEACHING TEMPLATE
=============================================================
Keep the existing task and board routes working.
Student TODOs only: /register, /login, /logout, /me, login_required,
                   POST /Boards/<Board_ID>/tasks (link an existing task).
Study the matching /examples/* club examples in section 1.
Task/board routes and logout are wired to login_required. Complete the guard
first: until then protected routes return 501. Register/login and the page stay public.
GET/DELETE board-task links remain provided so you can see/remove your links.
Run this file and open http://localhost:5555. No quiz route is included.
=============================================================
"""

from flask import Flask, jsonify, request, session, send_file
from flask_cors import CORS
import random
import sqlite3
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app, supports_credentials=True)   # supports_credentials is needed for sessions with CORS

# ---------------------------------------------------------------
# SECRET KEY — Flask uses this to sign the session cookie.
# In a real project, store this in an environment variable,
# never hardcode it. But for learning, this is fine.
# ---------------------------------------------------------------
app.secret_key = "super_secret_key_change_this_in_production"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'T_Todo.db')


# ---------------------------------------------------------------
# DB HELPER
# ---------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row   # lets us access columns by name: row["task_name"]
    return conn


# ---------------------------------------------------------------
# DB SETUP — creates tables if they don't exist yet
# Run this once when the server starts.
# ---------------------------------------------------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Task table ---
    # Task_id is INTEGER PRIMARY KEY AUTOINCREMENT — SQLite assigns the number
    # automatically (1, 2, 3, ...) every time a new task is inserted.
    # The frontend does NOT send a Task_id; the backend returns the generated one.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Task (
            Task_ID           INTEGER PRIMARY KEY AUTOINCREMENT,
            Task_Name         TEXT NOT NULL,
            Task_Description  TEXT,
            Task_TimeRequirement TEXT,
            Priority          TEXT DEFAULT 'medium',
            Creation_Date      TEXT,
            Task_Status        TEXT DEFAULT 'pending',
            Board_ID          INTEGER REFERENCES Board(Board_ID), -- optional: which board this task belongs to
            User_ID           TEXT REFERENCES User(username)  -- optional: which user created this task
        )
    """)

    # --- Board table ---
    # A board is a named collection of tasks (like a project or category)
    tables = {row[0] for row in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if 'Group' in tables and 'Board' not in tables:
        cursor.execute("ALTER TABLE [Group] RENAME TO Board")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Board (
            Board_ID    INTEGER PRIMARY KEY AUTOINCREMENT,
            Board_name  TEXT NOT NULL,
            created_by  TEXT    -- the username of whoever made it
        )
    """)

    # --- BoardTask join table ---
    # This is a many-to-many relationship:
    #   one task can belong to many boards
    #   one board can have many tasks
    # We store just the IDs of both sides.
    # Both Board_ID and Task_ID are INTEGER to match their parent tables.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS BoardTask (
            Board_ID INTEGER,
            Task_ID  INTEGER,
            PRIMARY KEY (Board_id, task_id)
        )
    """)

    # --- NEW: User table ---
    # Store a generate_password_hash() result in User.password, never plain text.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS User (
            username  TEXT PRIMARY KEY,
            password  TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()



# ===============================================================
# 1. WORKING EXAMPLES — read these first
# ===============================================================
# Separate club data and demo_member session; adapt the patterns in section 2.
def init_examples():
    conn = get_db_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS DemoMember (name TEXT PRIMARY KEY, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS DemoClub (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE IF NOT EXISTS DemoActivity (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE IF NOT EXISTS DemoClubActivity (
            club_id INTEGER, activity_id INTEGER, PRIMARY KEY (club_id, activity_id)
        );
        INSERT OR IGNORE INTO DemoClub VALUES (1, 'Art club');
        INSERT OR IGNORE INTO DemoActivity VALUES (1, 'Painting');
    """)
    conn.commit()
    conn.close()


def example_credentials():
    """Shared input check for the two demo forms."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    if not all(isinstance(data.get(k), str) and data[k].strip() for k in ('name', 'password')):
        return None
    return data['name'].strip(), data['password']


@app.route('/examples/register', methods=['POST'])
def example_register():
    # Pattern: validate -> hash -> insert -> handle duplicate -> success.
    credentials = example_credentials()
    if not credentials:
        return jsonify({"error": "Name and password are required."}), 400
    name, password = credentials
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO DemoMember VALUES (?, ?)",
                     (name, generate_password_hash(password)))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Member already exists."}), 409
    finally:
        conn.close()
    return jsonify({"message": "Club member registered. Now log in."}), 201


@app.route('/examples/login', methods=['POST'])
def example_login():
    credentials = example_credentials()
    if not credentials:
        return jsonify({"error": "Name and password are required."}), 400
    name, password = credentials
    conn = get_db_connection()
    member = conn.execute("SELECT * FROM DemoMember WHERE name = ?", (name,)).fetchone()
    conn.close()
    if not member or not check_password_hash(member['password'], password):
        return jsonify({"error": "Invalid club credentials."}), 401
    session['demo_member'] = member['name']
    return jsonify({"message": "Club login successful.", "name": member['name']})


@app.route('/examples/logout', methods=['POST'])
def example_logout():
    session.pop('demo_member', None)  # Only clear this demo's identity.
    return jsonify({"message": "Club logout successful."})


@app.route('/examples/me', methods=['GET'])
def example_me():
    name = session.get('demo_member')
    if name:
        return jsonify({"logged_in": True, "name": name})
    return jsonify({"logged_in": False}), 401


def example_login_required(f):
    # A decorator checks the session before executing the protected function.
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'demo_member' not in session:
            return jsonify({"error": "Log in to the club first."}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/examples/clubs/<int:club_id>/activities', methods=['POST'])
@example_login_required
def example_add_activity(club_id):
    # Pattern for adding an EXISTING task to an EXISTING board.
    data = request.get_json(silent=True)
    activity_id = data.get('activity_id') if isinstance(data, dict) else None
    if type(activity_id) is not int or activity_id <= 0:
        return jsonify({"error": "activity_id must be a positive integer."}), 400
    conn = get_db_connection()
    club = conn.execute("SELECT id FROM DemoClub WHERE id = ?", (club_id,)).fetchone()
    activity = conn.execute("SELECT id FROM DemoActivity WHERE id = ?", (activity_id,)).fetchone()
    if not club or not activity:
        conn.close()
        return jsonify({"error": "Club or activity not found."}), 404
    conn.execute("INSERT OR IGNORE INTO DemoClubActivity VALUES (?, ?)", (club_id, activity_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Activity linked to club (repeating creates no duplicate)."})


@app.route('/examples/clubs/<int:club_id>/activities', methods=['GET'])
@example_login_required
def example_list_activities(club_id):
    # Lets students verify the link and see that logout blocks protected reads.
    conn = get_db_connection()
    club = conn.execute("SELECT id FROM DemoClub WHERE id = ?", (club_id,)).fetchone()
    if not club:
        conn.close()
        return jsonify({"error": "Club not found."}), 404
    rows = conn.execute("""SELECT DemoActivity.* FROM DemoActivity
                           JOIN DemoClubActivity ON DemoActivity.id = DemoClubActivity.activity_id
                           WHERE DemoClubActivity.club_id = ?""", (club_id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])



# ===============================================================
# 2. STUDENT EXERCISES — complete these next
# ===============================================================
# Define login_required before routes use it. Protected routes return 501
# until this exercise is completed. Flask sessions use signed browser cookies.
def login_required(f):
    """STUDENT TEMPLATE — study example_login_required() in section 1.
    All task/board routes use this decorator. Until completed, they return 501.
    After completing it: no session -> 401; valid session -> execute the route.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"error": "Log in first."}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/register', methods=['POST'])
def register():
    """STUDENT TEMPLATE — study example_register() in section 1.
    Input JSON: {username, password}. Use the existing User table.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Username and password are required."}), 400
    if not all(isinstance(data.get(k), str) and data[k].strip() for k in ('username', 'password')):
        return jsonify({"error": "Username and password are required."}), 400

    username = data['username'].strip()
    password = data['password']

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO User (username, password) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists."}), 409
    finally:
        conn.close()
    return jsonify({"message": "User registered. Now log in."}), 201


@app.route('/login', methods=['POST'])
def login():
    """STUDENT TEMPLATE — study example_login() in section 1."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Username and password are required."}), 400
    if not all(isinstance(data.get(k), str) and data[k].strip() for k in ('username', 'password')):
        return jsonify({"error": "Username and password are required."}), 400

    username = data['username'].strip()
    password = data['password']

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM User WHERE username = ?", (username,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password'], password):
        return jsonify({"error": "Invalid credentials."}), 401

    session['username'] = user['username']
    return jsonify({"message": "Login successful.", "username": user['username']})


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """STUDENT TEMPLATE — study example_logout() in section 1."""
    session.pop('username', None)
    return jsonify({"message": "Logout successful."})


@app.route('/me', methods=['GET'])
def me():
    """STUDENT TEMPLATE — study example_me() in section 1."""
    username = session.get('username')
    if username:
        return jsonify({"logged_in": True, "username": username})
    return jsonify({"logged_in": False}), 401


@app.route('/Boards/<int:Board_ID>/tasks', methods=['POST'])
@login_required
def add_task_to_board(Board_ID):
    """STUDENT TEMPLATE — study example_add_activity() in section 1.
    POST /Boards/<Board_ID>/tasks with JSON {task_id: integer}.
    Here Board_ID is the existing Board.Board_ID.
    """
    data = request.get_json(silent=True)
    task_id = data.get('task_id') if isinstance(data, dict) else None
    if type(task_id) is not int or task_id <= 0:
        return jsonify({"error": "task_id must be a positive integer."}), 400

    conn = get_db_connection()
    board = conn.execute("SELECT Board_ID FROM Board WHERE Board_ID = ?", (Board_ID,)).fetchone()
    task = conn.execute("SELECT Task_ID FROM Task WHERE Task_ID = ?", (task_id,)).fetchone()
    if not board or not task:
        conn.close()
        return jsonify({"error": "Board or task not found."}), 404

    conn.execute(
        "INSERT OR IGNORE INTO BoardTask (Board_ID, Task_ID) VALUES (?, ?)",
        (Board_ID, task_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Task linked to board (repeating creates no duplicate)."})



# ===============================================================
# 3. ALREADY IMPLEMENTED — keep these route bodies as provided
# ===============================================================
@app.route('/tasks', methods=['GET'])
@login_required
def get_random_task():
    conn = get_db_connection()
    tasks_list = conn.execute("SELECT * FROM Task").fetchall()
    conn.close()
    if tasks_list:
        task = random.choice(tasks_list)
        return jsonify([dict(task)])
    return jsonify({"error": "No tasks found."}), 404


@app.route('/tasks/<int:Task_ID>', methods=['GET'])
@login_required
def get_task_by_id(Task_ID):
    # <int:task_id> tells Flask to only match this route if the value is an integer.
    # It also automatically converts the string from the URL into a Python int.
    conn = get_db_connection()
    Task = conn.execute("SELECT * FROM Task WHERE Task_id = ?", (Task_ID,)).fetchone()
    conn.close()
    if Task:
        return jsonify([dict(Task)])
    return jsonify({"error": f"Task '{Task_ID}' not found."}), 404


@app.route('/tasks/search', methods=['GET'])
@login_required
def search_tasks():
    query = request.args.get("Task_Name", "")
    conn = get_db_connection()
    tasks = conn.execute("SELECT * FROM Task WHERE Task_Name LIKE ?", (f"%{query}%",)).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tasks])


@app.route('/addtasks', methods=['POST'])
@login_required
def add_task():
    data = request.get_json()
    # Task_id is NOT in required — the database generates it automatically.
    required = ['Task_TimeRequirement', 'Priority', 'Task_Name',
                'Task_Description', 'Creation_Date', 'Task_Status']
    if not isinstance(data, dict) or not all(isinstance(data.get(f), str) for f in required):
        return jsonify({"error": "Missing required fields."}), 400

    if not data['Task_Name'].strip():
        return jsonify({"error": "Task name is required."}), 400
    if data['Priority'] not in ('high', 'medium', 'low') or data['Task_Status'] not in ('pending', 'in-progress', 'done'):
        return jsonify({"error": "Invalid priority or status."}), 400

    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO Task (Task_TimeRequirement, Priority, Task_Name, Task_Description, Creation_Date, Task_Status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data['Task_TimeRequirement'], data['Priority'], data['Task_Name'], data['Task_Description'], data['Creation_Date'], data['Task_Status'])
        # Notice: no Task_id in the columns list or values — SQLite fills it in.
    )
    new_id = cursor.lastrowid   # grab the auto-generated ID so we can return it
    conn.commit()
    conn.close()
    # Return the new ID so the frontend can use it immediately (e.g. to open the edit modal)
    return jsonify({"message": "Task added!", "Task_ID": new_id}), 201


@app.route('/updatetasks/<int:Task_ID>', methods=['PUT'])
@login_required
def update_task(Task_ID):
    data = request.get_json()
    required = ['Task_Name', 'Task_Description', 'Task_TimeRequirement',
                'Priority', 'Creation_Date', 'Task_Status']
    if not isinstance(data, dict) or not all(isinstance(data.get(f), str) for f in required):
        return jsonify({"error": "Missing required task fields."}), 400

    if not data['Task_Name'].strip():
        return jsonify({"error": "Task name is required."}), 400
    if data['Priority'] not in ('high', 'medium', 'low') or data['Task_Status'] not in ('pending', 'in-progress', 'done'):
        return jsonify({"error": "Invalid priority or status."}), 400

    conn = get_db_connection()
    result = conn.execute(
        """UPDATE Task SET task_name=?, task_description=?,
                           Task_TimeRequirement=?, Priority=?, Creation_Date=?, Task_Status=?
           WHERE Task_id=?""",
        (data.get('Task_Name'), data.get('Task_Description'),
         data.get('Task_TimeRequirement'), data.get('Priority'),
         data.get('Creation_Date'), data.get('Task_Status'), Task_ID)
    )
    conn.commit()
    conn.close()
    if result.rowcount > 0:
        return jsonify({"message": f"Task '{Task_ID}' updated."})
    return jsonify({"error": "Task not found."}), 404


@app.route('/tasks/<int:Task_ID>', methods=['DELETE'])
@login_required
def delete_task(Task_ID):
    """
    HOW IT WORKS:
    - The client sends DELETE to /tasks/abc123
    - We try to remove that row from the Task table
    - We also clean up any BoardTask entries that linked to it
      (otherwise we'd have "orphan" rows pointing at a deleted task)
    - If nothing was deleted (rowcount == 0) the task didn't exist → 404
    """
    conn = get_db_connection()

    # Remove from any boards first (clean up the join table)
    conn.execute("DELETE FROM BoardTask WHERE Task_ID = ?", (Task_ID,))

    # Now delete the task itself
    result = conn.execute("DELETE FROM Task WHERE Task_ID = ?", (Task_ID,))
    conn.commit()
    conn.close()

    if result.rowcount > 0:
        return jsonify({"message": f"Task '{Task_ID}' deleted."})
    return jsonify({"error": "Task not found."}), 404


@app.route('/Boards', methods=['POST'])
@login_required
def create_board():
    """
    Create a new Board (e.g. "Project Alpha", "Work Tasks").
    
    Expected JSON body:
    {
      "Board_name": "Project Alpha"
    }
    
    We also save who created the board by reading the session.
    @login_required checks the session before this route runs.
    """
    data = request.get_json()
    if not isinstance(data, dict) or not isinstance(data.get('Board_name'), str) or not data['Board_name'].strip():
        return jsonify({"error": "'Board_name' is required."}), 400

    creator = session['username']   # reads from session — explained below

    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO Board (Board_name, created_by) VALUES (?, ?)",
        (data['Board_name'], creator)
    )
    new_id = cursor.lastrowid   # SQLite gives us the auto-generated ID
    conn.commit()
    conn.close()

    return jsonify({"message": "board created!", "Board_ID": new_id}), 201


@app.route('/Boards', methods=['GET'])
@login_required
def get_all_boards():
    """Return every Board."""
    conn = get_db_connection()
    boards = conn.execute("SELECT * FROM Board").fetchall()
    conn.close()
    return jsonify([dict(b) for b in boards])


@app.route('/Boards/search', methods=['GET'])
@login_required
def search_board():
    query = request.args.get("board_name", "")
    conn = get_db_connection()
    boards = conn.execute(
        "SELECT * FROM Board WHERE Board_name LIKE ?", (f"%{query}%",)
    ).fetchall()
    conn.close()
    return jsonify([dict(b) for b in boards])


@app.route('/Boards/<int:Board_ID>', methods=['DELETE'])
@login_required
def delete_board(Board_ID):
    """Delete a board and its links; keep the original tasks."""
    conn = get_db_connection()
    conn.execute("DELETE FROM BoardTask WHERE Board_ID = ?", (Board_ID,))
    conn.execute("UPDATE Task SET Board_ID = NULL WHERE Board_ID = ?", (Board_ID,))
    result = conn.execute("DELETE FROM Board WHERE Board_ID = ?", (Board_ID,))
    conn.commit()
    conn.close()
    if result.rowcount > 0:
        return jsonify({"message": "Board deleted."})
    return jsonify({"error": "Board not found."}), 404


@app.route('/Boards/<int:Board_ID>/tasks', methods=['GET'])
@login_required
def get_tasks_in_board(Board_ID):
    """
    Return all tasks that belong to a specific board.
    
    SQL JOIN explanation for students:
      BoardTask holds (Board_ID, Task_ID) pairs.
      We JOIN with Task on Task_ID to get the full task details.
    """
    conn = get_db_connection()
    board = conn.execute("SELECT * FROM Board WHERE Board_ID = ?", (Board_ID,)).fetchone()
    if not board:
        conn.close()
        return jsonify({"error": "Board not found."}), 404

    tasks = conn.execute(
        """SELECT Task.* FROM Task
           JOIN BoardTask ON Task.Task_ID = BoardTask.Task_ID
           WHERE BoardTask.Board_ID = ?""",
        (Board_ID,)
    ).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tasks])


@app.route('/Boards/<int:Board_ID>/tasks/<task_id>', methods=['DELETE'])
@login_required
def remove_task_from_board(Board_ID, task_id):
    """Remove a task from a board (without deleting the task itself)."""
    conn = get_db_connection()
    result = conn.execute(
        "DELETE FROM BoardTask WHERE Board_ID = ? AND Task_ID = ?",
        (Board_ID, task_id)
    )
    conn.commit()
    conn.close()
    if result.rowcount > 0:
        return jsonify({"message": "Task removed from board."})
    return jsonify({"error": "That task is not in that board."}), 404


@app.route('/my-tasks', methods=['GET'])
@login_required
def my_tasks():
    """
    Returns boards created by the currently logged-in user.
    This is just an example to show @login_required in action.
    """
    username = session['username']
    conn = get_db_connection()
    boards = conn.execute(
        "SELECT * FROM Board WHERE created_by = ?", (username,)
    ).fetchall()
    conn.close()
    return jsonify({
        "username": username,
        "my_boards": [dict(b) for b in boards]
    })


@app.route('/')
def teaching_page():
    return send_file(os.path.join(BASE_DIR, 'ui_complete.html'))



if __name__ == '__main__':
    init_db()    # create tables on startup
    init_examples()  # separate worked-example tables
    app.run(host='0.0.0.0', port=5555, debug=True)

