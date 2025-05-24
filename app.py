from flask import Flask, render_template,redirect, request, jsonify, request, jsonify, send_from_directory, url_for, send_file
from dotenv import load_dotenv
import os
import json
import ast
import fitz
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from gemeniapi import query_gemini
from flask_sqlalchemy import SQLAlchemy
import datetime
from werkzeug.utils import secure_filename
import zipfile
import tempfile
import shutil
import random
from flask_cors import CORS


load_dotenv()  # Load environment variables from .env file
api_key = os.getenv('GEMINI_API_KEY')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Student.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

migrate = Migrate(app, db)

# TODO: move the database models to a separate file
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    solution = db.Column(db.Text, nullable=True)
    correct = db.Column(db.Boolean, nullable=False)
    annotation = db.Column(db.Text, nullable=True)
    def __repr__(self):
        return f'<Student {self.name}>'
    
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    course = db.Column(db.String(100))
    weight = db.Column(db.Integer, default=100)
    subject = db.Column(db.String(100))
    rubric = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationship with submissions
    submissions = db.relationship('Submission', backref='assignment', lazy=True)
    
    def __repr__(self):
        return f'<Assignment {self.name}>'

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    grading_breakdown = db.Column(db.JSON, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Submission {self.student_name} for Assignment {self.assignment_id}>'
    
def create_tables():
    db.create_all()
    return "All students deleted from the database!"

# TODO: to be removed after testing, and replaced with a dynamic test case generator or a test case file
# test_cases = [
#         {"input": "[]", "expected": 0},
#         {"input": "[1, 3, 5]", "expected": 0},
#         {"input": "[2, 4, 6]", "expected": 12},
#         {"input": "[1, 2, 3, 4, 5, 6]", "expected": 12},
#         {"input": "[-2, -3, 4]", "expected": 2},
#         {"input": "[0, 1, 2, 3]", "expected": 2},
#         {"input": "[10]", "expected": 10},
#         {"input": "[7]", "expected": 0},
#         {"input": "[1, -2, -4, 3, 0]", "expected": -6},
#         {"input": "[100, 101, 102]", "expected": 202}
#     ]
test_cases = []
@app.route("/")
def home():
    assignments = Assignment.query.all()
    students = Student.query.all()
    return render_template("index.html", assignments=assignments, students=students)

@app.route("/assignment/<int:assignment_id>")
def view_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Get all submissions for this assignment
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    
    return render_template("assignment_detail.html", assignment=assignment, submissions=submissions)

@app.route("/add_assignment", methods=["POST"])
def add_assignment():
    # TODO: currently the only information we have about this assignment is the description, but we need the file full description of the assignment
    data = request.get_json()
    
    name = data.get("name")
    description = data.get("description")
    course = data.get("course", "")
    weight = data.get("weight", 100)
    subject = data.get("subject", "NA")
    
    if not name or not description:
        return jsonify({"error": "Name and description are required"}), 400
    
    # Default rubric structure TODO: Make this dynamic
    default_rubric = {
        "Correctness": 50,
        "Edge Cases": 20,
        "Code Quality": 20,
        "Error Handling": 10
    }
    
    new_assignment = Assignment(
        name=name,
        description=description,
        course=course,
        weight=weight,
        subject=subject,
        rubric=default_rubric # rubric is a json object that is added to the assignment object
    )
    
    db.session.add(new_assignment)
    db.session.commit()
    
    return jsonify({
        "message": "Assignment created successfully",
        "id": new_assignment.id,
        "name": new_assignment.name
    }), 201

@app.route("/add_submission", methods=["POST"])
def add_submission():
    assignment_id = request.form.get("assignment_id")
    student_name = request.form.get("student_name")
    content = request.form.get("content")
    
    if not assignment_id or not student_name or not content:
        return jsonify({"error": "Assignment ID, student name, and content are required"}), 400
    
    # Check if assignment exists
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    
    # Check if student exists (optional linking to Student model)
    student = Student.query.filter_by(name=student_name).first()
    student_id = student.id if student else None
    
    submission = Submission(
        student_name=student_name,
        student_id=student_id,
        assignment_id=assignment_id,
        content=content
    )
    
    # If there's a file upload
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename:
            # Create uploads directory if it doesn't exist
            uploads_dir = os.path.join(app.root_path, 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            # Save the file
            filename = secure_filename(f"{student_name}_{assignment_id}_{file.filename}")
            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)
            
            # Save file path in submission
            submission.file_path = file_path
    
    db.session.add(submission)
    db.session.commit()
    
    return jsonify({"message": "Submission added successfully", "id": submission.id}), 201

@app.route("/get_assignments")
def get_assignments():
    assignments = Assignment.query.all()
    assignments_list = []
    
    for a in assignments:
        assignments_list.append({
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "course": a.course,
            "weight": a.weight,
            "submission_count": Submission.query.filter_by(assignment_id=a.id).count()
        })
    
    return jsonify({"assignments": assignments_list})

@app.route("/grading_dashboard")
def grading_dashboard():
    assignment_id = request.args.get('assignment_id')
    
    if assignment_id:
        # Load the specific assignment
        assignment = Assignment.query.get_or_404(assignment_id)
        
        # Get submissions for this assignment
        submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
        
        # Create student objects from submissions for compatibility with existing code
        students = []
        for submission in submissions:
            # Check if a Student object already exists
            student = Student.query.filter_by(name=submission.student_name).first()
            
            if not student:
                # Create a temporary Student object for the template
                student = Student(
                    name=submission.student_name,
                    solution=submission.content,
                    correct=bool(submission.grading_breakdown),  # Assume correct if graded
                    annotation=submission.grading_breakdown.get('evaluation', '') if submission.grading_breakdown else ''
                )
            
            students.append(student)
        
        # Use the actual assignment for the template
        return render_template("grading_dashboard.html", assignment=assignment, test_cases=test_cases, students=students)
    else:
        # Default behavior (original code)
        students = Student.query.all()
        
        for student in students:
            student.escaped_solution = json.dumps(student.solution)

        return render_template("grading_dashboard.html", assignment=assignment, test_cases=test_cases, students=students)


# assisting function to compute the final score from the grading breakdown
def compute_final_score(grading_breakdown):
    if not grading_breakdown or 'scores' not in grading_breakdown:
        return 0.0
        
    scores = grading_breakdown['scores']
    gemini_score = 0.0

    if 'total' in scores:
        gemini_score = float(scores['total'])
        
    else:
        for score in scores.items():
            if isinstance(score, (int, float)):
                gemini_score += score
    
    if 'test_cases' in grading_breakdown:
        test_results = grading_breakdown['test_cases']
        test_score = (test_results['passed'] / (test_results['passed'] + test_results['failed'])) * 50
        
    final_score = gemini_score + test_score
    return final_score


def pdf_to_json(pdf_stream):
    try:
        doc = fitz.open(pdf_stream)  # Open PDF directly from the file stream
        pdf_data = {}

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            
            # Check if any text is extracted
            if page_text.strip():  # If there's any non-whitespace text
                pdf_data[f"page_{page_num + 1}"] = page_text
            else:
                pdf_data[f"page_{page_num + 1}"] = "No text found on this page."
        
        return pdf_data if pdf_data else None

    except Exception as e:
        print(f"Error processing PDF: {e}")
        return None
    
# TODO: make use of this function to create the rubric for the assignment given the assignment full description
def generate_rubric_based_on_description(assignment_description):
    prompt = f"""
    Generate a rubric for a programming assignment based on the following description:
    {assignment_description} 
    
    Please evaluate the description, create a rubric according to the description and return a JSON response exactly formatted as:
  "rubric": {{
      "criteria 1": <points in integer>,
      "criteria 2": <points in integer>,
      "criteria 3": <points in integer>,
      "etc.": <points in integer>
  }}
  The total should be 100 points.
  Note that the format is really important, each criteria should be a key-value pair for JSON object. The criteria is a string with 
  quotations and the points are integers without quotations.
  make rubric for the assignment based on the description,
    Limit the criteria to 6 or fewer for simplicity,
    """
    response = query_gemini(prompt, api_key)  # Assuming query_gemini is your AI call

    # Handle and clean the response from AI to parse as JSON or structured rubric
    print(response)
    cleaned_response = response.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[len("```json"):].strip()
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3].strip()
    if cleaned_response.startswith("{") and cleaned_response.endswith("}"):
    # Remove the first and last characters (curly braces)
        cleaned_response = cleaned_response[1:-1].strip()
    if cleaned_response.startswith('"rubric":'):
        cleaned_response = cleaned_response[len('"rubric":'):].strip()
    print(f"Cleaned response: {cleaned_response}")
    try:
        rubric = json.loads(cleaned_response)
        print(f"Generated rubric: {rubric}")
        return rubric
    except Exception as e:
        print(f"Error generating rubric: {e}")
        return None
    
