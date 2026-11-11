# 📰 Equity Research News Tool

An AI-powered news research assistant for equity research analysts. Search any company, index or topic, and the app fetches the latest news articles and turns them into a structured summary with **key takeaways, sentiment and risks** in seconds.

Built with **Streamlit**, **LangChain**, **NewsAPI** and a choice of LLM providers (**Groq**, **Google Gemini** or **OpenAI**).

---

## ✨ Features

- 🔎 **Chat-style news search**: type a company, index or topic (e.g. *"Tesla Q3 earnings"*) and get an instant summary.
- 🧠 **AI summaries in a fixed format**: Overview, Key Takeaways, Sentiment (Bullish / Bearish / Neutral) and Risks & Things to Watch.
- 🚫 **Grounded answers**: the prompt tells the model to use only the fetched article summaries and not to invent facts or numbers.
- 🔀 **Switchable LLM provider**: Groq (free, default), Gemini or OpenAI, selected from the `.env` file.
- 🔐 **User accounts**: sign up / log in with username and password (salted PBKDF2-SHA256 hashing, 5 failed attempts lock the account for 5 minutes, optional invite code).
- 💬 **Saved chat history**: every user gets their own chats, with "Start new chat" and "Clear all history".
- 📥 **Export**: download any summary as `.md` or `.txt`, including the list of sources.
- ⚡ **Caching**: the same query is not re-fetched or re-summarized for 1 hour, which protects the free NewsAPI limit (100 requests/day).
- 🎨 **Clean UI** with a custom Streamlit theme and friendly error messages (rate limits, invalid keys, wrong model name).

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM orchestration | LangChain (`langchain-core`, `langchain-groq`) |
| LLM providers | Groq (default), Google Gemini, OpenAI |
| News data | NewsAPI (`newsapi-python`) |
| Auth | Python standard library (`hashlib`, `hmac`, `secrets`) |
| Config | `python-dotenv` |
| Language | Python 3.9+ |

---

## 📁 Project Structure

```
.
├── app.py                 # Streamlit app: UI, login/signup, search flow, chat history
├── auth.py                # Authentication: password hashing, sessions, lockout
├── langchain_config.py    # LLM setup, prompt template, NewsAPI helpers
├── config.toml            # Streamlit theme and settings
├── env.example            # Template for environment variables
├── requirements.txt       # Python dependencies
├── Equity_Research_News_Presetation.pptx   # Project presentation
├── News Research LLM Model Recording.mp4   # Demo recording
└── LICENSE
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/vm17-lab/Project_9_NHIS_-News-Research-Tool.git
cd Project_9_NHIS_-News-Research-Tool
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> Using Gemini or OpenAI? Also install `langchain-google-genai` or `langchain-openai`.

### 4. Set up your API keys

Copy the example file and fill in your own keys:

```bash
# Windows
copy env.example .env
# macOS / Linux
cp env.example .env
```

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-key
GROQ_MODEL=openai/gpt-oss-120b
NEWSAPI_KEY=your-newsapi-key

# Optional: only people with this code can create an account
# SIGNUP_CODE=your-invite-code
```

| Key | Where to get it |
|---|---|
| `GROQ_API_KEY` (free) | https://console.groq.com/keys |
| `NEWSAPI_KEY` (free) | https://newsapi.org/register |
| `GOOGLE_API_KEY` (optional) | Google AI Studio |
| `OPENAI_API_KEY` (optional) | https://platform.openai.com/api-keys |

> ⚠️ Never commit your real `.env` file.

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501**, create an account and start searching.

> 💡 Streamlit reads its theme from `config.toml`. the provided `config.toml` to apply the custom look.

---

## 🧭 How It Works

1. **Search**: the user enters a company, index or topic.
2. **Fetch**: `NewsAPI` returns the 10 most relevant English articles.
3. **Prepare**: article titles, sources and descriptions are combined into a compact list.
4. **Summarize**: a LangChain prompt sends that list to the chosen LLM (temperature 0.2).
5. **Display**: the structured summary appears in the chat, and can be downloaded as `.md` / `.txt` with sources.

---

## ⚙️ Configuration

| Setting | Location | Default |
|---|---|---|
| LLM provider | `LLM_PROVIDER` in `.env` | `groq` |
| Model name | `GROQ_MODEL` / `GEMINI_MODEL` / `OPENAI_MODEL` | `openai/gpt-oss-120b` |
| Articles per search | `NUM_ARTICLES` in `app.py` | `10` |
| Sort order | `SORT_BY` in `app.py` | `relevancy` |
| Cache duration | `ttl` in `app.py` | 1 hour |

---

## 🎬 Demo

- 📊 Presentation: `Equity_Research_News_Presetation.pptx`
- 🎥 Video walkthrough: `News Research LLM Model Recording.mp4`

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
