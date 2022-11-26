from typing import List, Any, Tuple

from guesslang import Guess
from collections import Counter


class SrcLanguageAnalyzer:
    def __init__(self, driver: Any):
        self.driver = driver

    def get_src_inner_html(self, input_src_urls: List[str]) -> Tuple[list, list]:
        """
        Search inner html script for name of js libraries
        :param input_src_urls: list of src urls
        :return: list of inner_html_s and found src_libraries
        """
        inner_html_s = []
        src_libraries = []
        for url in input_src_urls:
            if ".txt" not in url:
                self.driver.get(url)
                if self.driver.page_source:
                    """
                    comments_in_script = [i for i in
                         re.findall(r'/\*+(?:(?!\*/).)*\*+/', driver.page_source.replace("\n", " ").replace("\r", " "))
                         if "\*" in i or "*/" in i]
                    possible_matches = [i for i in [
                        re.findall(r'(([\w\s-]+|version)?[\s:]+v?\d{1,3}[.]\d{1,3}[.]\d{0,3}[\s]|[-\w.]+.js)', i.lower())
                        for i in comments_in_script if "license" in i.lower() or "version" in i.lower()] if i]
                    if possible_matches:
                        print(url, possible_matches)
                    print(url, url.split("/")[-1], url.split("/")[-1].split("?"))
                    """
                    f = url.split("/")[-1].split("?")
                    if f:
                        version = ""
                        name = url.split("/")[-1].split("?")[0]
                        name = name.replace("js", "").replace(".", " ").replace("www", "").replace("-", " ").replace(
                            "_", " ").replace("min", "")
                        if "#" in name:
                            name = name.split("#")[0]
                        name = name.strip().title()
                        if len(f) > 1:
                            if "v" in url.split("/")[-1].split("?")[1]:
                                version = url.split("/")[-1].split("?")[1].split("=")[1].replace("v", "")
                        if name:
                            temp = {
                                "name": name,
                                "category_name": "JavaScript libraries",
                                "version": version,
                                "website": url,
                                "language": "JavaScript",
                                "confidence": "100"
                            }
                            if not name + version in [i["name"] + i["version"] for i in src_libraries]:
                                src_libraries.append(temp)
                    inner_html_s.append((url, self.driver.page_source))
        # print(src_libraries)
        return inner_html_s, src_libraries

    @staticmethod
    def guess_script_language(snippet: str) -> str:
        """
        Guess the src language based on inner html snippet
        :param snippet: code snippet
        :return: guessed language
        """
        guess = Guess()
        # print([guess.probabilities(snippet) for snippet in inner_htmls])
        if snippet:
            return guess.language_name(snippet)
        else:
            return "None"

    def get_analysed_src_lib(self, script_src, prev_found_lib) -> List[dict]:
        """
        Concat prev found libraries with inner html found libraries
        :param script_src: src of libraries
        :param prev_found_lib: previous found src libraries
        :return: all found libs
        """
        _, src_libraries = self.get_src_inner_html(script_src)
        for i in src_libraries:
            if ''.join(filter(str.isalpha, i["name"])).lower() not in \
                   [''.join(filter(str.isalpha, j["name"].replace(".js", "").replace("-js", ""))).lower()
                    for j in prev_found_lib]:
                prev_found_lib += [i]
        return prev_found_lib

    def get_analysed_src_lang(self, script_inner_html: List[str], script_src: List[str], script_type: List[str],
                              prev_found_lang: List[str]) -> List[str]:
        """
        Return all found Src languages on the website and libraries
        :param script_inner_html: found inner html of src tags
        :param script_src: src of libraries
        :param script_type: src tags types
        :param prev_found_lang: previous found src libraries
        :return: all found languages
        """
        src_inner_html, _ = self.get_src_inner_html(script_src)
        found_src = [("innerHTML", self.guess_script_language(i)) for i in script_inner_html if self.guess_script_language(i)] + \
                    [(i, self.guess_script_language(j)) for i, j in src_inner_html if self.guess_script_language(j)]
        languages = Counter([j for i, j in found_src])
        for type_ in script_type + prev_found_lang:
            if languages.keys():
                if type_.lower() not in [i.lower() for i in languages.keys()]:
                    if type_.lower() == "json":
                        languages["JSON"] = 1
                    if type_.lower() == "php":
                        languages["PHP"] = 1
                    if type_.lower() == "typescript":
                        languages["TypeScript"] = 1
                    if type_.lower() not in ["json", "php", "typescript"]:
                        languages[type_.capitalize()] = 1
        result_languages = {}
        for lang in list(languages.keys()):
            result_languages[lang] = {"version": "None", "src": []}
        for src, lang_ in found_src:
            if lang_.lower() in [i.lower() for i in languages.keys()]:
                if src not in result_languages[lang_]["src"]:
                    result_languages[lang_]["src"].append(src)
        return list(result_languages.keys())
