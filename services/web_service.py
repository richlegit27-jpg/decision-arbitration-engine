import requests
from bs4 import BeautifulSoup

class WebService:
    def fetch_summary(self, url:str)->str:
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text,'html.parser')
            title = soup.title.string.strip() if soup.title else ''
            desc_tag = soup.find('meta', attrs={'name':'description'})
            desc = desc_tag['content'].strip() if desc_tag and desc_tag.get('content') else ''
            return f"Title: {title}\nDescription: {desc}" if title or desc else "Web page fetched, no summary available."
        except Exception as e:
            return f"Failed to fetch web content: {str(e)}"