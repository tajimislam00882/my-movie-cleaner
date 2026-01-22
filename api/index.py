from flask import Flask, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/movie/<id>')
def get_movie(id):
    # VidSrc এর আসল সোর্স লিঙ্ক
    target_url = f"https://vidsrc.to/embed/movie/{id}"
    
    try:
        # ব্রাউজারের মতো ছদ্মবেশ ধরার জন্য হেডার
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Referer': 'https://vidsrc.to/'
        }
        
        # ১. ওয়েবসাইট থেকে ডেটা নিয়ে আসা
        response = requests.get(target_url, headers=headers)
        
        # ২. কোড এডিট করা শুরু (Filtering)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ৩. ক্ষতিকর বা বিজ্ঞাপন স্ক্রিপ্টগুলো রিমুভ করা
        for script in soup.find_all("script"):
            if script.get("src"):
                src = script["src"].lower()
                # নিচের শব্দগুলো যে স্ক্রিপ্টে আছে সেগুলো ডিলিট হবে
                if any(x in src for x in ["ads", "pop", "click", "track", "monkey", "cloud", "analytics"]):
                    script.decompose()
        
        # ৪. পরিষ্কার করা কোড ইউজারকে পাঠানো
        return Response(str(soup), mimetype='text/html')
        
    except Exception as e:
        return f"Error: {str(e)}"

# Vercel এর জন্য হ্যান্ডলার
def handler(request):
    return app(request)