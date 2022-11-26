import logging
import time
import ast
from typing import Any

import regex as re

from utility.website_data import WebsiteData


class WappalyzerAnalyzer:
    def __init__(self, driver: Any, config: dict):
        self.driver = driver
        self.config = config

    def get_chrome_extension(self):
        """
        Open extensions-manager switch dev mode on and get info from the extension background page
        """
        self.driver.get(self.config["chrome_extensions_url"])
        self.driver.execute_script(
            '''document.querySelector("extensions-manager").delegate.setProfileInDevMode(true)''')
        self.driver.get(self.config["background_page"])
        self.driver.execute_script('''console.log = function(){
                                                   if(JSON.stringify(Array.from(arguments)).includes('"hostname"')){
                                                   document.body.innerHTML += JSON.stringify(Array.from(arguments)); }}''')

    def get_wappalyzer_info(self, url_: str, collected_website_data: WebsiteData) -> WebsiteData:
        """
        Extract the information about used web technologies through wappAlyzer extension
        :param collected_website_data: WebsiteData
        :param url_: current URL
        :return: list of the found wappAlyzer info
        """
        self.driver.switch_to.window(self.driver.window_handles[1])
        self.get_chrome_extension()
        time.sleep(3)
        self.driver.switch_to.window(self.driver.window_handles[0])
        time.sleep(5)
        self.driver.get(url_)
        time.sleep(5)
        self.driver.switch_to.window(self.driver.window_handles[1])
        page_source = self.driver.page_source
        wappalyzer_log_results = re.findall(r'\[\{("hostname":.*?)\].?\]', page_source)
        wappalyzer_libraries = []
        wappalyzer_languages = []
        wappalyzer_frameworks = []
        if wappalyzer_log_results:
            json_string = "{" + wappalyzer_log_results[-1].replace("true", "True").replace("false", "False").replace(
                "null", "None") + "]}"
            try:
                wappalyzer_result = ast.literal_eval(json_string)
                if wappalyzer_result:
                    for tech_entry in wappalyzer_result["technologies"]:
                        slugs = [i["slug"] for i in tech_entry["categories"]]
                        temp = {
                                "name": tech_entry["name"],
                                "slug": tech_entry["slug"],
                                "version": tech_entry["version"],
                                "website": tech_entry["website"],
                                "confidence": tech_entry["confidence"],
                                "category_slug": tech_entry["categories"][0]["slug"],
                                "category_name": tech_entry["categories"][0]["name"],
                                "language": "None"
                            }
                        if 'programming-languages' in slugs:
                            wappalyzer_languages.append(tech_entry["name"])
                        if 'javascript-libraries' in slugs:
                            wappalyzer_libraries.append(temp)
                        if 'javascript-libraries' not in slugs and 'programming-languages' not in slugs:
                            wappalyzer_frameworks.append(temp)
            except Exception as e:
                logging.info("Wappalyzer error %s for %s for json: %s", e, url_, json_string)
        self.driver.switch_to.window(self.driver.window_handles[0])
        collected_website_data.libraries = wappalyzer_libraries
        collected_website_data.languages = wappalyzer_languages
        collected_website_data.frameworks = wappalyzer_frameworks
        return collected_website_data
