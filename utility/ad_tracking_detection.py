import json
import re
from typing import List, Any

from selenium.webdriver.remote.webelement import WebElement

from utility.website_data import AdTracking


def get_tracking_pixel_information(elements: List[WebElement]) -> List[str]:
    """
    Find possible tracking pixel information
    :param elements: IMG WebElement
    :return: list of tracking pixel src
    """
    img_src = []
    css_keys = ["width", "height", "display", "visibility"]
    css_vals = ["hidden", "collapse", "none", "0", "1"]
    for i in elements:
        if i.get_attribute("style"):
            for entry in i.get_attribute("style").split(";"):
                if entry:
                    k = entry.split(":")[0].replace(" ", "")
                    v = entry.split(":")[1].replace(" ", "")
                    if k in css_keys and v in css_vals:
                        if i.get_attribute("src") not in img_src:
                            img_src.append(i.get_attribute("src"))
        for k in css_keys:
            if i.get_attribute(k):
                if i.get_attribute(k) in css_vals:
                    if i.get_attribute("src") not in img_src:
                        img_src.append(i.get_attribute("src"))
    res = re.findall(r'^(?!.*(jpg|jpeg|gif|png|tiff|bmp)).*$', "\n".join([str(i).lower() for i in img_src if i]))
    if res:
        return ";".join([str(i) for i in res if i])
    else:
        None


def get_utm_link_information(page_source: str) -> List[str]:
    """
    Find utm links and extract utm_properties
    :param page_source: website page source
    :return: list of found utm data
    """
    utm_info = []
    for utm_link in re.findall(r'[\w\;\?\=\//\?\_\-\&\.\:\\u]+\?utm[\\u\:\.\w\;\?\=\//\?\_\-\&]+', page_source):
        utm_properties = {"original_link": utm_link.split("?")[0]}
        for p in utm_link.split("?")[1].split(";"):
            if len(p.split("=")) > 1:
                utm_properties[p.split("=")[0]] = p.split("=")[1]
        utm_info.append(utm_properties)
    if utm_info:
        return ";".join(json.dumps(i) for i in utm_info)
    else:
        None


def get_tag_manager_information(page_source_: str) -> List[str]:
    tag_manager_info = {
        "google_tag_manager": re.findall(r"<[ a-zA-Z./:\"'?\-=0-9&;]*googletagmanager[ a-zA-Z./:\"'?\-=0-9&;]*>",
                                         page_source_),
        "g_tags": [gtag.replace("(", "").replace(")", "").replace(" ", "").split(",")
                   for gtag in re.findall(r'gtag\(.+\)', page_source_) if "config" in gtag]
    }
    """    "analytic" or "amp-analytics" or "facebook pixel code" or "fbevents"    """
    return tag_manager_info


def find_ad_tracking(driver_: Any) -> AdTracking:
    """
    Extract AdTracking info
    :param driver_: chrome webdriver
    :return: AdTracking information found
    """
    ad_data = AdTracking()
    cookies = driver_.execute_script("""return document.cookie;""")
    tracking_pixel = get_tracking_pixel_information(driver_.find_elements_by_tag_name("img"))
    utm_links = get_utm_link_information(driver_.page_source.lower())
    tag_manager = get_tag_manager_information(driver_.page_source.lower())
    if cookies:
        ad_data.cookies = cookies
    if tracking_pixel:
        ad_data.tracking_pixel = tracking_pixel
    if utm_links:
        ad_data.utm_links = utm_links
    if tag_manager:
        ad_data.tag_manager = tag_manager
    if ad_data.cookies or ad_data.tracking_pixel or ad_data.utm_links or ad_data.tag_manager:
        ad_data.used = True
    return ad_data

