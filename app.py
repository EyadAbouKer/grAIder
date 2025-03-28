from flask import Flask, render_template,redirect, request, jsonify, request, jsonify
from dotenv import load_dotenv
import os
import json
import ast
import fitz
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from gemeniapi import query_gemini
from flask_sqlalchemy import SQLAlchemy


load_dotenv()  # Load environment variables from .env file
api_key = os.getenv('GEMINI_API_KEY')

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Student.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

migrate = Migrate(app, db)

assignment = {
    "title": "Sum of Even Numbers",
    "description": "Write a Python function called `sum_even(numbers)` that accepts a list of integers and returns the sum of all even numbers in that list.",
    "rubric": {
        "Correctness": 50,
        "Edge Cases": 20,
        "Code Quality": 20,
        "Error Handling": 10
    }
}


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    solution = db.Column(db.Text, nullable=True)
    correct = db.Column(db.Boolean, nullable=False)
    annotation = db.Column(db.Text, nullable=True)
    def __repr__(self):
        return f'<Student {self.name}>'
    
def create_tables():
    db.create_all()
    


    
    return "All students deleted from the database!"
test_cases = [
    {"input": "[]", "expected": "0"},
    {"input": "[1, 3, 5]", "expected": "0"},
    {"input": "[2, 4, 6]", "expected": "12"},
    {"input": "[1, 2, 3, 4, 5, 6]", "expected": "12"},
    {"input": "[-2, -3, 4]", "expected": "2"},
    {"input": "[0, 1, 2, 3]", "expected": "2"},
    {"input": "[10]", "expected": "10"},
    {"input": "[7]", "expected": "0"},
    {"input": "[1, -2, -4, 3, 0]", "expected": "-6"},
    {"input": "[100, 101, 102]", "expected": "202"}
]

    #evaluate the students solutions based on the assignment
    #studentEvaluator(students, assignment, api_key)
    # print(evaluations[0])
    
    # return render_template("grading_dashboard.html", assignment=assignment, test_cases=test_cases, students=students, evaluations=evaluations[0])

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/grading_dashboard")
def grading_dashboard():
    students = Student.query.all()
    
    for student in students:
        student.escaped_solution = json.dumps(student.solution)

    return render_template("grading_dashboard.html", assignment=assignment, test_cases=test_cases, students=students)

@app.route("/seed_data")  
def seed_data():
    if not Student.query.first():
        students = [
            {"name": "Alice", "solution": "def sum_even(numbers):\n    return sum(x for x in numbers if x % 2 == 0)", "correct": True, "annotation": "Correct solution."},
            {"name": "Bob", "solution": "def sum_even(numbers):\n    total = 0\n    for x in numbers:\n        if x % 2 == 1:\n            total += x\n    return total", "correct": False, "annotation": "Checks for odd numbers instead of even."},
            {"name": "Charlie", "solution": "def sum_even(numbers):\n    total = 0\n    for num in numbers:\n        if num % 2 == 0:\n            total += num\n    return total", "correct": True, "annotation": "Correct solution."},
            {"name": "Diana", "solution": "def sum_even(numbers)  # Missing colon here\n    total = 0\n    for x in numbers:\n        if x % 2 == 0:\n            total += x\n    return total", "correct": False, "annotation": "Syntax error: Missing colon in function definition."},
            {"name": "Evan", "solution": "def sum_even(numbers):\n    count = 0\n    for num in numbers:\n        if num % 2 == 0:\n            count += 1  # Wrong: should add the number, not count it.\n    return count", "correct": False, "annotation": "Counts even numbers instead of summing their values."},
            {"name": "Fiona", "solution": "def sum_even(numbers):\n    total = 0\n    for num in numbers:\n        if num > 0 and num % 2 == 0:  # Faulty: Excludes negative even numbers.\n            total += num\n    return total", "correct": False, "annotation": "Only sums positive even numbers, ignoring negatives."},
            {"name": "George", "solution": "def sum_even(numbers):\n    return sum(numbers)  # No condition; adds every number.", "correct": False, "annotation": "Sums all numbers regardless of even/odd."},
            {"name": "Helen", "solution": "def sum_even(numbers):\n    even_numbers = []\n    for num in numbers:\n        if num % 2 == 0:\n            even_numbers.append(num)\n    result = 0\n    for even in even_numbers:\n        result += even\n    return result", "correct": True, "annotation": "Correct solution (verbose but clear)."},
            {"name": "Ian", "solution": "def sum_even(numbers):\n    if not numbers:\n        return 0\n    head = numbers[0]\n    tail = numbers[1:]\n    if head % 2 == 0:\n        return head + sum_even(tail)\n    else:\n        return sum_even(tail)", "correct": True, "annotation": "Correct recursive solution."},
            {"name": "Julia", "solution": "def sum_even(numbers):\n    total = 0\n    for num in numbers:\n        # This condition is intended to check evenness but is flawed.\n        if (num / 2) % 2 == 0:\n            total += num\n    return total", "correct": False, "annotation": "Faulty condition using division leads to wrong results."}
            ]
        print("Seeding data...")
        for s in students:
            student = Student(name=s["name"], solution=s["solution"], correct=s["correct"], annotation= s["annotation"])
            db.session.add(student)
        db.session.commit()  # Commit the changes to the database
        return "Data seeded!"

    return "Data already exists in the database."
    
