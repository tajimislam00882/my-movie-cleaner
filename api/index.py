from flask import Flask, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def home():
    return "সার্ভার চালু আছে! মুভি দেখতে লিঙ্কের শেষে /movie/IMDB_ID যোগ করুন।"

@app.route('/movie/<id>')
def get_movie(id):
    target_url = f"https://vidsrc.to/embed/movie/{id}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Referer': 'https://vidsrc.to/'
        }
        
        response = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # বিজ্ঞাপন স্ক্রিপ্ট রিমুভ করা
        for tag in soup.find_all(['script', 'ins']):
            if tag.name == 'script' and tag.get('src'):
                src = tag['src'].lower()
                if any(x in src for x in ["ads", "pop", "click", "track", "monkey", "cloud", "analytics"]):
                    tag.decompose()
            elif tag.name == 'ins':
                tag.decompose()

        # স্যান্ডবক্সিং ব্যবহার করে অটো রিডাইরেক্ট বন্ধ করা
        html_content = str(soup)
        clean_html = html_content.replace('<iframe', '<iframe sandbox="allow-forms allow-scripts allow-same-origin allow-presentation"')

        return Response(clean_html, mimetype='text/html')
    except Exception as e:
        return f"Error: {str(e)}"

# Vercel হ্যান্ডলার
app = app
