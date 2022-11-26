import asyncio
import logging
import time
import traceback
import random

import validators
import os
from typing import Any, List
from selenium.webdriver.chrome.options import Options

from concurrent.futures.thread import ThreadPoolExecutor
from urllib.parse import urlparse

from selenium import webdriver

from database.database_manager import DatabaseManager
from utility.ad_tracking_detection import find_ad_tracking
from utility.html_tag_extractor import HTMLTagExtractor
from utility.input_reader import read_input
from utility.src_lang_analyzer import SrcLanguageAnalyzer
from utility.wappalyzer_api import WappalyzerAnalyzer
from utility.web_assembly_analyser import WebAssemblyAnalyzer
from utility.website_data import WebsiteData


class WebCrawler:
    def __init__(self, config_: dict, dbm_: DatabaseManager):
        """
        Set up Crawler
        :param config_: Main configuration
        :param dbm_: DatabaseManager
        """
        self.config_ = config_
        self.dbm_ = dbm_

    @staticmethod
    def check_url_validity(url_: str) -> bool:
        """
        Check if a URL is syntactically valid
        :param url_: input url
        :return: boolean if valid or not
        """
        if validators.url(url_):
            return True
        else:
            logging.info("%s is not a valid hyperlink", str(url_))
        return False

    def scrape(self, executor: Any, chrome_options: Any, url: str, *, loop):
        """
        :param executor: ThreadPoolExecutor
        :param chrome_options: Chrome Options
        :param url: Current URL to crawl
        :param loop: asyncio loop
        """
        loop.run_in_executor(executor, self.crawler, chrome_options, url)

    def get_filtered_next_urls(self, next_urls: list) -> List[dict]:
        """
        Filter hyperlinks on website by netloc and config set breadth
        :param next_urls: next URL to be crawled
        :return: updated next_urls
        """
        if not (self.config_["crawler"]["extern_hyperlinks"] and self.config_["crawler"]["intern_hyperlinks"]):
            for i in next_urls:
                n = []
                for j in i["next"]:
                    netloc = urlparse(j).netloc.split(".")[0]
                    root_netloc = urlparse(i["root"]).netloc.split(".")[0]
                    if (self.config_["crawler"]["extern_hyperlinks"] and netloc != root_netloc) \
                            or (self.config_["crawler"]["intern_hyperlinks"] and netloc == root_netloc):
                        n.append(j)
                i["next"] = n
        logging.info("Next valid urls to crawl: %s", str(next_urls))
        breadth = self.config_["crawler"]["breadth"]
        if breadth != "max":
            for i in next_urls:
                if breadth < len(i["next"]):
                    random.shuffle(i["next"])
                    i["next"] = i["next"][:breadth]
            if breadth < len(i["next"]):
                random.shuffle(next_urls)
                next_urls = next_urls[:breadth]
        return next_urls

    def recursive_crawl(self, driver: Any, next_urls: list, current_depth: int) -> List[dict]:
        """
        recursively crawl inner hyperlinks found depending on the config set depth
        :param driver: Chrome webdriver
        :param next_urls: next URL to be crawled
        :param current_depth: current depth level
        :return:
        """
        next_urls = self.get_filtered_next_urls(next_urls=next_urls)
        res = []
        for entry in next_urls:
            for u_ in entry["next"]:
                if not self.dbm_.check_if_already_visited(url=u_):
                    logging.info("Current root URL: %s \n\t\tCurrent crawling URL: %s", str(entry["root"]), str(u_))
                    res += [{
                        "root": u_,
                        "next": self.crawl_website(driver=driver, url=u_, root=entry["root"],
                                                   current_depth=current_depth)
                    }]
                else:
                    logging.info("Skipping already visited url: %s", u_)
        return res

    def crawler(self, chrome_options: Any, url: str):
        """
        Different information webcrawler is collecting
        :param chrome_options: Chrome Options
        :param url: Current URL to crawl
        """
        # Depending on the config either remote webdriver ist used while using docker or local one
        try:
            if os.environ.get(self.config_["docker"]["env_var"], False):
                cap = chrome_options.to_capabilities()
                cap['javascriptEnabled'] = True
                driver = webdriver.Remote(self.config_["docker"]["uri"], cap)
            else:
                driver = webdriver.Chrome(chrome_options=chrome_options,
                                          executable_path=self.config_["chrome"]["driver_path"])
            if self.config_["chrome"]["max_window_size"]:
                driver.maximize_window()
            next_urls = [{
                "root": url,
                "next": self.crawl_website(driver=driver, url=url, root="input_file",
                                           current_depth=self.config_["crawler"]["depth"])
            }]
            current_depth = self.config_["crawler"]["depth"]
            while current_depth > 0:
                current_depth -= 1
                logging.info("Remaining crawling depth: %s", str(current_depth))
                if next_urls:
                    next_urls = self.recursive_crawl(driver=driver, next_urls=next_urls, current_depth=current_depth)
        except Exception as e:
            logging.info("Crawler Error %s", e)
            logging.info(traceback.format_exc())
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            driver.close()

    def crawl_website(self, driver: Any, url: str, root: str, current_depth: int) -> List[str]:
        """
        Crawl information from given current URL such as the used libraries, technologies and script information and save
        website data in database
        :param driver: Chrome webdriver
        :param url: current URL to crawl
        :param root: parent website or input file
        :param current_depth: current depth level
        :return: hyperlinks from webs
        """
        try:
            collected_website_data = WebsiteData(name=urlparse(url).hostname, url=url, root=root)
            logging.info(
                "\n\n -------------------------------------------- Crawling %s (Remaining Depth Level: %s)"
                " -------------------------------------------- \n ",
                url, str(current_depth))
            driver.get(url)

            # technology and ad tracking information
            wappalyzer_analyzer = WappalyzerAnalyzer(driver=driver, config=self.config_["chrome"]["extension"])
            collected_website_data = wappalyzer_analyzer.get_wappalyzer_info(url_=url, collected_website_data=collected_website_data)
            #time.sleep(0.5)

            collected_website_data.ad_tracking = find_ad_tracking(driver)
            logging.info("Found ad_tracking \t\t %s", str(collected_website_data.ad_tracking.used))
            #time.sleep(0.5)

            # HTML src tag information
            html_extr = HTMLTagExtractor()
            src_lang_analyzer = SrcLanguageAnalyzer(driver=driver)
            script_inner_html, script_src_link, script_type = html_extr.extract_script_tag_attribute_info(
                elements=driver.find_elements_by_tag_name("script"))
            collected_website_data.languages = src_lang_analyzer.get_analysed_src_lang(
                script_inner_html=script_inner_html, script_src=script_src_link, script_type=script_type,
                prev_found_lang=collected_website_data.languages)
            collected_website_data.libraries = src_lang_analyzer.get_analysed_src_lib(
                script_src=script_src_link, prev_found_lib=collected_website_data.libraries)
            logging.info("Found libraries \t\t\t %s", str([i["name"] for i in collected_website_data.libraries]))
            logging.info("Found languages \t\t\t %s", str(collected_website_data.languages))
            logging.info("Found frameworks \t\t\t %s", str([i["name"] for i in collected_website_data.frameworks]))
            driver.get(url)

            webassembly_analyzer = WebAssemblyAnalyzer(driver=driver,
                                                       default_directory_path=self.config_["crawler"]["download.default_directory"])
            # Web Assembly information
            collected_website_data.web_assembly.update_info(
                wasm_res_=webassembly_analyzer.analyze_script_src_for_wasm(script_files=script_src_link))
            logging.info("Found web_assembly \t\t %s", str(collected_website_data.web_assembly.used))
            driver.get(url)

            # link tag information
            # link_tag_data = html_extr.extract_hyperlink_info(self.dbm_, driver.find_elements_by_tag_name("link"))
            # logging.info("Found link_tag_data \t\t %s", str(len(link_tag_data)))

            # HTML hyperlink tag information
            hyperlink_tag_data = html_extr.extract_hyperlink_info(dbm=self.dbm_, elements=driver.find_elements_by_tag_name("a"))
            logging.info("Found hyperlink_tag_data \t %s", str(len(hyperlink_tag_data)))
            collected_website_data.hyperlink = hyperlink_tag_data
        finally:
            logging.info("\t\t\t\t\t\t\t-------->  Finished Crawling of %s. Collected all data", url)
            self.dbm_.insert_data_in_db(data=collected_website_data)
        hrf = [i["href"] for i in collected_website_data.hyperlink if "href" in i.keys()]
        return [i for i in hrf if self.check_url_validity(url_=i)]

    @staticmethod
    def set_up_chrome_options(_config: dict) -> Any:
        """
        Set the chrome options accordingly to the config
        :param _config: general configuration for chrome setup (config.yml)
        :return: Chrome options
        """
        chrome_options = Options()
        chrome_options.add_extension(_config["extension"]["crx_file_path"])
        for argument in _config["arguments"]:
            chrome_options.add_argument(argument)
        chrome_options.add_experimental_option("prefs", _config["prefs"])
        return chrome_options

    def set_default_dir(self):
        if not os.environ.get(self.config_["docker"]["env_var"], False):
            default_directory = os.getcwd() + "\\" + self.config_["crawler"]["download.default_directory"] + "\\"
            self.config_["chrome"]["prefs"]["download.default_directory"] = default_directory
        else:
            default_directory = "/WebCrawler/" + self.config_["crawler"]["download.default_directory"] + "/"
        self.config_["crawler"]["download.default_directory"] = default_directory

    def start_crawler(self):
        """
            Setup of Chrome Configuration
            Start the crawling loop
        """
        logging.getLogger().setLevel(level=logging.INFO)
        executor = ThreadPoolExecutor(self.config_["crawler"]["num_threads"])

        self.set_default_dir()
        chrome_options_ = self.set_up_chrome_options(_config=self.config_["chrome"])

        loop_ = asyncio.get_event_loop()
        input_urls = read_input(path=self.config_["input_file"]["name"],
                                prefix=self.config_["input_file"]["prefix"],
                                suffix=self.config_["input_file"]["suffix"])
        for url_ in input_urls:
            if not self.dbm_.check_if_already_visited(url=url_):
                self.scrape(executor=executor, chrome_options=chrome_options_, url=url_, loop=loop_)
            else:
                logging.info("Skipping already visited url: %s", url_)
        loop_.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop_)))
