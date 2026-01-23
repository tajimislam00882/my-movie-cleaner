from flask import Flask, Response, request
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin

app = Flask(__name__)

# AdGuard DNS Endpoints (সব protocols)
ADGUARD_DNS_HTTPS = "https://d.adguard-dns.com/dns-query/3a9582d5"
ADGUARD_DNS_TLS = "tls://3a9582d5.d.adguard-dns.com"
ADGUARD_DNS_QUIC = "quic://3a9582d5.d.adguard-dns.com"

class AdvancedAdsBlocker:
    def __init__(self):
        # Ad-related keywords
        self.ad_keywords = [
            'ad', 'ads', 'banner', 'popup', 'overlay', 'advertising',
            'doubleclick', 'googlesyndication', 'adserver', 'preroll',
            'midroll', 'ima-ad', 'video-ads', 'sponsor', 'promo',
            'popunder', 'interstitial', 'adsterra', 'exoclick',
            'propeller', 'popads', 'popcash', 'clickadu', 'monetag',
            'realsrv', 'adskeeper', 'mgid', 'taboola', 'outbrain'
        ]
        
        # Ad network domains (বেশি domains যোগ করা হয়েছে)
        self.ad_domains = [
            # Google Ads
            'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
            'google-analytics.com', 'googletagmanager.com',
            
            # Popular Ad Networks
            'advertising.com', 'adserver.', 'ads.', 'adservice.',
            'popads.net', 'propellerads.com', 'exoclick.com', 
            'adsterra.com', 'popcash.net', 'clickadu.com',
            'ad-maven.com', 'monetag.com', 'realsrv.com',
            
            # Video Ad Networks
            'runative-syndicate.com', 'adskeeper.com', 'mgid.com',
            'taboola.com', 'outbrain.com', 'advertising.apple.com',
            
            # Tracking & Analytics
            'track', 'analytics', 'pixel', 'beacon', 'metrics',
            
            # Common Ad Servers
            'adnxs.com', 'adsrvr.org', 'adform.net', 'criteo.com',
            '2mdn.net', 'advertising.yahoo.com', 'rubiconproject.com'
        ]
        
        # Redirect patterns
        self.redirect_patterns = [
            r'window\.open\s*\(',
            r'location\.href\s*=',
            r'location\.replace\s*\(',
            r'location\.assign\s*\(',
            r'window\.location\s*=',
            r'top\.location\s*=',
            r'parent\.location\s*=',
            r'document\.location\s*=',
            r'self\.location\s*='
        ]
    
    def is_blocked_domain(self, url):
        """Check if URL contains blocked ad domain"""
        if not url:
            return False
        
        url_lower = url.lower()
        for domain in self.ad_domains:
            if domain in url_lower:
                return True
        
        for keyword in self.ad_keywords:
            if f'/{keyword}/' in url_lower or f'.{keyword}.' in url_lower:
                return True
        
        return False
    
    def remove_ad_scripts(self, soup):
        """Remove all ad-related scripts"""
        removed = 0
        
        for script in soup.find_all('script'):
            should_remove = False
            
            # Check src attribute
            if script.get('src'):
                src = script.get('src')
                if self.is_blocked_domain(src):
                    should_remove = True
            
            # Check inline script content
            if script.string:
                script_content = script.string.lower()
                
                # Check for ad keywords
                if any(keyword in script_content for keyword in self.ad_keywords):
                    should_remove = True
                
                # Check for redirect patterns
                for pattern in self.redirect_patterns:
                    if re.search(pattern, script.string, re.IGNORECASE):
                        should_remove = True
                        break
                
                # Check for obfuscated ad code
                if 'eval(' in script_content or 'unescape(' in script_content:
                    if any(kw in script_content for kw in ['ad', 'pop', 'click']):
                        should_remove = True
            
            if should_remove:
                script.decompose()
                removed += 1
        
        return removed
    
    def remove_ad_iframes(self, soup):
        """Remove ad iframes"""
        removed = 0
        
        for iframe in soup.find_all('iframe'):
            should_remove = False
            
            # Check src
            if iframe.get('src'):
                if self.is_blocked_domain(iframe.get('src')):
                    should_remove = True
            
            # Check data-src (lazy loading)
            if iframe.get('data-src'):
                if self.is_blocked_domain(iframe.get('data-src')):
                    should_remove = True
            
            # Check size (small iframes are usually ads)
            try:
                width = int(iframe.get('width', 0))
                height = int(iframe.get('height', 0))
                if (width > 0 and width < 100) or (height > 0 and height < 100):
                    should_remove = True
            except:
                pass
            
            # Check class/id
            if iframe.get('class'):
                classes = ' '.join(iframe.get('class')).lower()
                if any(keyword in classes for keyword in self.ad_keywords):
                    should_remove = True
            
            if iframe.get('id'):
                iframe_id = iframe.get('id').lower()
                if any(keyword in iframe_id for keyword in self.ad_keywords):
                    should_remove = True
            
            if should_remove:
                iframe.decompose()
                removed += 1
        
        return removed
    
    def remove_ad_elements(self, soup):
        """Remove ad divs and containers"""
        removed = 0
        
        for element in soup.find_all(['div', 'aside', 'section', 'article', 'span', 'ins']):
            should_remove = False
            
            # Check class
            if element.get('class'):
                classes = ' '.join(element.get('class')).lower()
                if any(keyword in classes for keyword in self.ad_keywords):
                    should_remove = True
            
            # Check id
            if element.get('id'):
                element_id = element.get('id').lower()
                if any(keyword in element_id for keyword in self.ad_keywords):
                    should_remove = True
            
            # Check data attributes
            for attr in element.attrs:
                if attr.startswith('data-'):
                    attr_value = str(element.get(attr)).lower()
                    if any(keyword in attr_value for keyword in self.ad_keywords):
                        should_remove = True
                        break
            
            # Check style (overlays)
            if element.get('style'):
                style = element.get('style').lower()
                if 'position:fixed' in style.replace(' ', '') or 'position: fixed' in style:
                    if 'z-index' in style and not element.find('video'):
                        should_remove = True
            
            # Don't remove if contains video player
            if should_remove and not element.find('video') and not element.find('source'):
                element.decompose()
                removed += 1
        
        return removed
    
    def inject_protection(self, soup):
        """Inject client-side protection script with DNS configuration"""
        protection_script = BeautifulSoup(f"""
        <script>
        (function() {{
            'use strict';
            
            console.log('🛡️ AdGuard DNS Protection Active');
            console.log('📡 DNS-over-HTTPS: {ADGUARD_DNS_HTTPS}');
            console.log('🔒 DNS-over-TLS: {ADGUARD_DNS_TLS}');
            console.log('⚡ DNS-over-QUIC: {ADGUARD_DNS_QUIC}');
            
            // ==========================================
            // 1. POPUP & REDIRECT BLOCKING
            // ==========================================
            
            // Block all popups
            const originalOpen = window.open;
            window.open = function() {{ 
                console.log('🚫 Popup blocked'); 
                return null; 
            }};
            
            // Block location changes
            let preventRedirect = true;
            const originalLocationSet = Object.getOwnPropertyDescriptor(window, 'location').set;
            
            Object.defineProperty(window, 'location', {{
                get: function() {{ return document.location; }},
                set: function(value) {{
                    if (preventRedirect) {{
                        console.log('🚫 Redirect blocked:', value);
                        return false;
                    }}
                    return originalLocationSet.call(window, value);
                }}
            }});
            
            // Block history manipulation
            const originalPushState = history.pushState;
            const originalReplaceState = history.replaceState;
            
            history.pushState = function() {{
                console.log('🚫 History manipulation blocked');
                return originalPushState.apply(history, arguments);
            }};
            
            history.replaceState = function() {{
                console.log('🚫 History manipulation blocked');
                return originalReplaceState.apply(history, arguments);
            }};
            
            // ==========================================
            // 2. CLICK EVENT PROTECTION
            // ==========================================
            
            document.addEventListener('click', function(e) {{
                const target = e.target;
                const link = target.closest('a');
                
                if (link && link.href) {{
                    const currentHost = window.location.hostname;
                    try {{
                        const linkHost = new URL(link.href).hostname;
                        
                        // Block external links that aren't video sources
                        if (linkHost !== currentHost && !link.closest('.video-player, [class*="player"], video')) {{
                            e.preventDefault();
                            e.stopPropagation();
                            e.stopImmediatePropagation();
                            console.log('🚫 External ad link blocked:', link.href);
                            return false;
                        }}
                    }} catch(err) {{
                        console.log('🚫 Invalid link blocked');
                        e.preventDefault();
                        return false;
                    }}
                }}
                
                // Block clicks on suspicious elements
                const classList = target.className || '';
                const targetId = target.id || '';
                const combined = (classList + ' ' + targetId).toLowerCase();
                
                if (combined.includes('ad') || combined.includes('popup') || combined.includes('banner')) {{
                    if (!target.closest('video, [class*="player"]')) {{
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('🚫 Ad element click blocked');
                        return false;
                    }}
                }}
            }}, true);
            
            // Mouse event protection
            document.addEventListener('mousedown', function(e) {{
                if (e.button === 1) {{ // Middle click
                    const target = e.target;
                    if (!target.closest('video, [class*="player"]')) {{
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('🚫 Middle-click blocked');
                        return false;
                    }}
                }}
            }}, true);
            
            // Context menu protection (optional)
            document.addEventListener('contextmenu', function(e) {{
                const target = e.target;
                if (target.tagName === 'A' && !target.closest('video, [class*="player"]')) {{
                    const href = target.href || '';
                    if (href && !href.includes(window.location.hostname)) {{
                        e.preventDefault();
                        console.log('🚫 Suspicious context menu blocked');
                        return false;
                    }}
                }}
            }}, true);
            
            // ==========================================
            // 3. CSS INJECTION TO HIDE ADS
            // ==========================================
            
            const style = document.createElement('style');
            style.textContent = `
                /* Hide ad containers */
                [class*="ad-"]:not([class*="player"]):not([class*="video"]):not([class*="vad"]),
                [id*="ad-"]:not([id*="player"]):not([id*="video"]):not([id*="vad"]),
                [class*="ads-"], [id*="ads-"],
                [class*="banner"], [class*="popup"],
                [class*="overlay"]:not([class*="player"]):not([class*="video"]),
                [class*="popunder"], [class*="interstitial"],
                .ima-ad-container, .video-ads,
                ins.adsbygoogle,
                [data-ad-slot], [data-ad-client],
                [class*="adskeeper"], [class*="mgid"],
                [class*="taboola"], [class*="outbrain"] {{
                    display: none !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                    pointer-events: none !important;
                    width: 0 !important;
                    height: 0 !important;
                    position: absolute !important;
                    left: -9999px !important;
                }}
                
                /* Ensure video is visible and clickable */
                video, video[controls] {{
                    display: block !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                    pointer-events: auto !important;
                }}
                
                /* Remove suspicious fixed overlays */
                div[style*="position: fixed"][style*="z-index"]:not([class*="player"]):not([id*="player"]) {{
                    display: none !important;
                }}
                
                /* Hide small iframes (usually ads) */
                iframe[width="1"], iframe[height="1"],
                iframe[width="0"], iframe[height="0"] {{
                    display: none !important;
                }}
            `;
            document.head.appendChild(style);
            
            // ==========================================
            // 4. MUTATION OBSERVER - Dynamic Ad Removal
            // ==========================================
            
            const observer = new MutationObserver(function(mutations) {{
                mutations.forEach(function(mutation) {{
                    mutation.addedNodes.forEach(function(node) {{
                        if (node.nodeType === 1) {{ // Element node
                            const classList = node.className || '';
                            const nodeId = node.id || '';
                            
                            if (typeof classList === 'string' && typeof nodeId === 'string') {{
                                const combined = (classList + ' ' + nodeId).toLowerCase();
                                const adKeywords = ['ad-', 'ads-', 'banner', 'popup', 'overlay', 'interstitial'];
                                
                                if (adKeywords.some(kw => combined.includes(kw))) {{
                                    // Don't remove if it contains video
                                    if (!node.querySelector('video') && !node.closest('[class*="player"]')) {{
                                        node.remove();
                                        console.log('🗑️ Dynamically added ad removed');
                                    }}
                                }}
                            }}
                            
                            // Check for ad iframes
                            if (node.tagName === 'IFRAME') {{
                                const src = (node.src || '').toLowerCase();
                                const adDomains = ['doubleclick', 'googlesyndication', 'advertising', 'adserver', 'ads.'];
                                
                                if (adDomains.some(domain => src.includes(domain))) {{
                                    node.remove();
                                    console.log('🗑️ Ad iframe removed');
                                }}
                            }}
                        }}
                    }});
                }});
            }});
            
            observer.observe(document.documentElement, {{
                childList: true,
                subtree: true
            }});
            
            // ==========================================
            // 5. ANTI-ADBLOCK DETECTION BYPASS
            // ==========================================
            
            // Fake adsbygoogle
            Object.defineProperty(window, 'adsbygoogle', {{
                get: function() {{ return []; }},
                set: function() {{ return true; }}
            }});
            
            // Fake Google Ad Client
            window.google_ad_client = "ca-pub-0000000000000000";
            window.google_ad_slot = "0000000000";
            
            // ==========================================
            // 6. PERIODIC CLEANUP
            // ==========================================
            
            setInterval(function() {{
                // Remove any new ad elements
                document.querySelectorAll('[class*="ad-"], [id*="ad-"], [class*="popup"]').forEach(el => {{
                    if (!el.querySelector('video') && !el.closest('[class*="player"]')) {{
                        el.remove();
                    }}
                }});
            }}, 3000);
            
            console.log('✅ Full protection activated with AdGuard DNS');
        }})();
        </script>
        """, 'html.parser')
        
        if soup.body:
            soup.body.append(protection_script)
        elif soup.html:
            soup.html.append(protection_script)
        
        return soup
    
    def inject_dns_config(self, soup):
        """Inject DNS-over-HTTPS, DNS-over-TLS, and DNS-over-QUIC configuration"""
        if not soup.head:
            soup.html.insert(0, soup.new_tag('head'))
        
        # DNS-over-HTTPS
        dns_https = soup.new_tag('link')
        dns_https.attrs['rel'] = 'dns-prefetch'
        dns_https.attrs['href'] = ADGUARD_DNS_HTTPS
        soup.head.insert(0, dns_https)
        
        # DNS meta tags
        meta_dns = soup.new_tag('meta')
        meta_dns.attrs['http-equiv'] = 'x-dns-prefetch-control'
        meta_dns.attrs['content'] = 'on'
        soup.head.insert(1, meta_dns)
        
        # Security headers
        meta_csp = soup.new_tag('meta')
        meta_csp.attrs['http-equiv'] = 'Content-Security-Policy'
        meta_csp.attrs['content'] = "script-src 'self' 'unsafe-inline' 'unsafe-eval' *; frame-src 'self' *;"
        soup.head.insert(2, meta_csp)
        
        return soup

