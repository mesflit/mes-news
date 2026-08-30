import json
import random
import os
import re
from datetime import datetime
import feedparser
import markdown

RSS_FEEDS = [
    "https://www.merlininkazani.com/feed",
    "https://onedio.com/rss",
    "https://feeds.bbci.co.uk/turkce/rss.xml",
    "https://www.ntv.com.tr/gundem.rss"
]

PAGES_DIR = "pages"
SITE_DIR = "site"
MD_TEMPLATE_FILE = "templates/news_template.md"
HTML_TEMPLATE_FILE = "templates/page_template.html"
INDEX_JSON = "news_list.json"
FETCH_COUNT = 5  # Her çalıştığında kaç yeni haber çekilsin

def ensure_nojekyll():
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

def extract_full_content(entry):
    """RSS ögesinden en detaylı haber metnini ayıklar."""
    content = ""
    if hasattr(entry, 'content') and len(entry.content) > 0:
        content = entry.content[0].value
    elif hasattr(entry, 'summary_detail') and entry.summary_detail.value:
        content = entry.summary_detail.value
    elif hasattr(entry, 'summary'):
        content = entry.summary
    elif hasattr(entry, 'description'):
        content = entry.description

    clean_text = re.sub(r'<[^<]+?>', '', content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text if clean_text else "Haber içeriği bulunamadı."

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
        <div class="card news-card" data-title="{item['title'].lower()}" data-source="{item['source'].lower()}" style="margin-bottom: 15px; background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155;">
            <h2 style="margin: 0 0 10px 0; font-size: 1.2rem;"><a href="site/{item['slug']}.html" style="color: #38bdf8; text-decoration: none;">{item['title']}</a></h2>
            <div style="font-size: 0.85rem; color: #94a3b8;">Kaynak: {item['source']} | {item['date']}</div>
        </div>
        '''

    full_index = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mes-News | Otomatik Haber Portalı</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0f172a; color: #f8fafc; line-height: 1.6; }}
        header {{ border-bottom: 2px solid #334155; padding-bottom: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }}
        h1 {{ margin: 0; color: #38bdf8; font-size: 2rem; }}
        .subtitle {{ color: #94a3b8; font-size: 0.9rem; margin-top: 5px; }}
        .search-container {{ margin-bottom: 25px; }}
        .search-input {{ width: 100%; padding: 12px 16px; background: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #f8fafc; font-size: 1rem; box-sizing: border-box; outline: none; transition: border-color 0.2s; }}
        .search-input:focus {{ border-color: #38bdf8; }}
        .no-results {{ display: none; text-align: center; color: #94a3b8; padding: 30px; font-style: italic; }}
    </style>
</head>
<body>
    <header>
        <div>
            <h1>Mes-News</h1>
            <div class="subtitle">Anlık Otomatik Haber Akışı</div>
        </div>
    </header>

    <div class="search-container">
        <input type="text" id="searchInput" class="search-input" placeholder="Haberlerde veya kaynaklarda ara..." onkeyup="filterNews()">
    </div>

    <main id="newsContainer">
        {items_html}
        <div id="noResults" class="no-results">Aramanızla eşleşen haber bulunamadı.</div>
    </main>

    <script>
        function filterNews() {{
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const cards = document.querySelectorAll('.news-card');
            let visibleCount = 0;

            cards.forEach(card => {{
                const title = card.getAttribute('data-title');
                const source = card.getAttribute('data-source');

                if (title.includes(query) || source.includes(query)) {{
                    card.style.display = 'block';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});

            const noResults = document.getElementById('noResults');
            if (visibleCount === 0 && cards.length > 0) {{
                noResults.style.display = 'block';
            }} else {{
                noResults.style.display = 'none';
            }}
        }}
    </script>
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
    existing_titles = {item.get("title") for item in news_list}

    all_candidates = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        source_name = feed.feed.get("title", "Haber Kaynağı")
        for entry in feed.entries:
            if entry.link not in existing_links and entry.title not in existing_titles:
                all_candidates.append((entry, source_name))

    if not all_candidates:
        print("Yeni haber bulunamadı.")
        generate_index_html(news_list)
        return

    random.shuffle(all_candidates)
    selected_items = all_candidates[:FETCH_COUNT]

    with open(MD_TEMPLATE_FILE, "r", encoding="utf-8") as f:
        md_template = f.read()

    added_count = 0
    for selected, source in selected_items:
        title = selected.title
        link = selected.link
        full_content = extract_full_content(selected)
        pub_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        slug = f"{datetime.now().strftime('%Y-%m-%d')}-{slugify(title)}"

        md_content = md_template.format(
            title=title.replace('{', '').replace('}', ''),
            date=pub_date,
            source=source,
            link=link,
            slug=slug,
            summary=full_content
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
        existing_links.add(link)
        existing_titles.add(title)
        added_count += 1

    news_list = news_list[:200]

    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)

    generate_index_html(news_list)
    print(f"Toplam {added_count} yeni haber Mes-News portalına eklendi!")

if __name__ == "__main__":
    fetch_and_build()
    
