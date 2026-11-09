"""
langchain_config.py
-------------------
  * Initialize the LLM (free Groq / Gemini, or paid OpenAI)
  * Prompt template + LLMChain-style chain
  * NewsAPI integration (get_news_articles, summarize_articles, get_summary)
"""
import os

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from newsapi import NewsApiClient

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

MODEL_NAME = "unknown"


def _build_llm():
    global MODEL_NAME
    if PROVIDER == "groq":
        from langchain_groq import ChatGroq
        MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        return ChatGroq(
            model=MODEL_NAME,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
        )
    if PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        return ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.2,
        )
    if PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return ChatOpenAI(
            model=MODEL_NAME,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.2,
        )
    raise ValueError("LLM_PROVIDER must be groq, gemini or openai")


openai = _build_llm()


class LLMChain:
    def __init__(self, prompt, llm):
        self.chain = prompt | llm

    def run(self, inputs: dict) -> str:
        result = self.chain.invoke(inputs)
        return result.content if hasattr(result, "content") else str(result)


# ---------------------------------------------------------------------------
# NewsAPI integration
# ---------------------------------------------------------------------------
newsapi = NewsApiClient(api_key=os.getenv("NEWSAPI_KEY"))


def get_news_articles(query, page_size=10, sort_by="relevancy",from_date=None, to_date=None):
    articles = newsapi.get_everything(
        q=query,
        language="en",
        sort_by=sort_by,
        page_size=page_size,
        from_param=from_date,
        to=to_date,
    )
    return articles["articles"]


def summarize_articles(articles):
    summaries = []
    for i, article in enumerate(articles, start=1):
        if article.get("description"):  # Skip articles with an empty description
            source = (article.get("source") or {}).get("name", "Unknown")
            title = article.get("title") or ""
            summaries.append(f"{i}. [{source}] {title}: {article['description']}")
    return "\n".join(summaries)


def get_summary(query, **kwargs):
    articles = get_news_articles(query, **kwargs)
    summary = summarize_articles(articles)
    return summary


template = """
You are an AI assistant helping an equity research analyst. Given
the following query and the provided news article summaries, provide
an overall summary.

Write the answer in Markdown using exactly this structure:

### Overview
2-3 sentences summarizing the overall news.

### Key Takeaways
- 4 to 6 short bullet points with the most important facts.

### Sentiment
**Bullish**, **Bearish** or **Neutral** (pick exactly one) followed by a one-line reason.

### Risks & Things to Watch
- 2 to 4 short bullet points.

Only use the information in the summaries. Do not invent facts or numbers.

Query: {query}
Summaries:
{summaries}
"""
prompt = PromptTemplate(template=template, input_variables=["query", "summaries"])
llm_chain = LLMChain(prompt=prompt, llm=openai)
