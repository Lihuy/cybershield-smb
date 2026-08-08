"""
OpenAI Assistant module for CyberShield SMB.
Handles AI-powered chat responses with topic restriction and safety filtering.
"""

import re
import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def clean_response(text):
    """Remove Markdown formatting characters (**, *, __, etc.) from the response."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    return text

def is_cybersecurity_question(user_message):
    """Classify if a question is about cybersecurity."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict classifier. Answer only 'YES' if the user's question is about "
                        "cybersecurity, digital safety, data protection, online privacy, hacking, phishing, "
                        "ransomware, malware, backups, passwords, MFA, firewalls, network security, "
                        "Australian cybersecurity regulations (Essential Eight, Privacy Act), "
                        "or recommendations about cybersecurity improvements.\n\n"
                        "Answer only 'NO' for any other topic (e.g., general knowledge, history, "
                        "entertainment, cooking, personal advice, sports).\n\n"
                        "If the user asks to explain or provide more details about a cybersecurity topic, "
                        "answer 'YES'.\n\n"
                        "Do not provide any other explanation."
                    )
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=5,
            temperature=0
        )
        classification = response.choices[0].message.content.strip().upper()
        return classification == "YES"
    except Exception as e:
        print(f"Classification error: {e}")
        return False

def is_content_safe(user_message):
    """Check if the user message is safe using OpenAI's Moderation API."""
    try:
        response = client.moderations.create(input=user_message)
        return not response.results[0].flagged
    except Exception as e:
        print(f"Moderation error: {e}")
        return False

def get_openai_response(user_message, risk_context=None):
    """
    Get a response from OpenAI's GPT-4o-mini model.
    Includes topic restriction and safety filtering.
    Falls back to rule-based assistant if the API fails.
    """
    # --- BYPASS FOR "ASK AI" FEATURE ---
    is_ask_ai = False
    if user_message.startswith('[ASK_AI]'):
        is_ask_ai = True
        user_message = user_message.replace('[ASK_AI]', '').strip()

    # Step 1: Safety check (skip for Ask AI)
    if not is_ask_ai:
        if not is_content_safe(user_message):
            return (
                "I'm sorry, but I cannot respond to that request. "
                "I'm here to help with cybersecurity questions only."
            )

    # Step 2: Topic classification (skip for Ask AI)
    if not is_ask_ai:
        if not is_cybersecurity_question(user_message):
            return (
                "I'm a specialised cybersecurity advisor and can only answer questions "
                "about digital safety, data protection, and securing your business. "
                "I'm not able to help with that topic."
            )

    # Step 3: Main AI response
    try:
        system_prompt = (
            "You are CyberShield Advisor, a specialised cybersecurity expert for Australian small businesses. "
            "Your purpose is to provide plain-English, actionable advice on cybersecurity topics.\n\n"
            "RULES:\n"
            "1. Be friendly, supportive, and avoid technical jargon. Use plain English.\n"
            "2. Be practical: When relevant, provide actionable steps for small business owners.\n"
            "3. If you don't know the answer, say so honestly and suggest they consult a professional.\n"
            "4. Keep responses concise and helpful."
        )

        if risk_context:
            system_prompt += f"\n\nUser's current risk profile: {risk_context}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )

        raw_response = response.choices[0].message.content
        return clean_response(raw_response)

    except Exception as e:
        print(f"OpenAI API error: {e}")
        try:
            from ai.assistant import answer_question
            return answer_question(user_message)
        except Exception:
            return (
                "I'm sorry, I'm having trouble connecting to my knowledge base right now. "
                "Please try again in a moment."
            )