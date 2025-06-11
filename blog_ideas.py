import streamlit as st
import json
import time
import requests
from bs4 import BeautifulSoup
import re
import yake
import google.generativeai as genai

# ---------- CONFIG ----------
st.set_page_config(page_title="Smart Blog Idea Generator", layout="centered")
st.title("💡 AI Blog Idea Generator for Brands")

# ---------- LOAD BRAND DATA ----------
with open("brand_data.json", "r") as f:
    brand_data = json.load(f)
brand_dict = {brand["brand_name"]: brand for brand in brand_data}
brand_names = list(brand_dict.keys())

# ---------- SELECT BRAND ----------
selected_brand = st.selectbox("🔍 Select a Brand", brand_names)
brand_info = brand_dict[selected_brand]
brand_desc = brand_info.get("description", "")
brand_example_blogs = brand_info.get("example_blogs", "")

st.subheader("📌 Brand Overview")
with st.expander("Show Brand Info"):
    for key, value in brand_info.items():
        st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")

# ---------- WEBSITE CRAWLING ----------
def get_internal_links(base_url, max_pages=5):
    visited = set()
    to_visit = [base_url]
    allowed_keywords = ["product", "shop", "about", "collection", "category", "wedding", "jewellery", "ethnic", "clothing"]
    disallowed_keywords = ["cart", "account", "login", "wishlist", "checkout"]

    internal_links = []
    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited or any(bad in url for bad in disallowed_keywords):
            continue
        visited.add(url)
        try:
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            if any(word in url for word in allowed_keywords):
                internal_links.append(url)
            for a_tag in soup.find_all("a", href=True):
                href = a_tag['href']
                if href.startswith("/"):
                    href = base_url.rstrip("/") + href
                if href.startswith(base_url) and href not in visited:
                    to_visit.append(href)
        except:
            continue
    return internal_links

def extract_text_from_urls(urls):
    text = ""
    for url in urls:
        try:
            r = requests.get(url, timeout=5)
            soup = BeautifulSoup(r.text, "html.parser")
            for script in soup(["script", "style"]): script.extract()
            text += " " + soup.get_text(separator=' ')
        except:
            continue
    return re.sub(r'\s+', ' ', text)

# ---------- YAKE SETUP ----------
def get_keywords(text, n=15):
    kw_extractor = yake.KeywordExtractor(top=n, stopwords=None)
    keywords = kw_extractor.extract_keywords(text)
    return [kw[0] for kw in keywords]

# ---------- GEMINI SETUP ----------
GEMINI_API_KEY = "GEMINI_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash-latest")

# ---------- GENERATE BLOG IDEAS ----------
if st.button("🧠 Generate Blog Ideas"):
    with st.spinner("Crawling website and crafting unique blog ideas..."):
        website_url = brand_info.get("website", "")
        if not website_url:
            st.error("❌ Website URL not found.")
        else:
            urls = get_internal_links(website_url)
            text_data = extract_text_from_urls(urls)
            keywords = get_keywords(text_data)

            context_snippet = f"""
Brand Description:
{brand_desc}

Example Blogs:
{brand_example_blogs}

Extracted Keywords from website: {", ".join(keywords)}
"""

            blog_idea_prompt = f"""
You are a senior content strategist helping a premium brand come up with **original and creative blog ideas**.

{context_snippet}

Now, based on the above, generate **5 fresh, unique, and engaging blog titles** that:
- Use non-branded keywords only (no brand name)
- Reflect real customer intent (how-to guides, styling tips, emotional connections, etc.)
- Are NOT generic or repeated — avoid clichés
- Allow for natural internal product linking on a website (e.g., "explore our latest collection")
- Match the tone and style of high-end fashion or lifestyle blogs

Ensure every title is blog-ready — catchy, crisp, and impactful.
"""

            try:
                response = model.generate_content(blog_idea_prompt)
                blog_ideas = response.text.strip()
            except Exception as e:
                blog_ideas = f"❌ Error generating blog ideas: {e}"

            st.subheader("🎯 Blog Ideas")
            st.markdown(blog_ideas)
