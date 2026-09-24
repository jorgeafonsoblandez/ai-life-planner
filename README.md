# 🧠 AI Life Planner

Your own personal, proactive AI life planner. 
Instead of waiting for you to ask it questions, this Planner wakes up on a schedule, looks at your life configuration (hobbies, schedule, goals), scans the local weather and community discussions, and builds a customized weekend plan for you.

## How it works

The Planner is built around a single `config.json` file where you define your "Life Profile":
- **Who and Where:** Your location (for weather).
- **Logistics:** Do you have a car? What is your budget? 
- **Quests:** What are you currently looking for? (e.g., "Buying a used couch", "Finding a tech job").
- **Preferences:** What language, tone, and length should the AI use? (e.g., "Spanish, sarcastic, max 3 bullet points").

### The Data Engine
When the script runs, it fetches:
1. **Weather:** A free, hyper-local forecast for your coordinates via Open-Meteo.
2. **Community News:** Top posts from your configured Subreddits (e.g., `r/auckland` for local events, or `r/technology` for your hobbies) to find real, high-signal news and deals.
3. **Memory State:** It remembers what it has already told you, so it never bothers you with the same Reddit post or deal twice!
4. **Time Context:** It injects the current date into the AI prompt so it knows what "tomorrow" means.

It feeds all of this to **Gemini 2.5 Flash**, which synthesizes the ultimate plan and pings it to your Telegram.

---

## 🚀 How to Run It (Two Options)

### 💻 Option 1: Run Locally (Best for Testing)
Run the planner directly from your computer terminal.

1. Duplicate `.env.example` and rename it to `.env`.
2. Open `.env` and paste your **Gemini API Key** and **Telegram Bot credentials**.
3. Duplicate `config.example.json` and rename it to `config.json`.
4. Edit `config.json` to match your personal life, exact location, and interests.
5. Install the requirements and run the app:
   ```bash
   pip install -r requirements.txt
   python planner.py
   ```

### ☁️ Option 2: Run in the Cloud (Fully Automated)
Run the planner serverlessly on GitHub so it automatically pings your phone every Thursday afternoon!

1. Fork or push this repository to your own GitHub account.
2. Go to your repository's **Settings -> Secrets and variables -> Actions**.
3. Add these secrets exactly as they appear:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GEMINI_API_KEY`
   - `CONFIG_JSON` *(Optional but recommended: Paste the entire contents of your personal `config.json` file here so the cloud version uses your real data. If you skip this, it will run using the generic `config.example.json` data!)*
4. The Planner will now automatically run every Thursday! 
   - *Want a plan right now?* Go to the **Actions** tab, click **AI Life Planner**, and click the **Run workflow** button to trigger it manually.
