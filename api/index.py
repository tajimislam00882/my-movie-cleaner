from flask import Flask, Response, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# AdGuard DNS Endpoints
ADGUARD_DNS_HTTPS = "https://d.adguard-dns.com/dns-query/3a9582d5"
ADGUARD_DNS_TLS = "tls://3a9582d5.d.adguard-dns.com"
ADGUARD_DNS_QUIC = "quic://3a9582d5.d.adguard-dns.com"

# Ad keywords to block
AD_KEYWORDS = ['ad', 'ads', 'banner', 'popup', 'overlay', 'advertising', 
               'doubleclick', 'googlesyndication', 'adserver', 'popads',
               'propeller', 'exoclick', 'adsterra', 'monetag', 'click']

# Ad domains to block
AD_DOMAINS = ['doubleclick', 'googlesyndication', 'googleadservices',
              'advertising', 'adserver', 'popads', 'propeller', 'exoclick',
              'adsterra', 'monetag', 'realsrv', 'ads.', 'ad.']

def is_blocked_url(url):
    """Check if URL should be blocked"""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in AD_DOMAINS) or any(kw in url_lower for kw in AD_KEYWORDS)

def clean_html(html_content):
    """Clean HTML from ads and tracking"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove ad scripts
    for script in soup.find_all('script'):
        if script.get('src') and is_blocked_url(script.get('src')):
            script.decompose()
        elif script.string and any(kw in script.string.lower() for kw in AD_KEYWORDS):
            script.decompose()
    
    # Remove ad iframes
    for iframe in soup.find_all('iframe'):
        if iframe.get('src') and is_blocked_url(iframe.get('src')):
            iframe.decompose()
    
    # Remove ad elements
    for element in soup.find_all(['div', 'aside', 'ins']):
        elem_class = ' '.join(element.get('class', [])).lower()
        elem_id = (element.get('id') or '').lower()
        if any(kw in elem_class or kw in elem_id for kw in AD_KEYWORDS):
            if not element.find('video'):
                element.decompose()
    
    # Add DNS and protection
    if not soup.head:
        head = soup.new_tag('head')
        soup.html.insert(0, head)
    
    # DNS meta
    dns_meta = soup.new_tag('link', rel='dns-prefetch', href=ADGUARD_DNS_HTTPS)
    soup.head.insert(0, dns_meta)
    
    # Protection script
    protection = soup.new_tag('script')
    protection.string = f"""
(function() {{
    console.log('🛡️ AdGuard DNS Active');
    window.open = function() {{ return null; }};
    document.addEventListener('click', function(e) {{
        const link = e.target.closest('a');
        if (link && link.href && !link.href.includes(window.location.hostname)) {{
            if (!link.closest('video, [class*="player"]')) {{
                e.preventDefault();
                e.stopPropagation();
                return false;
            }}
        }}
    }}, true);
    const style = document.createElement('style');
    style.textContent = '[class*="ad-"]:not([class*="player"]),[id*="ad-"]:not([id*="player"]),[class*="popup"]{{display:none!important}}';
    document.head.appendChild(style);
}})();
"""
    soup.body.append(protection) if soup.body else soup.html.append(protection)
    
    return str(soup)

@app.route('/')
def index():
    return f"""
<html>
<head><title>Ads Blocker API</title></head>
<body style="font-family:Arial;max-width:800px;margin:50px auto;padding:20px;">
<h1>🛡️ Video Ads Blocker API</h1>
<p><strong>DNS Endpoints:</strong></p>
<ul>
<li>HTTPS: <code>{ADGUARD_DNS_HTTPS}</code></li>
<li>TLS: <code>{ADGUARD_DNS_TLS}</code></li>
<li>QUIC: <code>{ADGUARD_DNS_QUIC}</code></li>
</ul>
<h2>Usage:</h2>
<p><code>/movie/550</code> - VidSrc Movie</p>
<p><code>/tv/1396/1/1</code> - VidSrc TV</p>
<p><code>/embed/vidsrc.to/embed/movie/550</code> - Custom URL</p>
</body>
</html>
"""

@app.route('/movie/<id>')
def get_movie(id):
    return fetch_and_clean(f"https://vidsrc.to/embed/movie/{id}")

@app.route('/tv/<id>/<season>/<episode>')
def get_tv(id, season, episode):
    return fetch_and_clean(f"https://vidsrc.to/embed/tv/{id}/{season}/{episode}")

@app.route('/embed/<path:url>')
def get_embed(url):
    if not url.startswith('http'):
        url = 'https://' + url
    return fetch_and_clean(url)

def fetch_and_clean(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': url
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        cleaned = clean_html(response.text)
        return Response(cleaned, mimetype='text/html')
    except Exception as e:
        return Response(f"<h1>Error</h1><p>{str(e)}</p>", status=500)

# Vercel serverless function handler
app = app