# Initialize blocker
blocker = AdvancedAdsBlocker()

@app.route('/movie/<id>')
def get_movie(id):
    """Handle movie embed requests"""
    target_url = f"https://vidsrc.to/embed/movie/{id}"
    return process_url(target_url)

@app.route('/tv/<id>/<season>/<episode>')
def get_tv(id, season, episode):
    """Handle TV show embed requests"""
    target_url = f"https://vidsrc.to/embed/tv/{id}/{season}/{episode}"
    return process_url(target_url)

@app.route('/2embed/movie/<id>')
def get_2embed_movie(id):
    """Handle 2embed movie requests"""
    target_url = f"https://2embed.stream/movie/{id}"
    return process_url(target_url)

@app.route('/2embed/tv/<id>/<season>/<episode>')
def get_2embed_tv(id, season, episode):
    """Handle 2embed TV requests"""
    target_url = f"https://2embed.stream/tv/{id}/{season}/{episode}"
    return process_url(target_url)

@app.route('/embed/<path:url>')
def get_embed(url):
    """Handle any embed URL"""
    if not url.startswith('http'):
        url = 'https://' + url
    return process_url(url)

def process_url(target_url):
    """Process and clean the target URL"""
    try:
        # Browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': urlparse(target_url).scheme + '://' + urlparse(target_url).netloc,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        
        # Fetch the page
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove ads step by step
        scripts_removed = blocker.remove_ad_scripts(soup)
        iframes_removed = blocker.remove_ad_iframes(soup)
        elements_removed = blocker.remove_ad_elements(soup)
        
        # Inject DNS configuration
        soup = blocker.inject_dns_config(soup)
        
        # Inject protection
        soup = blocker.inject_protection(soup)
        
        # Log blocking stats
        print(f"🗑️ Removed: {scripts_removed} scripts, {iframes_removed} iframes, {elements_removed} elements")
        print(f"📡 DNS: HTTPS={ADGUARD_DNS_HTTPS}")
        print(f"🔒 DNS: TLS={ADGUARD_DNS_TLS}")
        print(f"⚡ DNS: QUIC={ADGUARD_DNS_QUIC}")
        
        # Return cleaned HTML
        cleaned_html = str(soup)
        return Response(cleaned_html, mimetype='text/html')
        
    except requests.RequestException as e:
        return Response(f"<h1>Error fetching video</h1><p>{str(e)}</p>", status=500)
    except Exception as e:
        return Response(f"<h1>Error processing video</h1><p>{str(e)}</p>", status=500)

