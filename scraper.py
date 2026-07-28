from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re

url = 'https://arquitecturaviva.com/works'

chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

print("Spouštím prohlížeč na pozadí...")
driver = webdriver.Chrome(options=chrome_options)

rss_items = ""
count = 0
seen_links = set()

try:
    driver.get(url)
    print("Čekám na prvotní načtení...")
    time.sleep(3)
    
    # KROK NAVÍC: Skrolujeme dolů, aby se aktivovaly líné obrázky (lazy-loading)
    print("Skroluji pro načtení obrázků...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
    time.sleep(3)
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    container = soup.find('div', id='resultados')
    
    if container:
        for link_tag in container.find_all('a'):
            href = link_tag.get('href', '')
            if not href or 'javascript' in href:
                continue
                
            full_url = href if href.startswith('http') else 'https://arquitecturaviva.com' + href
            
            if full_url in seen_links:
                continue
            
            title_tag = link_tag.find(['h2', 'h3', 'h4', 'strong', 'span'])
            title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
            
            # Pokud je odkaz prázdný nebo nesmyslný, přeskočíme ho
            if not title or len(title) < 3:
                continue
            
            # --- AGRESIVNÍ ZÍSKÁNÍ OBRÁZKU V OKOLÍ ODKAZU ---
            image_url = ""
            context = link_tag
            
            # Půjdeme až o 4 úrovně HTML bloků výš, abychom fotku chytli, i když není součástí odkazu
            for _ in range(4): 
                if not context or context.get('id') == 'resultados' or context.name == 'body':
                    break
                
                # Hledáme ve všech dětech aktuálního bloku
                for el in context.find_all(['img', 'source', 'div', 'figure', 'span']):
                    # Široká paleta lazy-loading atributů, které vývojáři používají
                    for attr in ['data-original', 'data-src', 'data-lazy', 'data-srcset', 'srcset', 'src', 'data-bg', 'style']:
                        val = el.get(attr, '')
                        
                        if attr == 'style' and val:
                            match = re.search(r'url\(\s*[\'"]?(.*?)[\'"]?\s*\)', val)
                            if match:
                                val = match.group(1).replace('\\/', '/').replace('\\.', '.').replace('\\', '').strip()
                                if val and 'data:image' not in val:
                                    image_url = val
                                    break
                        elif val and isinstance(val, str) and 'data:image' not in val and '.svg' not in val and 'avatar' not in val:
                            # Ošetření formátu "srcset", který obsahuje více adres oddělených čárkou
                            if ',' in val: 
                                val = val.split(',')[0].strip().split(' ')[0]
                            image_url = val
                            break
                            
                    if image_url: break
                if image_url: break
                
                context = context.parent
            
            # Úprava, aby URL byla kompletní a funkční pro RSS čtečku
            if image_url and not image_url.startswith('http'):
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    image_url = 'https://arquitecturaviva.com' + image_url
            
            seen_links.add(full_url)
            
            # Metadata pouze s obrázkem, bez vkládání do description (abys v CommaFeedu neměl zdvojené fotky a texty navíc)
            enclosure_tag = ""
            media_tag = ""
            if image_url:
                clean_img = image_url.replace('&', '&amp;')
                enclosure_tag = f'<enclosure url="{clean_img}" type="image/jpeg" length="1024" />'
                media_tag = f'<media:content url="{clean_img}" medium="image" />'
            
            rss_items += f"""
        <item>
            <title><![CDATA[{title}]]></title>
            <link>{full_url}</link>
            <guid>{full_url}</guid>
            <description><![CDATA[<p><strong>{title}</strong></p>]]></description>
            {enclosure_tag}
            {media_tag}
        </item>"""
            
            count += 1
            if count >= 20:
                break
    else:
        print("Kontejner #resultados se na stránce nenašel.")

except Exception as e:
    print(f"Chyba: {e}")
finally:
    driver.quit()

# Vygenerování platného RSS XML
rss_feed = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
  <title>Arquitectura Viva - Works</title>
  <link>{url}</link>
  <description>Nejnovější projekty z Arquitectura Viva</description>
  <lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>
  {rss_items}
</channel>
</rss>"""

with open('feed.xml', 'w', encoding='utf-8') as f:
    f.write(rss_feed)

print(f"HOTOVO: Zpracováno {count} projektů.")
