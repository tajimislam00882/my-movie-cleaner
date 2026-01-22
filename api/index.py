from flask import Flask, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# তোমার দেওয়া অ্যাড-ব্লকার জাভাস্ক্রিপ্ট কোড
AD_BLOCKER_JS = """
<script>
(function() {
    'use strict';
    // পপ-আপ এবং রিডাইরেক্ট ব্লক করার জন্য উইন্ডো ওপেন ফাংশন বন্ধ করা
    window.open = function() { return null; };
    
    // বিজ্ঞাপন এলিমেন্ট রিমুভ করার ফাংশন
    function removeAds() {
        const adSelectors = ['[class*="ad-"]', '[id*="ad-"]', '.ima-ad-container', '.video-ads', 'iframe[src*="doubleclick"]'];
        adSelectors.forEach(s => {
            document.querySelectorAll(s).forEach(el => {
                if (!el.querySelector('video')) el.remove();
            });
        });
    }

    // পেজে নতুন কোনো বিজ্ঞাপন আসলে তা সাথে সাথে ডিলিট করা
    const observer = new MutationObserver(() => { removeAds(); });
    observer.observe(document.documentElement, { childList: true, subtree: true });

    console.log('✅ Advanced Ads Blocker Activated!');
})();
</script>
"""

@app.route('/')
def home():
    return "Movie Cleaner Server is Running! Use /movie/IMDB_ID"

@app.route('/movie/<id>')
def get_movie(id):
    # তোমার চাওয়া multiembed সোর্স
    target_url = f"https://multiembed.mov/?video_id={id}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Referer': 'https://multiembed.mov/'
        }
        
        response = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # ১. হেড ট্যাগ বা পেজের শুরুতে অ্যাড-ব্লকার জাভাস্ক্রিপ্ট ইনজেক্ট করা
        if soup.head:
            soup.head.insert(0, BeautifulSoup(AD_BLOCKER_JS, 'html.parser'))
        else:
            soup.insert(0, BeautifulSoup(AD_BLOCKER_JS, 'html.parser'))

        # ২. স্যান্ডবক্সিং যোগ করা যাতে ব্রাউজার রিডাইরেক্ট হতে না পারে
        html_content = str(soup)
        clean_html = html_content.replace('<iframe', '<iframe sandbox="allow-forms allow-scripts allow-same-origin allow-presentation"')

        return Response(clean_html, mimetype='text/html')
    except Exception as e:
        return f"Error: {str(e)}"

# Vercel-এর জন্য এক্সপোর্ট
app = app
