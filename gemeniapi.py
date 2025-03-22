import os
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Any, Dict, Union

# load_dotenv()
# api_key = os.getenv('GEMINI_API_KEY')

def query_gemini(prompt: str, api_key: str) -> Union[str, Dict[str, str]]:
    """
    Query Gemini API with a prompt and return the structured response.
    
    Args:
        prompt (str): The input prompt to send to Gemini
        api_key (str): Your Google API key
    
    Returns:
        Union[str, Dict[str, str]]: The response from Gemini or error information
    """
    # Configure the API
    genai.configure(api_key=api_key)
    
    # Use Gemini 2.0 Flash-Lite model
    model = genai.GenerativeModel('gemini-2.0-flash-lite')
    
    try:
        # Generate response
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            return {"error": "Empty response from Gemini API"}
            
        # Return the structured response
        return response.text
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error querying Gemini API: {error_msg}")
        return {"error": f"Gemini API Error: {error_msg}"}

def studentEvaluator(students: list, assignment: dict, api_key: str) -> list:
    """
    Evaluate multiple student solutions using Gemini API.
    
    Args:
        students (list): List of student dictionaries containing name and solution
        assignment (dict): Assignment details including title, description and rubric
        api_key (str): API key for Gemini
    
    Returns:
        list: List of dictionaries containing evaluation results
    """
    all_results = []
    
    for student in students:
        # Construct prompt for Gemini with specific rubric categories
        prompt = f"""
        Assignment: {assignment['title']}
        Description: {assignment['description']}
        
        Student Name: {student['name']}
        Student Solution:
        {student['solution']}
        
        Please evaluate this solution based on the following rubric:
        - Correctness (50 points): Does the solution correctly sum even numbers?
        - Edge Cases (20 points): Handles empty lists, negative numbers, etc.
        - Code Quality (20 points): Code clarity, efficiency, and style
        - Error Handling (10 points): Proper handling of invalid inputs
        
        Format your response exactly as:
        SCORE: [total percentage 0-100]
        CORRECTNESS: [score /50]
        EDGE_CASES: [score /20]
        CODE_QUALITY: [score /20]
        ERROR_HANDLING: [score /10]
        EVALUATION: [detailed explanation of scoring]
        """
        
        try:
            # Get evaluation from Gemini
            response = query_gemini(prompt, api_key)
            
            if isinstance(response, dict) and 'error' in response:
                all_results.append({'error': response['error']})
                continue
                
            # Parse response
            lines = response.strip().split('\n')
            scores = {}
            evaluation = []
            
            for line in lines:
                if line.startswith('SCORE:'):
                    scores['total'] = float(line.replace('SCORE:', '').strip().rstrip('%'))
                elif line.startswith('CORRECTNESS:'):
                    # Parse X/50 format
                    score_text = line.replace('CORRECTNESS:', '').strip()
                    scores['correctness'] = float(score_text.split('/')[0])
                elif line.startswith('EDGE_CASES:'):
                    score_text = line.replace('EDGE_CASES:', '').strip()
                    scores['edge_cases'] = float(score_text.split('/')[0])
                elif line.startswith('CODE_QUALITY:'):
                    score_text = line.replace('CODE_QUALITY:', '').strip()
                    scores['code_quality'] = float(score_text.split('/')[0])
                elif line.startswith('ERROR_HANDLING:'):
                    score_text = line.replace('ERROR_HANDLING:', '').strip()
                    scores['error_handling'] = float(score_text.split('/')[0])
                elif line.startswith('EVALUATION:'):
                    evaluation = [line.replace('EVALUATION:', '').strip()]
                elif evaluation:
                    evaluation.append(line.strip())
                    
            student['evaluation'] = evaluation
            student['scores'] = scores
            
            all_results.append({
                # 'name': student['name'],
                # 'solution': student['solution'],
                'evaluation': '\n'.join(evaluation),
                'scores': scores
            })
            
        except Exception as e:
            all_results.append({'error': f'Evaluation failed for {student["name"]}: {str(e)}'})
    
    return all_results