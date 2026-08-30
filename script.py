import json
import random
import os
import re
from datetime import datetime
import feedparser
import markdown

RSS_FEEDS = [
    "https://www.trthaber.com/sondakika_articles.rss",
    "https://www.aa.com.tr/tr/rss/default?cat=guncel",
    "https://feeds.bbci.co.uk/turkce/rss.xml"
]

PAGES_DIR = "pages"
SITE_DIR = "site"
MD_TEMPLATE_FILE = "templates/news_template.md"
HTML_TEMPLATE_FILE = "templates/page_template.html"
INDEX_JSON = "news_list.json"

def ensure_nojekyll():
    """GitHub Pages'in Jekyll derleyicisini devre dışı bırakır."""
    if not os.path.exists(".nojekyll"):
        open(".nojekyll", "w").close()

def slugify(text):
    tr_map = {'ç': 'c', 'Ç': 'c', 'ğ': 'g', 'Ğ': 'g', 'ı': 'i', 'İ': 'i', 
              'ö': 'o', 'Ö': 'o', 'ş': 's', 'Ş': 's', 'ü': 'u', 'Ü': 'u'}
    for search, replace in tr_map.items():
        text = text.replace(search, replace)
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text[:60]

def build_html_from_md(md_content, title):
    body_md = re.sub(r'---[\s\S]*?---', '', md_content).strip()
    html_body = markdown.markdown(body_md)

    with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        html_template = f.read()

    return html_template.replace("{{TITLE}}", title).replace("{{CONTENT}}", html_body)

def generate_index_html(news_list):
    items_html = ""
    for item in news_list:
        items_html += f'''
        <div class="card" style="margin-bottom: 15px; background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155;">
            <h2 style="margin: 0 0 10px 0; font-size: 1.2rem;"><a href="site/{item['slug']}.html" style="color: #38bdf8; text-decoration: none;">{item['title']}</a></h2>
            <div style="font-size: 0.85rem; color: #94a3b8;">Kaynak: {item['source']} | {item['date']}</div>
        </div>
        '''

    full_index = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Otomatik Haber Portalı</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0f172a; color: #f8fafc; line-height: 1.6; }}
        h1 {{ border-bottom: 2px solid #334155; padding-bottom: 10px; color: #f1f5f9; }}
    </style>
</head>
<body>
    <h1>Son Haberler</h1>
    {items_html}
</body>
</html>'''

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_index)

def fetch_and_build():
    ensure_nojekyll()
    os.makedirs(PAGES_DIR, exist_ok=True)
    os.makedirs(SITE_DIR, exist_ok=True)

    news_list = []
    if os.path.exists(INDEX_JSON):
        with open(INDEX_JSON, "r", encoding="utf-8") as f:
            try: news_list = json.load(f)
            except: news_list = []

    existing_links = {item.get("link") for item in news_list}

    feed = feedparser.parse(random.choice(RSS_FEEDS))
    if not feed.entries: return

    new_entries = [e for e in feed.entries if e.link not in existing_links]
    if not new_entries: return

    selected = random.choice(new_entries)
    title = selected.title
    link = selected.link
    summary = re.sub(r'<[^<]+?>', '', getattr(selected, "summary", getattr(selected, "description", "Açıklama yok.")))
    source = feed.feed.get("title", "Haber Kaynağı")
    pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    slug = f"{datetime.now().strftime('%Y-%m-%d')}-{slugify(title)}"

    with open(MD_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        md_template = f.read()

    md_content = md_template.format(
        title=title.replace('"', '\\"'),
        date=pub_date,
        source=source,
        link=link,
        slug=slug,
        summary=summary.strip()
    )
    
    md_path = os.path.join(PAGES_DIR, f"{slug}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    html_content = build_html_from_md(md_content, title)
    html_path = os.path.join(SITE_DIR, f"{slug}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    news_list.insert(0, {
        "title": title,
        "slug": slug,
        "link": link,
        "source": source,
        "date": pub_date
    })
    news_list = news_list[:100]

    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    generate_index_html(news_list)
    print(f"Başarıyla eklendi: {slug}")

if __name__ == "__main__":
    fetch_and_build()
    
