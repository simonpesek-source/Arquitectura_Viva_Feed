from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
import time

url = 'https://arquitecturaviva.com/works'

# Nastavení skrytého prohlížeče (Headless Chrome pro automatické skripty)
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
    print("Čekám na načtení projektů pomocí JavaScriptu...")
    time.sleep(5)  # Počkáme 5 vteřin, než si stránka dotáhne články
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # Najdeme kontejner, do kterého se nahrávají výsledky
    container = soup.find('div', id='resultados')
    
    if container:
        # Projdeme všechny odkazy (karty článků) uvnitř výsledků
        for item in container.find_all('a'):
            href = item.get('href', '')
            if not href or href in seen_links or 'javascript' in href:
                continue
                
            full_url = href if href.startswith('http') else 'https://arquitecturaviva.com' + href
            
            # Zkusíme najít nadpis (často bývá v h2, h3, nebo uvnitř silného textu/spanu)
            title_tag = item.find(['h2', 'h3', 'h4', 'strong', 'span'])
            title = title_tag.get_text(strip=True) if title_tag else item.get_text(strip=True)
            
            # Vyfiltrujeme prázdné nebo nesmyslné odkazy (např. prázdné ikony)
            if not title or len(title) < 3:
                continue
                
            # Hledání obrázku (často jako tag img, nebo data-src u líného načítání)
            img_tag = item.find('img')
            image_url = ""
            if img_tag:
                image_url = img_tag.get('src') or img_tag.get('data-src') or ""
                if image_url and not image_url.startswith('http'):
                    image_url = 'https://arquitecturaviva.com' + image_url
            
            seen_links.add(href)
            
            # Opět vložíme obrázek duplicitně pro podporu různých čteček
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
            <description><![CDATA[<p>Nový projekt na Arquitectura Viva: <strong>{title}</strong></p>]]></description>
            {enclosure_tag}
            {media_tag}
        </item>"""
            
            count += 1
            if count >= 20: # Omezíme generování na 20 nejnovějších, ať XML není zbytečně obrovské
                break
    else:
        print("Kontejner s výsledky se na stránce nenašel.")

except Exception as e:
    print(f"Kritická chyba: {e}")
finally:
    # Prohlížeč musíme za každých okolností bezpečně zavřít
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