@app.route("/run_code", methods=["POST"])
def run_code():
    data = request.json
    student_name = data.get("student_name")
    assignment_id = data.get("assignment_id")  # Optional parameter
    custom_test_cases = data.get("test_cases")  # Check for custom test cases from frontend

    # Try both Student and Submission objects
    solution = None
    
    # First try to find the student
    student = Student.query.filter_by(name=student_name).first()
    if student:
        solution = student.solution
    
    # If no student or assignment_id is specified, try to find a submission
    if not solution or assignment_id:
        submission = None
        if assignment_id:
            submission = Submission.query.filter_by(student_name=student_name, assignment_id=assignment_id).first()
        else:
            # Try to find any submission by this student
            submission = Submission.query.filter_by(student_name=student_name).first()
        
        if submission:
            solution = submission.content
    
    if not solution:
        return jsonify({"error": f"No solution found for '{student_name}'"}), 404

    # Use custom test cases if provided, otherwise use the global test_cases
    current_test_cases = custom_test_cases if custom_test_cases else test_cases

    results = {"passed": 0, "failed": 0, "details": []}

    try:
        # Dynamically execute the student's solution in an isolated environment
        exec_globals = {}
        exec(solution, exec_globals)

        # Extract the function name dynamically
        function_name = next((name for name in exec_globals if callable(exec_globals[name])), None)
        if not function_name:
            raise ValueError("No callable function found in the provided solution.")

        function = exec_globals[function_name]

        for test_case in current_test_cases:
            input_data = ast.literal_eval(test_case["input"])
            expected_output = test_case["expected"]
            

            try:
                print(f"[run_code] Testing student '{student_name}' solution...")
                print(f"[run_code] Test case: {test_case['input']} expected: {expected_output}")
                # Call the student's function
                actual_output = function(input_data)
                if actual_output == expected_output:
                    results["passed"] += 1
                    results["details"].append({"input": test_case["input"], "status": "Passed"})
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "input": test_case["input"],
                        "status": "Failed",
                        "expected": expected_output,
                        "actual": actual_output
                    })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "input": test_case["input"],
                    "status": "Error",
                    "error": str(e)
                })

    except Exception as e:
        results["failed"] = len(current_test_cases)
        results["details"] = [{"input": "N/A", "status": "Error", "error": str(e)}]

    return jsonify(results)

