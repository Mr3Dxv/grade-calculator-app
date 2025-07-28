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
    # Check if the app is already initialized to prevent errors on reload
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Successfully connected to Firebase.")
except Exception as e:
    print(f"Could not connect to Firebase: {e}")
    db = None


# --- Flask App Initialization ---
app = Flask(__name__)

# The MODULES dictionary now includes Computer Architecture.
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
    # --- NEW MODULE ADDED HERE ---
    'Computer Architecture': {
        'type': 'pre-graded',
        'note': 'Grade found in email from the first result sheet'
    },
    'English for Academic Purposes (IELTS)': {
        'assessments': {'Listening': 0, 'Reading': 0, 'Writing': 0, 'Speaking': 0},
        'type': 'ielts'
    }
}


# --- Helper function to calculate a score for a single module ---
def calculate_module_score(module_name, form_data):
    module_info = MODULES[module_name]
    module_type = module_info.get('type')
    total_score = 0

    if module_type == 'ielts':
        if 'include_ielts' not in form_data:
            return None 
        # ... (IELTS calculation logic remains the same)
        listening = float(form_data.get('IELTS-Listening', 0))
        reading = float(form_data.get('IELTS-Reading', 0))
        writing = float(form_data.get('IELTS-Writing', 0))
        speaking = float(form_data.get('IELTS-Speaking', 0))
        if any([listening, reading, writing, speaking]):
            raw_average = (listening + reading + writing + speaking) / 4
            total_score = round(raw_average * 2) / 2
        else: return None
    
    # --- NEW LOGIC FOR PRE-GRADED MODULE ---
    elif module_type == 'pre-graded':
        input_name = f"{module_name}-grade"
        score_str = form_data.get(input_name)
        if score_str: # Check if a value was entered
            total_score = float(score_str)
        else:
            return None # Return None if no grade was entered

    elif module_type == 'standard':
        assessments = module_info['assessments']
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
        academic_scores_list = [] # List for scores to be averaged

        # Loop through all modules to calculate scores
        for name, module_data in MODULES.items():
            score = calculate_module_score(name, request.form)
            if score is not None:
                module_scores[name] = score
                # Add to the list for averaging ONLY if it's an academic module
                if module_data['type'] in ['standard', 'pre-graded']:
                    academic_scores_list.append(score)

        # Calculate overall average from ONLY the academic modules
        overall_score = 0
        if academic_scores_list:
            overall_score = sum(academic_scores_list) / len(academic_scores_list)

        # Save data to Firebase
        if db:
            try:
                data_to_save = {
                    'name': student_name,
                    'score': overall_score,
                    'timestamp': firestore.SERVER_TIMESTAMP
                }
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
    if db:
        try:
            docs = db.collection('leaderboard').order_by('score', direction=firestore.Query.DESCENDING).stream()
            for doc in docs:
                leaderboard_entries.append(doc.to_dict())
            print("Successfully fetched leaderboard from Firestore.")
        except Exception as e:
            print(f"Error fetching from Firestore: {e}")
            
    return render_template('leaderboard.html', leaderboard=leaderboard_entries)


if __name__ == '__main__':
    app.run(debug=True)