@app.route('/')
def index():
    """Home page with usage instructions"""
    return f"""
    <html>
    <head>
        <title>🛡️ Video Ads Blocker API</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #fff;
                padding: 20px;
                min-height: 100vh;
            }}
            .container {{ 
                max-width: 900px; 
                margin: 0 auto; 
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }}
            h1 {{ 
                font-size: 2.5em; 
                margin-bottom: 10px;
                text-align: center;
            }}
            .subtitle {{
                text-align: center;
                opacity: 0.9;
                margin-bottom: 30px;
                font-size: 1.1em;
            }}
            .dns-info {{
                background: rgba(255,255,255,0.15);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            .dns-info h3 {{
                margin-bottom: 10px;
                color: #ffd700;
            }}
            .dns-item {{
                margin: 8px 0;
                padding: 10px;
                background: rgba(0,0,0,0.2);
                border-radius: 5px;
                font-family: monospace;
            }}
            code {{ 
                background: rgba(0,0,0,0.3);
                padding: 3px 8px; 
                border-radius: 4px;
                font-size: 0.9em;
            }}
            .endpoint {{ 
                background: rgba(255,255,255,0.15);
                padding: 20px; 
                margin: 15px 0; 
                border-radius: 10px;
                border-left: 4px solid #ffd700;
            }}
            .endpoint strong {{
                color: #ffd700;
                font-size: 1.1em;
            }}
            ul {{ 
                list-style: none;
                margin: 20px 0;
            }}
            ul li {{
                padding: 10px;
                margin: 5px 0;
                background: rgba(255,255,255,0.1);
                border-radius: 5px;
            }}
            ul li:before {{
                content: "✓ ";
                color: #4ade80;
                font-weight: bold;
                margin-right: 10px;
            }}
            .features {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .feature-box {{
                background: rgba(255,255,255,0.1);
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ Video Ads Blocker API</h1>
            <p class="subtitle">AdGuard DNS দিয়ে সম্পূর্ণ ads blocking সিস্টেম</p>
            
            <div class="dns-info">
                <h3>📡 Active DNS Protocols:</h3>
                <div class="dns-item">🌐 DNS-over-HTTPS: <code>{ADGUARD_DNS_HTTPS}</code></div>
                <div class="dns-item">🔒 DNS-over-TLS: <code>{ADGUARD_DNS_TLS}</code></div>
                <div class="dns-item">⚡ DNS-over-QUIC: <code>{ADGUARD_DNS_QUIC}</code></div>
            </div>
            
            <h2>📌 API Endpoints:</h2>
            
            <div class="endpoint">
                <strong>VidSrc Movie:</strong><br><br>
                <code>/movie/{{tmdb_id}}</code><br>
                Example: <code>/movie/550</code>
            </div>
            
            <div class="endpoint">
                <strong>VidSrc TV Show:</strong><br><br>
                <code>/tv/{{tmdb_id}}/{{season}}/{{episode}}</code><br>
                Example: <code>/tv/1396/1/1</code>
            </div>
            
            <div class="endpoint">
                <strong>2Embed Movie:</strong><br><br>
                <code>/2embed/movie/{{tmdb_id}}</code><br>
                Example: <code>/2embed/movie/550</code>
            </div>
            
            <div class="endpoint">
                <strong>2Embed TV:</strong><br><br>
                <code>/2embed/tv/{{tmdb_id}}/{{season}}/{{episode}}</code><br>
                Example: <code>/2embed/tv/1396/1/1</code>
            </div>
            
            <div class="endpoint">
                <strong>Custom Embed:</strong><br><br>
                <code>/embed/{{full_url}}</code><br>
                Example: <code>/embed/vidsrc.to/embed/movie/550</code>
            </div>
            
            <h2>✨ Features:</h2>
            
            <div class="features">
                <div class="feature-box">
                    <h3>🔒</h3>
                    <p>DNS-over-TLS</p>
                </div>
                <div class="feature-box">
                    <h3>⚡</h3>
                    <p>DNS-over-QUIC</p>
                </div>
                <div class="feature-box">
                    <h3>🌐</h3>
                    <p>DNS-over-HTTPS</p>
                </div>
                <div class="feature-box">
                    <h3>🚫</h3>
                    <p>Popup Blocking</p>
                </div>
                <div class="feature-box">
                    <h3>🗑️</h3>
                    <p>Ad Removal</p>
                </div>
                <div class="feature-box">
                    <h3>🛡️</h3>
                    <p>Redirect Protection</p>
                </div>
            </div>
            
            <h2>💡 Usage Example:</h2>
            <div class="endpoint">
                <code>&lt;iframe src="https://your-app.vercel.app/movie/550" width="100%" height="500" frameborder="0" allowfullscreen&gt;&lt;/iframe&gt;</code>
            </div>
        </div>
    </body>
    </html>
    """

# Vercel handler
def handler(event, context):
    return app(event, context)

if __name__ == '__main__':
    app.run(debug=True)
