import re
import scrapy
from scrapy_splash import SplashRequest

class BBCSpider(scrapy.Spider):
    name = "bbc"
    allowed_domains = ["bbc.com", "localhost", "127.0.0.1"]
    start_urls = ["https://www.bbc.com/news"]

    # re-use your Lua script or use the one below
    script = """
    function main(splash, args)
        splash.private_mode_enabled = false
        splash:set_user_agent(args.user_agent or "Mozilla/5.0")
        assert(splash:go(args.url))
        assert(splash:wait(args.wait or 2))
        return { html = splash:html() }
    end
    """

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(
                url,
                callback=self.parse,
                endpoint="execute",
                args={"lua_source": self.script, "wait": 2, "timeout": 90, "user_agent": "Mozilla/5.0"},
            )

    def parse(self, response):
        """Find article links and schedule article page requests."""
        raw_links = response.xpath('//a[contains(@href, "/news/")]/@href').getall()
        # filter out non-article patterns (topics, galleries, in_pictures, indexes)
        links = [
            l for l in raw_links
            if not re.search(r'^/news/(topics/|in_pictures|bbcindepth|media|av/|:)', l)
        ]

        seen = set()
        for href in links:
            url = response.urljoin(href)
            if url in seen:
                continue
            seen.add(url)
            yield SplashRequest(
                url,
                callback=self.parse_article,
                endpoint="execute",
                args={"lua_source": self.script, "wait": 2, "timeout": 90, "user_agent": "Mozilla/5.0"},
                meta={"orig_link": url},
            )

    def parse_article(self, response):
        """Extract title and body text from an article page."""
        def clean_text(parts):
            return " ".join(p.strip() for p in parts if p and p.strip())

        # Title: try <h1>, then og:title, then <title>
        title = response.xpath('normalize-space(//h1[@class="sc-f98b1ad2-0 dfvxux"]/text())').get()
        if not title:
            title = response.xpath('//meta[@property="og:title"]/@content').get()
        if not title:
            title = response.xpath('normalize-space(//title)').get()
        title = title.strip() if title else None

        # Body: try a few common containers that hold article paragraphs
        body_paras = []
        # 1) <article> tags
        body_paras = response.xpath('//div[@class="sc-3b6b161a-0 dEGcKf"]/p/text()').getall()

        body = clean_text(body_paras) if body_paras else None

        yield {
            "source": "BBC",
            "link": response.meta.get("orig_link", response.url),
            "title": title,
            "text": body
        }