@app.route("/evaluate_student", methods=["POST"])
def evaluate_student():
    data = request.get_json()
    student_name = data.get("student_name")
    assignment_id = data.get("assignment_id")  # Optional parameter
    
    # First, try to get student from database
    student = Student.query.filter_by(name=student_name).first()
    
    # If no student found or if assignment_id is provided, check for submissions
    if not student or assignment_id:
        submission = None
        if assignment_id:
            submission = Submission.query.filter_by(student_name=student_name, assignment_id=assignment_id).first()
        else:
            # Get any submission by this student name
            submission = Submission.query.filter_by(student_name=student_name).first()
        
        if submission:
            # Get the assignment related to this submission
            current_assignment = Assignment.query.get(submission.assignment_id)
            
            prompt = f"""Assignment: {current_assignment.name}
Description: {current_assignment.description}

Student Name: {student_name}
Student Solution:
{submission.content}

Please evaluate this solution based on the following rubric:
"""
            # Add rubric criteria to the prompt
            for criterion, points in current_assignment.rubric.items():
                prompt += f"- {criterion} ({points} points)\n"
            
            prompt += """
Format your response as a JSON object with the following structure:
{
  "scores": {
    "total": <total score (0-100)>,
"""
            # Add individual rubric criteria to expected JSON format
            for criterion in current_assignment.rubric.keys():
                criterion_key = criterion.lower().replace(" ", "_")
                prompt += f'    "{criterion_key}": <score>,\n'
            
            prompt += """  },
  "evaluation": "<detailed explanation of the grading>"
}"""
        else:
            return jsonify({"error": "Student submission not found."}), 404
    else:
        # Use the existing student object and global assignment
        print("[evaluate_student] Prompt sent to Gemini:\n", prompt)
        prompt = f"""Assignment: {assignment['title']}
Description: {assignment['description']}

Student Name: {student.name}
Student Solution:
{student.solution}

Rubric: {assignment['rubric']}

Please evaluate the solution based on the above rubric and return a JSON response exactly formatted as:
{{
  "scores": {{
      "total": <total score (0-100)>,
      "correctness": <score out of 50>,
      "edge_cases": <score out of 20>,
      "code_quality": <score out of 20>,
      "error_handling": <score out of 10>
  }},
  "evaluation": "<short explanation>"
}}"""
    
    # Send the prompt to the AI service
    response = query_gemini(prompt, api_key)
    print("[evaluate_student] Raw response from Gemini:", response)

    # Clean up response if it is wrapped in markdown code fence blocks
    cleaned_response = response.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[len("```json"):].strip()
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3].strip()
    try:
        res_json = json.loads(cleaned_response)
        
        # If this is a submission, update the grading_breakdown
        if submission:
            submission.grading_breakdown = res_json
            db.session.commit()
        
    except Exception as e:
        print("[evaluate_student] JSON parse error:", e)
        return jsonify({"error": f"Invalid JSON response: {str(e)}"}), 500
    return jsonify(res_json)

