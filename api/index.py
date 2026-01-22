from flask import Flask, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def home():
    return "MultiEmbed Cleaner is Running! Use /movie/IMDB_ID"

@app.route('/movie/<id>')
def get_movie(id):
    # MultiEmbed এর URL স্ট্রাকচার
    target_url = f"https://multiembed.mov/?video_id={id}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Referer': 'https://multiembed.mov/'
        }
        
        # ১. সোর্স সাইট থেকে ডেটা আনা
        response = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ২. বিজ্ঞাপন এবং ট্র্যাকিং স্ক্রিপ্ট পরিষ্কার করা
        for tag in soup.find_all(['script', 'ins', 'iframe']):
            if tag.name == 'script' and tag.get('src'):
                src = tag['src'].lower()
                # পপ-আপ এবং পরিচিত অ্যাড নেটওয়ার্ক ফিল্টার
                if any(x in src for x in ["ads", "pop", "click", "track", "monkey", "cloud", "analytics"]):
                    tag.decompose()
            elif tag.name == 'ins':
                tag.decompose()

        # ৩. স্যান্ডবক্সিং (Sandbox) যোগ করা
        # এটি রিডাইরেক্ট এবং পপ-আপ অ্যাড পুরোপুরি বন্ধ করতে সাহায্য করবে
        html_content = str(soup)
        clean_html = html_content.replace('<iframe', '<iframe sandbox="allow-forms allow-scripts allow-same-origin allow-presentation"')

        return Response(clean_html, mimetype='text/html')
        
    except Exception as e:
        return f"Error occurred: {str(e)}"

# Vercel এর জন্য হ্যান্ডলার
app = app
