from flask import Flask, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def home():
    return "SuperEmbed Cleaner is Running! Use /movie/IMDB_ID"

@app.route('/movie/<id>')
def get_movie(id):
    # SuperEmbed এর URL প্যাটার্ন
    target_url = f"https://www.superembed.stream/video/{id}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Referer': 'https://www.superembed.stream/'
        }
        
        # ১. সোর্স সাইট থেকে ডেটা আনা
        response = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ২. পরিচিত বিজ্ঞাপনের স্ক্রিপ্ট এবং আইফ্রেম মুছে ফেলা
        for tag in soup.find_all(['script', 'ins', 'iframe']):
            if tag.name == 'script' and tag.get('src'):
                src = tag['src'].lower()
                if any(x in src for x in ["ads", "pop", "click", "track", "analytics", "doubleclick"]):
                    tag.decompose()
            elif tag.name == 'ins':
                tag.decompose()
        
        # ৩. স্যান্ডবক্সিং যোগ করা (রিডাইরেক্ট এবং পপ-আপ বন্ধ করতে)
        html_content = str(soup)
        # এটি ভিডিও প্লেয়ারকে একটি নিরাপদ 'বক্স' এর মধ্যে আটকে রাখে
        clean_html = html_content.replace('<iframe', '<iframe sandbox="allow-forms allow-scripts allow-same-origin allow-presentation"')

        return Response(clean_html, mimetype='text/html')
        
    except Exception as e:
        return f"Error: {str(e)}"

# Vercel এর জন্য এক্সপোর্ট
app = app
