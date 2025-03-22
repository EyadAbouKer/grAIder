import google.generativeai as genai
from typing import Any, Dict, Union

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

