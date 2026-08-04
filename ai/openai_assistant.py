import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_openai_response(user_message, risk_context=None):
    """
    Get a response from OpenAI's GPT-4o-mini model.
    Falls back to rule-based assistant if API fails.
    """
    try:
        # Build system prompt
        system_prompt = """You are CyberShield Advisor, a friendly cybersecurity expert for Australian small businesses.
        Provide plain-English, actionable advice. Be supportive and avoid technical jargon.
        """
        if risk_context:
            system_prompt += f"\n\nUser's risk profile: {risk_context}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Fallback to rule-based assistant
        from ai.assistant import get_response
        return get_response(user_message)