@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.get_json()
    name = data.get('student_name')
    solution = data.get('student_solution')

    # Fix: You missed required fields
    if not name or not solution:
        return jsonify({'error': 'Missing student name or solution!'}), 400

    # Check if student already exists
    existing_student = Student.query.filter_by(name=name).first()
    if existing_student:
        return jsonify({'error': 'Student with this name already exists!'}), 400

    # Create a new student entry
    student = Student(name=name, solution=solution, correct=False, annotation="")
    db.session.add(student)
    db.session.commit()

    return jsonify({'message': 'Student added successfully!'}), 200

@app.route('/delete')   
def delete_students():
    # Delete all students
    Student.query.delete()
    db.session.commit()
    return "All students deleted from the database!"

@app.route("/get_submission/<int:submission_id>")
def get_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    
    # Return submission data as JSON
    return jsonify({
        "id": submission.id,
        "student_name": submission.student_name,
        "assignment_id": submission.assignment_id,
        "content": submission.content,
        "file_path": submission.file_path,
        "submitted_at": submission.submitted_at,
        "grading_breakdown": submission.grading_breakdown
    })

@app.route("/grade_submission/<int:submission_id>", methods=["POST"])
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = Assignment.query.get_or_404(submission.assignment_id)
    
    # Construct evaluation prompt
    prompt = f"""Assignment: {assignment.name}
Description: {assignment.description}

Student Name: {submission.student_name}
Student Solution:
{submission.content}

Please evaluate this solution based on the following rubric:
"""
    
    # Add rubric criteria to the prompt
    for criterion, points in assignment.rubric.items():
        prompt += f"- {criterion} ({points} points)\n"
    
    prompt += """
Format your response as a JSON object with the following structure:
{
  "scores": {
    "total": <total score 0-100>,
"""

    # Add individual rubric criteria to expected JSON format
    for criterion in assignment.rubric.keys():
        criterion_key = criterion.lower().replace(" ", "_")
        prompt += f'    "{criterion_key}": <score>,\n'
    
    prompt += """  },
  "evaluation": "<detailed explanation of the grading>"
}
"""
    
    # Call the AI service
    try:
        response = query_gemini(prompt, api_key)
        
        # Parse the response
        if isinstance(response, dict) and 'error' in response:
            return jsonify({"error": response['error']}), 500
        
        # Clean up JSON if needed
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[len("```json"):].strip()
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3].strip()
        
        # Parse the JSON response
        grading_data = json.loads(cleaned_response)
        
        # Ensure the grading_data has a scores.total property
        if 'scores' in grading_data and 'total' not in grading_data['scores']:
            # Calculate total from other scores if available
            if grading_data['scores']:
                score_values = [score for key, score in grading_data['scores'].items() if isinstance(score, (int, float))]
                if score_values:
                    grading_data['scores']['total'] = round(sum(score_values) / len(score_values))
                else:
                    grading_data['scores']['total'] = 0
            else:
                grading_data['scores']['total'] = 0
        
        # Update the submission with grading data
        submission.grading_breakdown = grading_data
        db.session.commit()
        
        return jsonify({
            "message": "Submission graded successfully",
            "grading": grading_data
        })
        
    except Exception as e:
        return jsonify({"error": f"Error during grading: {str(e)}"}), 500

