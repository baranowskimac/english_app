import dash
from dash import html, dcc, Output, Input, State
import dash_bootstrap_components as dbc
from newspaper import Article
from openai import OpenAI, RateLimitError
import httpx
import time
import os
from openai import OpenAI
import httpx
import time
from openai import RateLimitError
import time
from dotenv import load_dotenv
import os
import re


# Load environment variables from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI client
client = OpenAI(
    api_key=api_key,
    http_client=httpx.Client(verify=False)
)

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

def extract_article(url):
    article = Article(url)
    article.download()
    article.parse()
    article.nlp()
    return {
        "title": article.title,
        "text": article.text,
        "keywords": article.keywords,
        "url": url
    }

def safe_api_call(messages, model="gpt-4-turbo", max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=2000
            )
        except RateLimitError:
            time.sleep(10)
        except Exception as e:
            return f"Error: {e}"
    return "Failed after multiple retries"

def highlight_keywords(text, keywords):
    for kw in sorted(keywords, key=len, reverse=True):  # longest first
        pattern = re.compile(rf"(?<!\w)({re.escape(kw)})(?!\w)", re.IGNORECASE)
        text = pattern.sub(r"<mark>\1</mark>", text)
    return text

app.layout = dbc.Container([
    html.H2("📰 Article Rewriter using GPT-4"),
    dbc.Input(id='url-1', placeholder='Enter URL to first article', type='text', className="mb-2"),
    dbc.Input(id='url-2', placeholder='Enter URL to second article', type='text', className="mb-2"),
    dbc.Textarea(id='keywords', placeholder='Optional: Enter keywords, comma-separated', className="mb-2"),
    dbc.Button("Rewrite Article", id='run-button', color="primary", className="mb-3"),
    
    dbc.Spinner(html.Div(id='output', style={'whiteSpace': 'pre-line'}), size="lg", color="primary", fullscreen=False),
], fluid=True)



@app.callback(
    Output('output', 'children'),
    Input('run-button', 'n_clicks'),
    State('url-1', 'value'),
    State('url-2', 'value'),
    State('keywords', 'value'),
    prevent_initial_call=True
)
def process_articles(n, url1, url2, keywords_input):
    try:
        article1 = extract_article(url1)
        article2 = extract_article(url2)
    except Exception as e:
        return f"❌ Error downloading articles: {e}"

    difficult_words = [k.strip() for k in keywords_input.split(',')] if keywords_input else article1["keywords"]

    prompt = f"""
Rewrite the following article using the words: {', '.join(difficult_words)}.
Keep the original meaning and context of the article.
Article:
{article2['text']}
"""

    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    response = safe_api_call(messages)

    if isinstance(response, str):
        return response

    rewritten_text = response.choices[0].message.content

    # Format the full output nicely
    return html.Div([
        html.H4("📘 First Article"),
        html.P(f"🔗 Title: {article1['title']}"),
        html.P(f"🗝 Keywords: {', '.join(article1['keywords'])}"),
        html.P(f"📝 Content:\n{article1['text'][:1500]}{'...' if len(article1['text']) > 1500 else ''}"),

        html.Hr(),

        html.H4("📙 Second Article"),
        html.P(f"🔗 Title: {article2['title']}"),
        html.P(f"🗝 Keywords: {', '.join(article2['keywords'])}"),
        html.P(f"📝 Content:\n{article2['text'][:1500]}{'...' if len(article2['text']) > 1500 else ''}"),

        html.Hr(),

        html.H4("✍️ Rewritten Article"),
        html.Div(dcc.Markdown(highlight_keywords(rewritten_text, difficult_words), dangerously_allow_html=True)),

        html.Hr(),

        html.H4("📌 Keywords Used in Rewrite"),
        html.P(', '.join(difficult_words))
    ])

if __name__ == '__main__':
    app.run(debug=True)
