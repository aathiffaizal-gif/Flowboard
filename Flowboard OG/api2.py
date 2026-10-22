from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import sqlite3
import os

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'Flowboard.db')

# Helper function to get a database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This allows fetching results as dictionaries
    return conn

#####API 1
# Route to get a random trivia question from the8 database
@app.route('/randomtask', methods=['GET'])
def get_random_task():
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
   
    # Fetch all tasks from the database
    cursor.execute("SELECT * FROM Tasks")
    task_list = cursor.fetchall()
   
    # Close the database connection
    conn.close()
   
    if task_list:
        # Select a random trivia question from the list
        tasks = random.choice(task_list)
        return jsonify({"Task ID": tasks["Task_ID"], "Due_Date": tasks["Due_Date"], "Task Name": tasks["Task_Name"], "Task Description": tasks["Task_Description"], "User ID": tasks["User_ID"], "Board_ID": tasks["Board_ID"]})
    else:
        return jsonify({"error": "No tasks found in the database."}), 404
 
#API 2
# Route to get trivia for a specific superhero
@app.route('/tasks/<User_ID>', methods=['GET'])
def get_task_for_user(User_ID):
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
   
    # Fetch tasks for the specified user
    cursor.execute("SELECT * FROM Tasks WHERE User_ID = ?", (User_ID))
    tasks = cursor.fetchone()
   
    # Close the database connection
    conn.close()
   
    if tasks:
        return jsonify({"Task_ID": tasks["Task_ID"], "Due_Date": tasks["Due_Date"], "Priority": tasks["Priority"], "Task_Name": tasks["Task_Name"], "Task_Description": tasks["Task_Description"], "User_ID": tasks["User_ID"], "Board_ID": tasks["Board_ID"]})
    else:
        return jsonify({"error": f"No tasks found for user '{User_ID}'."}), 404
 
 
#API 3
# Route to add a new trivia entry to the database
@app.route('/addtask', methods=['POST'])
def add_task():
    data = request.get_json()  # Get the JSON data from the request
   
    # Validate the JSON data
    if not data or 'task_ID' not in data or 'Due_Date' not in data or 'Task_Name' not in data:
        return jsonify({"error": "Invalid data. 'Task_ID', 'Task_Name', and 'Due_Date' are required fields."}), 400
   
    Task_ID = data['Task_ID']
    Task_Name = data['Task_Name']
    Due_Date = data['Due_Date']
   
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
   
    # Insert the new task into the database
    cursor.execute("INSERT INTO Tasks (Task_ID, Task_Name, Due_Date) VALUES (?, ?, ?)", (Task_ID, Task_Name, Due_Date))
    conn.commit()  # Save (commit) the changes to the database
    conn.close()
   
    return jsonify({"message": "New task added successfully!"}), 201
 
 
#API - 4
# New route to update tasks for a specific user
@app.route('/updatetask/<user_ID>', methods=['PUT'])
def update_task_for_user(user_ID):
    data = request.get_json()
   
    # Validate the input data
    if not data or 'Task_Name' not in data or 'Due_Date' not in data or 'Priority' not in data or 'Task_Description' not in data:
        return jsonify({"error": "Invalid data. 'Task_Name' and 'Due_Date' and 'Priority' and 'Task_Description' are required fields."}), 400
   
    Task_Name = data['Task_Name']
    Due_Date = data['Due_Date']
    Priority = data['Priority']
    Task_Description = data['Task_Description']
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
 
    # Update tasks for the specified user
    cursor.execute("UPDATE Taskss SET Task_Name = ?, Due_Date = ?, Priority = ?, Task_Description = ? WHERE User_ID = ?", (Task_Name, Due_Date, Priority, Task_Description, user_ID))
    rows_updated = cursor.rowcount  # Get the number of rows updated
    conn.commit()  # Save changes
    conn.close()
   
    if rows_updated > 0:
        return jsonify({"message": f"Updated task for user '{user_ID}'", "rows_updated": rows_updated}), 200
    else:
        return jsonify({"error": f"No tasks found for user '{user_ID}'."}), 404

from flask import Flask, jsonify, request
 

 
@app.route('/tasks/search', methods=["GET"])
def search_tasks():
    query = request.args.get("name", "")
 
    conn = get_db_connection()
    # Ensure rows are returned as dictionary-like objects
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
 
    cursor.execute("SELECT * FROM Tasks WHERE Task_Name LIKE ?", (f"%{query}%",))
    Tasks = cursor.fetchall()
    conn.close()
 
    # Convert sqlite3.Row objects into standard dictionaries
    task_list = [dict(row) for row in Tasks]
 
    return jsonify(task_list), 20

@app.route('/boards/search', methods=["GET"])
def search_boards():
    query = request.args.get("name", "")
 
    conn = get_db_connection()
    # Ensure rows are returned as dictionary-like objects
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
 
    cursor.execute("SELECT * FROM Boards WHERE Board_Name LIKE ?", (f"%{query}%",))
    Boards = cursor.fetchall()
    conn.close()
 
    # Convert sqlite3.Row objects into standard dictionaries
    board_list = [dict(row) for row in Boards]
 
    return jsonify(board_list), 20



# Quiz mode endpoint
##def quiz_mode():
    #if request.method == 'GET':
        # TODO: Connect to the database and fetch a list of trivia questions
        # conn = (Connect to the database)
        # cursor = (Create a cursor from the connection)
        # cursor.execute("SELECT * FROM trivia")  # Query to fetch trivia questions
        # trivia_list = (Fetch all trivia questions)
        # conn.close()  # Close the database connection

        # TODO: Check if trivia_list contains questions
        # if trivia_list:
            # TODO: Select a random trivia question and return it as JSON (excluding the answer)
            # trivia = (Select a random trivia item from trivia_list)
            # return jsonify({"Superhero": (Superhero name), "Question": (Question text)})
        # else:
            # TODO: Return a 404 error if no trivia is found in the database
            # return jsonify({"error": "No trivia found in the database."}), 404
        

    #elif request.method == 'POST':
        # TODO: Retrieve JSON data from the request
        # data = (Get JSON data from the request)
        # hero = (Extract 'hero' from data)
        # user_answer = (Extract 'answer' from data)

        # TODO: Validate that both 'hero' and 'answer' fields are present
        # if (Check if hero or user_answer is missing):
            # return jsonify({"error": "Hero and answer are required fields."}), 400

        # TODO: Connect to the database and fetch the correct answer for the given hero
        # conn = (Connect to the database)
        # cursor = (Create a cursor from the connection)
        # cursor.execute("SELECT * FROM trivia WHERE hero = ?", (hero,))
        # trivia = (Fetch one trivia item for the specified hero)
        # conn.close()  # Close the database connection

        # TODO: Check if trivia is found for the given hero
        # if trivia:
            # correct_answer = (Retrieve correct answer from trivia item)
            # TODO: Compare the user's answer to the correct answer (case insensitive)
            # if (User answer matches correct answer):
                # return jsonify({"result": "Correct!", "correct_answer": correct_answer})
            # else:
                # return jsonify({"result": "Incorrect", "correct_answer": correct_answer})
        # else:
            # TODO: Return a 404 error if no trivia is found for the specified hero
            # return jsonify({"error": f"No trivia found for superhero '{hero}'."}), 404
            #print()



# Start the Flask server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555)