@app.route('/uploads/<path:filename>')
def download_file(filename):
    uploads_dir = os.path.join(app.root_path, 'uploads')
    return send_from_directory(directory=uploads_dir, path=filename)

@app.route("/bulk_management")
def bulk_management():
    assignments = Assignment.query.all()
    return render_template("bulk_submissions.html", assignments=assignments)

@app.route("/bulk_upload", methods=["POST"])
def bulk_upload():
    # Get form data
    assignment_id = request.form.get("assignment_id")
    file_structure = request.form.get("file_structure", "student_folders")
    
    if not assignment_id:
        return jsonify({"error": "Assignment ID is required"}), 400
    
    # Check if assignment exists
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    
    # Check if file was uploaded
    if 'submissions_zip' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    zip_file = request.files['submissions_zip']
    if zip_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not zip_file.filename.lower().endswith('.zip'):
        return jsonify({"error": "File must be a ZIP archive"}), 400
    
    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save and extract the zip file
        zip_path = os.path.join(temp_dir, secure_filename(zip_file.filename))
        zip_file.save(zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Process the extracted files based on structure
        processed_submissions = []
        
        if file_structure == "student_folders":
            # Each folder is a student name with submission files inside
            for item in os.listdir(temp_dir):
                if item == zip_file.filename:
                    continue
                
                student_dir = os.path.join(temp_dir, item)
                if os.path.isdir(student_dir):
                    student_name = item
                    submission_files = os.listdir(student_dir)
                    
                    if submission_files:
                        # Get the first file as submission content
                        main_file = os.path.join(student_dir, submission_files[0])
                        with open(main_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Save submission to database
                        submission = create_submission(student_name, assignment_id, content)
                        
                        # Save file path if we want to keep the file
                        for file in submission_files:
                            file_path = os.path.join(student_dir, file)
                            # Copy to uploads directory
                            dest_path = save_to_uploads(file_path, student_name, assignment_id)
                            if main_file == file_path:
                                submission.file_path = dest_path
                                db.session.commit()
                        
                        processed_submissions.append({
                            "student_name": student_name,
                            "status": "Processed successfully"
                        })
        
        else:  # filename_prefix
            # Files are named like "student_name_filename.ext"
            for item in os.listdir(temp_dir):
                if item == zip_file.filename or os.path.isdir(os.path.join(temp_dir, item)):
                    continue
                
                parts = item.split('_', 1)
                if len(parts) > 1:
                    student_name = parts[0]
                    file_path = os.path.join(temp_dir, item)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Save submission to database
                    submission = create_submission(student_name, assignment_id, content)
                    
                    # Save file path
                    dest_path = save_to_uploads(file_path, student_name, assignment_id)
                    submission.file_path = dest_path
                    db.session.commit()
                    
                    processed_submissions.append({
                        "student_name": student_name,
                        "status": "Processed successfully"
                    })
        
        return jsonify({
            "success": True,
            "processed": len(processed_submissions),
            "submissions": processed_submissions
        })
        
    except Exception as e:
        return jsonify({"error": f"Error processing ZIP file: {str(e)}"}), 500
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

def create_submission(student_name, assignment_id, content):
    """Helper function to create a submission in the database"""
    student = Student.query.filter_by(name=student_name).first()
    student_id = student.id if student else None
    
    submission = Submission(
        student_name=student_name,
        student_id=student_id,
        assignment_id=assignment_id,
        content=content
    )
    
    db.session.add(submission)
    db.session.commit()
    return submission

def save_to_uploads(file_path, student_name, assignment_id):
    """Save a file to the uploads directory and return the path"""
    uploads_dir = os.path.join(app.root_path, 'uploads')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    
    filename = secure_filename(f"{student_name}_{assignment_id}_{os.path.basename(file_path)}")
    dest_path = os.path.join(uploads_dir, filename)
    shutil.copy2(file_path, dest_path)
    return dest_path

@app.route("/generate_test_data", methods=["POST"])
def generate_test_data():
    assignment_id = request.form.get("test_assignment_id")
    student_count = int(request.form.get("student_count", 10))
    solution_type = request.form.get("solution_type", "mixed")
    output_format = request.form.get("output_format", "zip")
    
    if not assignment_id:
        return jsonify({"error": "Assignment ID is required"}), 400
    
    # Check if assignment exists
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    
    # Cap the student count at a reasonable number
    student_count = min(student_count, 50)
    
    # Generate sample submissions
    submissions = []
    
    # Get sample solutions based on the assignment
    sample_solutions = get_sample_solutions(assignment.name)
    
    # Create temporary directory for zip file generation if needed
    temp_dir = None
    if output_format == "zip":
        temp_dir = tempfile.mkdtemp()
    
    try:
        for i in range(student_count):
            # Generate student name
            student_name = f"Student_{i+1:02d}"
            
            # Determine if this solution should be correct
            is_correct = True
            if solution_type == "incorrect":
                is_correct = False
            elif solution_type == "mixed":
                is_correct = random.choice([True, False])
            
            # Get appropriate solution content
            if is_correct:
                content = random.choice(sample_solutions["correct"])
            else:
                content = random.choice(sample_solutions["incorrect"])
            
            # Add to database if direct database option selected
            if output_format == "database":
                submission = create_submission(student_name, assignment_id, content)
                
                # Set correctness in database for testing
                student = Student.query.filter_by(name=student_name).first()
                if not student:
                    student = Student(name=student_name, solution=content, correct=is_correct, annotation="Test data")
                    db.session.add(student)
                    db.session.commit()
                    submission.student_id = student.id
                    db.session.commit()
            
            # For zip output, create a file
            elif temp_dir:
                student_dir = os.path.join(temp_dir, student_name)
                os.makedirs(student_dir, exist_ok=True)
                
                with open(os.path.join(student_dir, "submission.py"), "w", encoding="utf-8") as f:
                    f.write(content)
            
            submissions.append({
                "student_name": student_name,
                "correct": is_correct
            })
        
        # Create zip file if requested
        zip_path = None
        file_url = None
        
        if output_format == "zip" and temp_dir:
            zip_filename = f"test_submissions_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = os.path.join(app.root_path, 'uploads', zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(
                            file_path, 
                            os.path.relpath(file_path, temp_dir)
                        )
            
            file_url = url_for('download_file', filename=zip_filename)
        
        return jsonify({
            "success": True,
            "count": student_count,
            "output_format": output_format,
            "file_url": file_url,
            "submissions": submissions
        })
    
    except Exception as e:
        return jsonify({"error": f"Error generating test data: {str(e)}"}), 500
    
    finally:
        # Clean up temporary directory if created
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def get_sample_solutions(assignment_name):
    """Return sample correct and incorrect solutions based on assignment name"""
    
    # Default for "Sum of Even Numbers" assignment
    correct_solutions = [
        "def sum_even(numbers):\n    return sum(x for x in numbers if x % 2 == 0)",
        "def sum_even(numbers):\n    total = 0\n    for num in numbers:\n        if num % 2 == 0:\n            total += num\n    return total",
        "def sum_even(numbers):\n    even_numbers = []\n    for num in numbers:\n        if num % 2 == 0:\n            even_numbers.append(num)\n    return sum(even_numbers)"
    ]
    
    incorrect_solutions = [
        "def sum_even(numbers):\n    return sum(numbers)",
        "def sum_even(numbers):\n    total = 0\n    for x in numbers:\n        if x % 2 == 1:  # Checks odd instead of even\n            total += x\n    return total",
        "def sum_even(numbers):\n    count = 0\n    for num in numbers:\n        if num % 2 == 0:\n            count += 1  # Counts evens rather than summing\n    return count",
        "def sum_even(numbers)  # Missing colon\n    total = 0\n    for x in numbers:\n        if x % 2 == 0:\n            total += x\n    return total"
    ]
    
    # Customize based on assignment name if needed
    if "factorial" in assignment_name.lower():
        correct_solutions = [
            "def factorial(n):\n    if n == 0 or n == 1:\n        return 1\n    else:\n        return n * factorial(n-1)",
            "def factorial(n):\n    result = 1\n    for i in range(2, n+1):\n        result *= i\n    return result",
            "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"
        ]
        
        incorrect_solutions = [
            "def factorial(n):\n    return n + factorial(n-1) if n > 0 else 0",  # Addition instead of multiplication
            "def factorial(n):\n    result = 0\n    for i in range(1, n+1):\n        result += i\n    return result",  # Sum instead of product
            "def factorial(n):\n    if n == 0:\n        return 0\n    else:\n        return n * factorial(n-1)",  # Wrong base case
            "def factorial(n)\n    result = 1\n    for i in range(2, n+1):\n        result *= i\n    return result"  # Missing colon
        ]
    
    return {
        "correct": correct_solutions,
        "incorrect": incorrect_solutions
    }

@app.route("/get_student_results")
def get_student_results():
    student_name = request.args.get('student_name')
    assignment_id = request.args.get('assignment_id')
    
    if not student_name:
        return jsonify({"error": "Student name is required"}), 400
    
    # First check if we have a submission for this student
    submission = None
    if assignment_id:
        submission = Submission.query.filter_by(
            student_name=student_name, 
            assignment_id=assignment_id
        ).first()
    else:
        # If no assignment_id is provided, get any submission from this student
        submission = Submission.query.filter_by(student_name=student_name).first()
    
    # If submission exists and has grading data
    if submission and submission.grading_breakdown:
        # Return the grading data with test results if available
        result = submission.grading_breakdown
        
        # Check if we need to add a 'total' score to scores
        if 'scores' in result and 'total' not in result['scores']:
            if result['scores']:
                score_values = [score for key, score in result['scores'].items() 
                               if isinstance(score, (int, float))]
                if score_values:
                    result['scores']['total'] = round(sum(score_values) / len(score_values))
                else:
                    result['scores']['total'] = 0
            else:
                result['scores']['total'] = 0
        
        return jsonify(result)
    
    # If no submission or no grading data, check student model
    student = Student.query.filter_by(name=student_name).first()
    if student and student.annotation:
        # Construct a result object with available data
        result = {
            "evaluation": student.annotation,
            "scores": {
                "total": 100 if student.correct else 0
            }
        }
        return jsonify(result)
    
    # No results found
    return jsonify({"error": "No evaluation results found for this student"}), 404

@app.route("/save_grading_result", methods=["POST"])
def save_grading_result():
    data = request.get_json()
    student_name = data.get("student_name")
    assignment_id = data.get("assignment_id")
    grading_result = data.get("grading_result")
    final_score = data.get("final_score")
    
    if not student_name or not grading_result:
        return jsonify({"error": "Student name and grading result are required"}), 400
    
    # Find the submission to update
    submission = None
    if assignment_id:
        submission = Submission.query.filter_by(
            student_name=student_name, 
            assignment_id=assignment_id
        ).first()
    else:
        # Try to find any submission by this student
        submission = Submission.query.filter_by(student_name=student_name).first()
    
    if not submission:
        return jsonify({"error": "No submission found for this student"}), 404
    
    # Ensure the grading_result has a scores.total property
    if 'scores' in grading_result:
        if 'total' not in grading_result['scores'] or final_score is not None:
            grading_result['scores']['total'] = final_score or 0
    else:
        grading_result['scores'] = {'total': final_score or 0}
    
    # Update the submission with the grading data
    submission.grading_breakdown = grading_result
    db.session.commit()
    
    # Also update the student record if it exists
    student = Student.query.filter_by(name=student_name).first()
    if student:
        student.correct = (final_score >= 70) if final_score is not None else False
        student.annotation = grading_result.get('evaluation', '')
        db.session.commit()
    
    return jsonify({"message": "Grading result saved successfully"})

@app.route("/update_assignment_description", methods=["POST"])
def update_assignment_description():
    data = request.get_json()
    assignment_id = data.get("assignment_id")
    description = data.get("description")
    
    if not assignment_id or not description:
        return jsonify({"error": "Assignment ID and description are required"}), 400
    
    # Get the assignment
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    
    # Update the description
    assignment.description = description
    db.session.commit()
    
    return jsonify({"message": "Assignment description updated successfully"}), 200

@app.route("/update_assignment_rubric", methods=["POST"])
def update_assignment_rubric():
    data = request.get_json()
    assignment_id = data.get("assignment_id")
    rubric = data.get("rubric")
    
    if not assignment_id or not rubric:
        return jsonify({"error": "Assignment ID and rubric are required"}), 400
    
    # Get the assignment
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    
    # Validate the rubric structure and ensure percentages add up to 100
    total_percentage = sum(points for points in rubric.values())
    if total_percentage != 100:
        return jsonify({"error": f"Rubric percentages must sum to 100% (currently {total_percentage}%)"}), 400
    
    # Update the rubric
    assignment.rubric = rubric
    db.session.commit()
    
    return jsonify({"message": "Assignment rubric updated successfully"}), 200

@app.route("/generate_test_cases", methods=["POST"])
def generate_test_cases():
    data = request.get_json()
    assignment_id = data.get("assignment_id")
    
    if not assignment_id:
        return jsonify({"error": "Assignment ID is required"}), 400
    
    # Get the assignment
    assignment = Assignment.query.get(assignment_id)
    if not assignment:
        return jsonify({"error": "Assignment not found"}), 404
    
    # Create prompt for the AI to generate test cases based on the assignment
    prompt = f"""
    Assignment: {assignment.name}
    Description: {assignment.description}
    
    Generate 10 comprehensive test cases for this programming assignment. 
    Each test case should include an input value and the expected output.
    The test cases should cover various scenarios including edge cases.
    
    Return ONLY a JSON array in this exact format:
    [
      {{"input": "<input value>", "expected": <expected output>}},
      ...
    ]
    
    Do not include any markdown formatting, explanations, or other text outside the JSON array.
    """
    
    try:
        # Query Gemini API to generate test cases
        response = query_gemini(prompt, api_key)
        
        # Clean up response (remove any markdown code fences)
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[len("```json"):].strip()
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3].strip()
        
        # Parse JSON response
        generated_test_cases = json.loads(cleaned_response)
        
        # Update the global test_cases variable in app.py (this is what the user requested)
        global test_cases
        test_cases = generated_test_cases
        
        # Return the generated test cases to the client
        return jsonify({"test_cases": generated_test_cases}), 200
        
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse generated test cases: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error generating test cases: {str(e)}"}), 500

@app.route("/delete_submission/<int:submission_id>", methods=["DELETE"])
def delete_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    
    # Store file path if we need to delete the file too
    file_path = submission.file_path
    
    # Delete from database
    db.session.delete(submission)
    db.session.commit()
    
    # Delete the associated file if it exists
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            # Continue even if file deletion fails
            print(f"Warning: Could not delete file {file_path}: {str(e)}")
    
    return jsonify({"message": "Submission deleted successfully"}), 200

if __name__ == "__main__":
    with app.app_context():
        create_tables()
    app.run(debug=True)
