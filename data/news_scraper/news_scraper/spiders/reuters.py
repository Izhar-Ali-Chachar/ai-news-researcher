import scrapy


class ReutersSpider(scrapy.Spider):
    name = "reuters"
    allowed_domains = ["www.reuters.com"]
    start_urls = ["https://www.reuters.com/world"]

    def parse(self, response):
        pass
