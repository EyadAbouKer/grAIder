from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
from gemeniapi import query_gemini

load_dotenv()  # Load environment variables from .env file
api_key = os.getenv('GEMINI_API_KEY')

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/grading_dashboard")
def grading_dashboard():
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

    return render_template("grading_dashboard.html", assignment=assignment, test_cases=test_cases, students=students)

@app.route("/query", methods=['GET', 'POST'])
def query():
    try:
        # Handle both GET and POST requests
        if request.method == 'GET':
            prompt = "What is the capital of France?"  # Default prompt for GET requests
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

if __name__ == "__main__":
    app.run(debug=True)
