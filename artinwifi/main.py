import json
import logging
from pathlib import Path
from typing import Any

import click
from scrapy.crawler import CrawlerProcess

from artinwifi import logging_config
from artinwifi.spider import Spider
import munch



@click.command()
@click.option("-m", "--mac_address", help="Mac address.")
@click.option("-w", "--workers", help="Workers", default=3)
@click.option("-s", "--start", help="Password start", default="000000")
@click.option("-e", "--end", help="Password end", default="999999")
@click.option("-a", "--alphabet", help="Alphabet", default="0123456789")
@click.option('-v', '--verbose', count=True)
def main(**kwargs) -> None:
    process = CrawlerProcess()
    process.crawl(Spider(**kwargs))
    process.start()


if __name__ == "__main__":
    main()

