from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import json
import time
import os

MONGO_URI = os.getenv('MONGO_URI')  # 👈 이 방식으로 교체
print(MONGO_URI)
def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def get_top10_links_with_selenium(driver):
    driver.get('https://www.fmkorea.com/best2')
    time.sleep(5)  # 렌더링 및 Cloudflare 통과 대기

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = []
    for a in soup.select('h3.title > a')[:10]:
        href = a.get('href')
        if href:
            links.append('https://www.fmkorea.com' + href)
    return links

def parse_post(driver, url):
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    title_el = soup.select_one('h1.np_18px span')
    title = title_el.get_text(strip=True) if title_el else '제목 없음'

    content_el = soup.select_one('div.xe_content')
    body = content_el.get_text(separator='\n', strip=True) if content_el else '본문 없음'

    images = []
    if content_el:
        for img in content_el.find_all('img'):
            src = img.get('src')
            if src and src.startswith('/'):
                src = 'https://' + src
            images.append(src)

    return {
        'url': url,
        'title': title,
        'body': body,
        'images': images,
        'scrapedAt': datetime.utcnow().isoformat(),
        'source': 'fmkorea'
    }

def save_to_json(posts, filename='posts.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

def save_to_mongo(posts):
    client = MongoClient(MONGO_URI)
    db = client.mycommunity
    col = db.scrapedposts

    for post in posts:
        col.update_one({ 'url': post['url'] }, { '$set': post }, upsert=True)
    print(f"✅ MongoDB에 {len(posts)}개 저장 완료")

if __name__ == '__main__':
    driver = setup_driver()
    links = get_top10_links_with_selenium(driver)
    print(f"🔗 Top 10 링크 수집 완료 ({len(links)}개)")

    posts = []
    for i, link in enumerate(links, 1):
        print(f'📄 {i}. 수집 중: {link}')
        try:
            post = parse_post(driver, link)
            posts.append(post)
        except Exception as e:
            print(f'⚠️ 에러: {e}')
        time.sleep(1)

    driver.quit()
    save_to_json(posts)
    save_to_mongo(posts)
