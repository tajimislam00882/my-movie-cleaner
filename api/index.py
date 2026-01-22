from flask import Flask, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

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
        
        # ১. সব ধরণের স্ক্রিপ্ট যা বিজ্ঞাপন হতে পারে সেগুলো মুছে ফেলা
        for tag in soup.find_all(['script', 'ins', 'iframe']):
            if tag.name == 'script' and tag.get('src'):
                src = tag['src'].lower()
                # আরও কিছু কিউয়ার্ড যোগ করা হয়েছে
                if any(x in src for x in ["ads", "pop", "click", "track", "monkey", "cloud", "analytics", "doubleclick", "adservice"]):
                    tag.decompose()
            elif tag.name == 'ins' or tag.name == 'iframe':
                # ভিডিও প্লেয়ারের মেইন ফ্রেম বাদে বাকি আইফ্রেম মুছে ফেলা
                if not tag.get('id') == 'player_iframe':
                    tag.decompose()

        # ২. স্যান্ডবক্সিং (Sandbox) ব্যবহার করে রিডাইরেক্ট ঠেকানো
        # এটি ব্রাউজারকে পপ-আপ খুলতে বাধা দেবে
        html_content = str(soup)
        clean_html = html_content.replace('<iframe', '<iframe sandbox="allow-forms allow-scripts allow-same-origin allow-presentation"')

        return Response(clean_html, mimetype='text/html')
        
    except Exception as e:
        return f"Error: {str(e)}"

app = app
