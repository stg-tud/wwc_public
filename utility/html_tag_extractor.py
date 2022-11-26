from selenium.webdriver.remote.webelement import WebElement
from typing import List, Tuple
import regex as re

from database.database_manager import DatabaseManager


class HTMLTagExtractor:
    @staticmethod
    def extract_script_tag_attribute_info(elements: List[WebElement]) -> Tuple[list, list, list]:
        """
        Find the information of all script tag on HTML page
        :param elements: found WebElements with script tag
        :return: Found information to the script tag such as inner html, src link and type
        """
        script_inner_html, script_src_link, script_type = [], [], []
        for e in elements:
            if e.get_attribute("innerHTML"):
                script_inner_html.append(e.get_attribute("innerHTML"))
            if e.get_attribute("src"):
                script_src_link.append(e.get_attribute("src"))
            if e.get_attribute("type"):
                if len(e.get_attribute("type").split("/")) > 1:
                    script_type.append(e.get_attribute("type").split("/")[1].lower())
            if e.get_attribute("crossorigin"):
                script_type.append(e.get_attribute("crossorigin"))
        return script_inner_html, script_src_link, script_type

    @staticmethod
    def extract_hyperlink_info(dbm: DatabaseManager, elements: List[WebElement]) -> List[str]:
        """
        Find the information of all "link" and "a" tag on HTML page
        :param dbm: DatabaseManager
        :param elements: found WebElements with "link" and "a" tag
        :return: Found hyperlinks
        """
        found_links = []
        for e in elements:
            if not e.get_attribute("innerHTML"):
                inner_html = "None"
            else:
                inner_html = e.get_attribute("innerHTML")
            temp = {"innerHTML": inner_html}
            for attr in re.findall(r'([a-z]+=)', e.get_attribute("outerHTML")):
                if e.get_attribute(attr[:-1]):
                    temp[attr[:-1]] = e.get_attribute(attr[:-1])
            if "href" in temp.keys():
                temp["already_visited"] = dbm.check_if_already_visited(url=temp["href"])
            found_links.append(temp)
        return found_links

    @staticmethod
    def extract_meta_info(elements: List[WebElement]) -> List[str]:
        """
        Meta data information
        :param elements: found WebElements with "meta" tag
        :return: Found information
        """
        found_meta_data = []
        for e in elements:
            for attr in ["content"]:
                if e.get_attribute(attr):
                    found_meta_data.append(e.get_attribute(attr))
        return found_meta_data
