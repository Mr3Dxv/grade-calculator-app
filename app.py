# app.py
# --- This is the main Python file for our Flask App ---

from flask import Flask, render_template, request
import os
import firebase_admin
from firebase_admin import credentials, firestore

# --- Firebase Initialization ---
# IMPORTANT: Make sure the 'firebase_key.json' file is in the same directory as this app.py file.
try:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Successfully connected to Firebase.")
except Exception as e:
    print(f"Could not connect to Firebase: {e}")
    # You might want to exit the app if Firebase connection fails
    # For this example, we'll allow it to run but leaderboard will be empty.
    db = None


# --- Flask App Initialization ---
app = Flask(__name__)

# The MODULES dictionary remains the same.
MODULES = {
    'Principles of Computing': {
        'assessments': {'Coursework': 20, 'Mid-term Exam': 30, 'Final Exam': 50},
        'type': 'standard'
    },
    'Database': {
        'assessments': {'Final Exam': 50, 'Assessment': 50},
        'type': 'standard'
    },
    'Digital Evidence': {
        'assessments': {'Written Assignments': 50, 'Portfolios': 50},
        'type': 'standard'
    },
    'C++': {
        'assessments': {'Spoken Assessment': 50, 'Practical Assignment': 50},
        'type': 'standard'
    },
    'Web Programming': {
        'assessments': {'Group Project': 70, 'Portfolios': 30},
        'type': 'standard'
    },
    'AI': {
        'assessments': {'Practical Assignment': 50, 'Spoken Exam': 50},
        'type': 'standard'
    },
    'English for Academic Purposes (IELTS)': {
        'assessments': {'Listening': 0, 'Reading': 0, 'Writing': 0, 'Speaking': 0},
        'type': 'ielts'
    }
}

# We no longer need the local list for leaderboard data.
# leaderboard_data = []

# --- Helper function to calculate a score for a single module ---
def calculate_module_score(module_name, form_data):
    module_info = MODULES[module_name]
    assessments = module_info['assessments']
    module_type = module_info['type']
    total_score = 0

    if module_type == 'ielts':
        if 'include_ielts' not in form_data:
            return None 
        
        listening = float(form_data.get('IELTS-Listening', 0))
        reading = float(form_data.get('IELTS-Reading', 0))
        writing = float(form_data.get('IELTS-Writing', 0))
        speaking = float(form_data.get('IELTS-Speaking', 0))
        
        if any([listening, reading, writing, speaking]):
            raw_average = (listening + reading + writing + speaking) / 4
            total_score = round(raw_average * 2) / 2
        else:
            return None
    else:
        for assessment_name, weight in assessments.items():
            input_name = f"{module_name}-{assessment_name}"
            score = float(form_data.get(input_name, 0))
            total_score += score * (weight / 100.0)
            
    return total_score

# --- Routes (The URLs of our website) ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        student_name = request.form.get('name')
        
        module_scores = {}
        standard_scores_list = []

        for name in MODULES:
            if MODULES[name]['type'] == 'standard':
                score = calculate_module_score(name, request.form)
                if score is not None:
                    module_scores[name] = score
                    standard_scores_list.append(score)

        ielts_score = calculate_module_score('English for Academic Purposes (IELTS)', request.form)
        if ielts_score is not None:
            module_scores['English for Academic Purposes (IELTS)'] = ielts_score

        overall_score = 0
        if standard_scores_list:
            overall_score = sum(standard_scores_list) / len(standard_scores_list)

        # --- NEW FIREBASE LOGIC: Saving data ---
        if db:
            try:
                # Create a dictionary with the data to save.
                data_to_save = {
                    'name': student_name,
                    'score': overall_score,
                    'timestamp': firestore.SERVER_TIMESTAMP # Good practice to store a timestamp
                }
                # Add a new document to the 'leaderboard' collection.
                # Firestore will automatically generate a unique ID for the document.
                db.collection('leaderboard').add(data_to_save)
                print(f"Successfully saved data for {student_name} to Firestore.")
            except Exception as e:
                print(f"Error saving to Firestore: {e}")

        return render_template('result.html',
                               name=student_name,
                               overall_score=overall_score,
                               module_scores=module_scores)

    return render_template('index.html', modules=MODULES)


@app.route('/leaderboard')
def leaderboard():
    leaderboard_entries = []
    # --- NEW FIREBASE LOGIC: Reading data ---
    if db:
        try:
            # Get all documents from the 'leaderboard' collection.
            # Order them by 'score' in descending order (highest first).
            docs = db.collection('leaderboard').order_by('score', direction=firestore.Query.DESCENDING).stream()
            for doc in docs:
                leaderboard_entries.append(doc.to_dict())
            print("Successfully fetched leaderboard from Firestore.")
        except Exception as e:
            print(f"Error fetching from Firestore: {e}")
            
    # We no longer need to sort here, as Firestore does it for us.
    return render_template('leaderboard.html', leaderboard=leaderboard_entries)


if __name__ == '__main__':
    app.run(debug=True)
