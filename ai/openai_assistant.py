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
    # Remove bold (**text**)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Remove italic (*text*)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Remove underline (__text__)
    text = re.sub(r'__(.+?)__', r'\1', text)
    return text

def is_cybersecurity_question(user_message):
    """
    Classify if a question is about cybersecurity using a cheap model call.
    Returns True if cybersecurity-related, False otherwise.
    """
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
                        "or any other topic related to protecting business data and systems.\n\n"
                        "Answer only 'NO' for any other topic (e.g., general knowledge, history, "
                        "entertainment, cooking, personal advice, sports).\n\n"
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
        # Fail closed for safety – if the classifier fails, treat it as off-topic
        return False


def is_content_safe(user_message):
    """
    Check if the user message is safe using OpenAI's Moderation API.
    Returns True if safe, False if flagged.
    """
    try:
        response = client.moderations.create(input=user_message)
        return not response.results[0].flagged
    except Exception as e:
        print(f"Moderation error: {e}")
        # Fail closed for safety – if moderation fails, treat it as unsafe
        return False


def get_openai_response(user_message, risk_context=None):
    """
    Get a response from OpenAI's GPT-4o-mini model.
    Includes topic restriction and safety filtering.
    Falls back to rule-based assistant if the API fails.
    """
    # Step 1: Safety check (OpenAI Moderation API)
    if not is_content_safe(user_message):
        return (
            "I'm sorry, but I cannot respond to that request. "
            "I'm here to help with cybersecurity questions only."
        )

    # Step 2: Topic classification (Pre-flight filter)
    if not is_cybersecurity_question(user_message):
        return (
            "I'm a specialised cybersecurity advisor and can only answer questions "
            "about digital safety, data protection, and securing your business. "
            "I'm not able to help with that topic."
        )

    # Step 3: Main AI response (on-topic question)
    try:
        # Build the system prompt with topic restrictions
        system_prompt = (
            "You are CyberShield Advisor, a specialised cybersecurity expert for Australian small businesses. "
            "Your purpose is to provide plain-English, actionable advice on cybersecurity topics ONLY.\n\n"
            "RULES:\n"
            "1. STRICT TOPIC BOUNDARY: You must ONLY answer questions related to cybersecurity, "
            "digital safety, data protection, online privacy, and related Australian regulations "
            "(like the Privacy Act or ASD Essential Eight).\n"
            "2. If a user asks a question that is NOT about cybersecurity, you MUST politely decline "
            "to answer. Use a response like: 'I'm a specialised cybersecurity advisor and can only "
            "answer questions about digital safety and protecting your business.'\n"
            "3. TONE: Be friendly, supportive, and avoid technical jargon. Use plain English.\n"
            "4. Be practical: When relevant, provide actionable steps for small business owners.\n"
            "5. If you don't know the answer, say so honestly and suggest they consult a professional.\n"
            "6. Include appropriate disclaimers for legal or insurance advice."
        )

        # Add risk context if provided
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

        # Step 4: Clean the response (remove Markdown formatting)
        raw_response = response.choices[0].message.content
        return clean_response(raw_response)

    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Fallback to rule-based assistant
        try:
            from ai.assistant import answer_question
            return answer_question(user_message)
        except Exception:
            return (
                "I'm sorry, I'm having trouble connecting to my knowledge base right now. "
                "Please try again in a moment."
            )