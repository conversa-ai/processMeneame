import scrapy
from bs4 import BeautifulSoup
import re
from scrapy.exporters import BaseItemExporter


class MeneameSpyderSpider(scrapy.Spider):
    name = "meneame_spyder"
    allowed_domains = ["old.meneame.net"]
    start_urls = ["https://old.meneame.net/"]

    def start_requests(self):
        base_url = 'https://old.meneame.net/?page='
        num_pages = 95000  # Replace with the number of pages you want to scrape
        for page_num in range(500, num_pages):
            url = base_url + str(page_num)
            yield scrapy.Request(url, callback=self.parse_page)

    def parse_page(self, response):
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all("div", {"class": "news-body"})
        for article in articles:
            article_id = article.find('a', {"id": re.compile(f"^comments-number")})['id'].split('-')[2]
            article_link = 'https://old.meneame.net' + article.find('a', {"id": re.compile(f"^comments-number")})['href']
            yield {'article_id': article_id, 'article_link': article_link}