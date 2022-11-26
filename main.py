import os

from database.database_manager import DatabaseManager
from crawler import WebCrawler
from utility.input_reader import get_config


if __name__ == "__main__":
    """
        Setup of Main Crawler Configuration
        Start Crawling here
    """
    config = get_config('config.yml')
    if os.environ.get(config["docker"]["env_var"], False):
        db_path = config["database"]["path"]
    else:
        db_path = config["database"]["local_path"]
    dbm = DatabaseManager(set_up=config["database"]["setup"], path=db_path)
    crawler = WebCrawler(config_=config, dbm_=dbm)
    if config["crawler"]["start"]:
        crawler.start_crawler()
