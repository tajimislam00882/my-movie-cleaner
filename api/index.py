from flask import Flask, Response, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

class VideoAdsBlocker:
    def __init__(self):
        self.ad_keywords = ['ad', 'ads', 'banner', 'popup', 'overlay', 'advertising', 'doubleclick', 'googlesyndication', 'adserver', 'preroll', 'midroll', 'ima-ad', 'video-ads', 'sponsor', 'promo']
        self.ad_domains = ['doubleclick.net', 'googlesyndication.com', 'googleadservices.com', 'advertising.com', 'popads.net', 'propellerads.com', 'exoclick.com', 'adsterra.com']
        self.redirect_patterns = [r'window\.open\(', r'location\.href\s*=', r'location\.replace\(', r'window\.location\s*=']

    def clean_html(self, html_content):
        # জাভাস্ক্রিপ্ট রিডাইরেক্ট রিমুভ (Regex)
        for pattern in self.redirect_patterns:
            html_content = re.sub(pattern, '// BLOCKED REDIRECT: ', html_content, flags=re.IGNORECASE)

        soup = BeautifulSoup(html_content, 'html.parser')

        # অ্যাড এলিমেন্ট রিমুভ
        for element in soup.find_all():
            attr_str = str(element.get('class', [])) + str(element.get('id', ''))
            if any(key in attr_str.lower() for key in self.ad_keywords):
                if not element.find('video') and 'player' not in attr_str.lower():
                    element.decompose()

        # প্রটেকশন স্ক্রিপ্ট ইনজেক্ট
        protection_script = """
        <script>
        window.open = function() { console.log('🚫 Popup blocked'); return null; };
        document.addEventListener('click', function(e) {
            const href = e.target.closest('a')?.href;
            if (href && !href.includes(window.location.hostname)) {
                e.preventDefault();
                return false;
            }
        }, true);
        </script>
        <style>
            [class*="ad-"], [id*="ad-"], .ima-ad-container, .video-ads { display: none !important; }
        </style>
        """
        if soup.head:
            soup.head.insert(0, BeautifulSoup(protection_script, 'html.parser'))
        
        # আইফ্রেম স্যান্ডবক্সিং
        final_html = str(soup).replace('<iframe', '<iframe sandbox="allow-forms allow-scripts allow-same-origin allow-presentation"')
        return final_html

blocker = VideoAdsBlocker()

@app.route('/')
def home():
    return "vidsrc-embed.ru Cleaner is Running! Use /movie/ID or /tv/ID/S-E"

# মুভির জন্য এন্ডপয়েন্ট
@app.route('/movie/<id>')
def get_movie(id):
    target_url = f"https://vidsrc-embed.ru/embed/movie/{id}"
    return process_request(target_url)

# টিভি শো এবং এপিসোডের জন্য এন্ডপয়েন্ট (যেমন: /tv/tt0944947/1-1)
@app.route('/tv/<id>/<se>')
def get_tv(id, se):
    target_url = f"https://vidsrc-embed.ru/embed/tv/{id}/{se}"
    return process_request(target_url)

def process_request(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://vidsrc-embed.ru/'
        }
        response = requests.get(url, headers=headers, timeout=10)
        cleaned_page = blocker.clean_html(response.text)
        return Response(cleaned_page, mimetype='text/html')
    except Exception as e:
        return f"Error: {str(e)}"

app = app
