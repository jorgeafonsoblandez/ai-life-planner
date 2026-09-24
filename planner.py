import os
import sys
import json
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MEMORY_FILE = "memory.json"

def load_config():
    """Loads the user's JSON configuration."""
    if os.path.exists("config.json"):
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    elif os.path.exists("config.example.json"):
        print("⚠️ config.json not found! Falling back to config.example.json...")
        with open("config.example.json", "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print("❌ No configuration files found!")
        sys.exit(1)

def load_memory():
    """Loads the memory state to prevent duplicate alerts."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen_reddit_posts": []}

def save_memory(memory):
    """Saves the memory state."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

def fetch_weather(lat, lon):
    """Fetches a 7-day weather forecast from Open-Meteo (Free, no API key)."""
    print("🌤️ Fetching weather data...")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️ Failed to fetch weather: {e}")
        return None

def fetch_reddit(subreddits, memory):
    """Fetches top posts from local subreddits and filters out ones we've already seen."""
    print("📱 Fetching local community data...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    new_posts = []
    seen_posts = set(memory.get("seen_reddit_posts", []))
    
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/top.json?t=week&limit=15"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for child in data.get("data", {}).get("children", []):
                    post = child["data"]
                    post_id = post["id"]
                    
                    if post_id not in seen_posts:
                        new_posts.append({
                            "title": post["title"],
                            "text": post.get("selftext", "")[:500], # Keep it concise
                            "score": post["score"],
                            "url": f"https://reddit.com{post['permalink']}"
                        })
                        seen_posts.add(post_id)
        except Exception as e:
            print(f"⚠️ Failed to fetch r/{sub}: {e}")
            
    memory["seen_reddit_posts"] = list(seen_posts)
    return new_posts

def send_telegram(message):
    """Sends the finalized plan to the user via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials missing. Printing output to console:\n")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    
    if response.status_code == 400 and "parse entities" in response.text:
        print("⚠️ AI generated broken HTML tags. Retrying in plain text...")
        payload.pop("parse_mode")
        response = requests.post(url, json=payload)
        
    if response.status_code != 200:
        print(f"❌ Failed to send Telegram message: {response.text}")
        return False
    else:
        print("📨 Plan successfully sent to Telegram!")
        return True

def generate_plan(config, weather, reddit_posts):
    """Uses Gemini to synthesize the data into a personalized plan."""
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY is missing!")
        sys.exit(1)
        
    print("🧠 Synthesizing Life Plan with AI...")
    
    # 1. Build the Time Context
    now = datetime.now()
    date_context = f"Today is {now.strftime('%A, %B %d, %Y')}."
    
    # 2. Build the Prompt
    prompt = f"""
{date_context}

You are an elite, highly personalized AI Life Planner for {config['user']['name']}.
Your job is to act as their proactive assistant, looking at their schedule, their constraints, the weather, and what is happening locally, and providing them with an actionable plan.

=== USER PROFILE ===
Location: {config.get('user', {}).get('location', 'Unknown')}
Free Days: {', '.join(config.get('schedule', {}).get('free_days', []))}
Hobbies: {', '.join(config.get('interests', {}).get('outdoors', []) + config.get('interests', {}).get('social', []))}
Quests/Goals: {', '.join(config.get('quests', []))}
Logistics/Constraints: {json.dumps(config.get('logistics', {}))}

=== WEATHER FORECAST ===
{json.dumps(weather['daily'] if weather else 'Weather data unavailable.')}

=== NEW COMMUNITY KNOWLEDGE (Events/Deals/News) ===
{json.dumps(reddit_posts) if reddit_posts else 'No new local updates today.'}

=== INSTRUCTIONS ===
1. Analyze the weather for their free days. If it's sunny, suggest an outdoor hobby. If raining, suggest indoor. Mention transportation constraints!
2. For their 'Quests', do NOT just repeat the goals back to them. Suggest highly specific, actionable steps, real websites, actual companies, or creative strategies they can use this weekend to achieve them.
3. Review the Community Knowledge. If there are any posts relevant to their 'Quests' or 'Hobbies', alert them!
4. If the 'NEW COMMUNITY KNOWLEDGE' data is NOT empty, include a 'News Digest' section highlighting 2-3 SPECIFIC, real posts. If the data is empty, completely omit the News Digest section (do not even mention it).
5. IMPORTANT: Telegram's HTML parser is incredibly strict. ONLY use <b> and <i> tags. Do NOT use <ul>, <li>, <br>, <p>, or headers. Use standard text bullets (-) for lists. CRITICAL: Do NOT use the `<` or `>` math symbols anywhere in your text (e.g., write 'under $100' instead of '<$100'), as it crashes the HTML parser.
6. LENGTH: {config.get('preferences', {}).get('message_length', 'Keep the total message under 3000 characters.')}
7. Adopt this exact persona/tone: "{config.get('preferences', {}).get('tone', 'Friendly and concise.')}"
8. Write the response in this language: "{config.get('preferences', {}).get('language', 'English')}"
"""

    max_retries = 5
    for attempt in range(max_retries):
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7
                )
            )
            return response.text
        except Exception as e:
            print(f"⚠️ AI Generation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("⏳ Waiting 60 seconds before retrying due to high demand...")
                time.sleep(60)
            else:
                print("❌ Max retries reached. AI is currently unavailable.")
                return None

def main():
    print("🚀 Starting AI Life Planner...")
    
    config = load_config()
    memory = load_memory()
    
    # Gather Context
    weather = fetch_weather(config["user"]["coordinates"]["lat"], config["user"]["coordinates"]["lon"])
    reddit_posts = fetch_reddit(config["data_sources"]["subreddits"], memory)
    
    # Synthesize
    plan_html = generate_plan(config, weather, reddit_posts)
    
    if plan_html:
        # Deliver
        success = send_telegram(plan_html)
        # Only save memory if generation AND delivery were successful 
        if success:
            save_memory(memory)
            print("✅ Planner run complete!")
        else:
            print("⚠️ Memory not saved due to delivery failure.")
            sys.exit(1)
    else:
        print("❌ Could not generate plan. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