@app.route("/query", methods=['GET', 'POST'])
def query():
    if not api_key:
        return jsonify({"error": "API key not found. Please check your .env file."}), 500
        
    try:
        # Handle both GET and POST requests
        if request.method == 'GET':
            prompt = "What is the capital of France?"  
        else:
            data = request.get_json()
            if not data or 'prompt' not in data:
                return jsonify({"error": "No prompt provided"}), 400
            
            prompt = data['prompt']
            
        response = query_gemini(prompt, api_key)
        
        if isinstance(response, dict) and 'error' in response:
            return jsonify(response), 500
            
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/upload_description', methods=['POST'])
def upload_pdf():
    if 'assignment_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    

    file = request.files['assignment_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
   
    app.config['UPLOAD_FOLDER'] = 'uploads'
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    
    # Process the saved PDF file
    pdf_data = pdf_to_json(file_path)

    if not pdf_data:
        return jsonify({'error': 'No text extracted from the PDF'}), 400
    
        # Combine all page text from the PDF into one large string for the description
    full_pdf_text = "\n".join([text for page, text in pdf_data.items()])
    
    assignment["description"] = full_pdf_text
    
    
    rubric = generate_rubric_based_on_description(full_pdf_text)

    # Update rubric with the generated values
    assignment["rubric"] = rubric
    
    return redirect("/grading_dashboard")

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

    # Find the student's solution
    student = Student.query.filter_by(name=student_name).first()
    if not student:
        return jsonify({"error": f"Student '{student_name}' not found."}), 404

    solution = student.solution
    test_cases = [
        {"input": "[]", "expected": 0},
        {"input": "[1, 3, 5]", "expected": 0},
        {"input": "[2, 4, 6]", "expected": 12},
        {"input": "[1, 2, 3, 4, 5, 6]", "expected": 12},
        {"input": "[-2, -3, 4]", "expected": 2},
        {"input": "[0, 1, 2, 3]", "expected": 2},
        {"input": "[10]", "expected": 10},
        {"input": "[7]", "expected": 0},
        {"input": "[1, -2, -4, 3, 0]", "expected": -6},
        {"input": "[100, 101, 102]", "expected": 202}
    ]

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

        for test_case in test_cases:
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
        results["failed"] = len(test_cases)
        results["details"] = [{"input": "N/A", "status": "Error", "error": str(e)}]

    return jsonify(results)

@app.route("/evaluate_student", methods=["POST"])
def evaluate_student():
    data = request.get_json()
    student_name = data.get("student_name")
    student = Student.query.filter_by(name=student_name).first()
    if not student:
        print(f"[evaluate_student] Student '{student_name}' not found.")
        return jsonify({"error": "Student not found."}), 404

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
    print("[evaluate_student] Prompt sent to Gemini:\n", prompt)
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

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
