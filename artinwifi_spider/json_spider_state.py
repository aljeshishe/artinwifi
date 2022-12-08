import json
import os

from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.extensions.spiderstate import SpiderState
from twisted.internet import task


class JsonSpiderState(SpiderState):
    """Store and load spider state during a scraping job in json format with a configurable interval"""

    def __init__(self, state_jobdir, interval):
        super().__init__(jobdir=state_jobdir)
        self.counter = 0
        self.interval = interval


    @classmethod
    def from_crawler(cls, crawler):
        state_jobdir = crawler.settings['STATE_JOBDIR']
        if state_jobdir and not os.path.exists(state_jobdir):
            os.makedirs(state_jobdir)

        interval = crawler.settings.getfloat('JSON_SPIDER_STATE_DUMP_INTERVAL', default=5.0)
        if not interval:
            raise NotConfigured

        obj = cls(state_jobdir=state_jobdir, interval=interval)
        crawler.signals.connect(obj.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(obj.spider_opened, signal=signals.spider_opened)
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
