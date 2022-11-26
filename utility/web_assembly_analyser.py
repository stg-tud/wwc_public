import base64
import json
import logging
import os
import re
import time
from typing import Any, List, Tuple
from urllib.parse import urlparse
from ppci import wasm
import hashlib
from utility.website_data import WasmFile


class WebAssemblyAnalyzer:
    def __init__(self, driver: Any, default_directory_path: str):
        self.driver = driver
        self.default_directory_path = default_directory_path

    def wait_until_downloaded_wasm_file(self):
        """
        Get to the chrome downloads manager wait until download is complete
        """
        if not self.driver.current_url.startswith("chrome://downloads"):
            self.driver.get("chrome://downloads/")
        self.driver.execute_script('''
            var items = document.querySelector('downloads-manager').shadowRoot.getElementById('downloadsList').items;
            if (items.every(e => e.state === "COMPLETE")) return items.map(e => e.fileUrl || e.file_url);''')

    def delete_unwanted_files(self):
        os.chdir(self.default_directory_path)
        dir_files = sorted(os.listdir(os.getcwd()), key=os.path.getmtime)
        for file in dir_files:
            if "txt" in file:
                os.remove(self.default_directory_path + file)

    def rename_file(self, file_name_: str) -> str:
        """
        Rename the wasm file
        :return: new name of wasm file
        """
        os.chdir(self.default_directory_path)
        dir_files = sorted(os.listdir(os.getcwd()), key=os.path.getmtime)
        if len(dir_files) > 0:
            latest_file_name = dir_files[-1]
            if os.environ.get('RUN_IN_DOCKER_CONTAINER', False):
                old_file_path = os.getcwd() + "/" + file_name_.replace("'", "").replace('"', "")
            else:
                old_file_path = os.getcwd() + "\\" + file_name_.replace("'", "").replace('"', "")
            if os.path.exists(old_file_path):
                new_name = hashlib.sha224(
                    self.read_wasm_file(latest_file_name)).hexdigest() + ".wasm"
                try:
                    os.rename(self.default_directory_path + latest_file_name, new_name)
                    logging.info("\t\t\t\t\t\t\t-------->Renamed file: %s to %s", latest_file_name, new_name)
                    logging.info("\t\t\t\t\t\t\t-------->File %s saved", new_name)
                except Exception as e:
                    logging.info("\t\t\t\t\t\t\t-------->Renaming error %s for: %s to %s", e, latest_file_name, new_name)
                    os.remove(self.default_directory_path + latest_file_name)
                    logging.info("\t\t\t\t\t\t\t-------->Removed possible duplicate %s", latest_file_name)
                return new_name
            else:
                None
        else:
            None

    @staticmethod
    def find_web_assembly_files(_page_source: str, _url: str) -> List[tuple]:
        """
        Find the possible WebAssembly files on the current website
        :param _page_source: plain html of website
        :param _url: current website URL
        :return: wasm files found on page
        """
        wasm_files = []
        if ".wasm" in _page_source:
            wasm_file_names = re.findall(r'[\"\']{1}[a-zA-Z0-9_-]+[.]wasm[\"\']{1}', _page_source)
            if not isinstance(wasm_file_names, list):
                wasm_file_names = [wasm_file_names]
            for file_name in wasm_file_names:
                original_url = re.search(r'.*/', _url).group(0)
                wasm_file_path = original_url + file_name.replace('"', "").replace("'", "")
                wasm_files.append((file_name, wasm_file_path))
        return wasm_files

    @staticmethod
    def find_web_assembly_func(_page_source: str) -> List[str]:
        """
        Find WebAssembly functions used
        :param _page_source:  plain html of website
        :return: WebAssembly functions found
        """
        webassembly_func = []
        if "webassembly" in _page_source.lower():
            webassembly_code_snippet = re.findall(r'\{(.* ?WebAssembly.* ?)\}', _page_source)
            if not isinstance(webassembly_code_snippet, list):
                webassembly_code_snippet = [webassembly_code_snippet]
            for i in webassembly_code_snippet:
                webassembly_func += re.findall(r'WebAssembly[.]\w+', i)
        if "wat" in _page_source.lower():
            print("wat found")
        return webassembly_func

    def read_wasm_file(self, file_name: str) -> bytes:
        """
        read the wasm file content
        :param file_name: file name of wasm file
        :return: byte data from file
        """
        print(os.getcwd())
        os.chdir(self.default_directory_path)
        with open(file_name, 'rb') as f:
            byte_data = f.read()
        return byte_data

    def analyze_wasm_binary(self, file_name: str, wasm_temp: WasmFile) -> Tuple[WasmFile, bool]:
        """
        Analyse the found wasm file
        :param file_name: wasm file name
        :param wasm_temp: current WasmFile
        :return: updated WasmFile
        """
        valid = False
        try:
            module = wasm.Module(self.read_wasm_file(file_name))
            definitions_per_section = module.get_definitions_per_section()
            # module.show_interface()
            information = {
                "file_name": file_name,
                "file size": os.path.getsize(file_name),
                "imports": [(str(import_.kind) + " " + str(import_.modname) + "." + str(import_.name)) for import_ in
                            definitions_per_section["import"]],
                "exports": [(str(export_.kind) + " " + str(export_.name)) for export_ in
                            definitions_per_section["export"]],
                "tables": [{"kind": table_.kind,
                            "min": table_.min,
                            "max": table_.max} for table_ in definitions_per_section["table"]],
                "memory": [{"min": memory_.min,
                            "max": memory_.max} for memory_ in definitions_per_section["memory"]],
                "global": [{"init": global_.init,
                            "mutable": global_.mutable,
                            "typ": global_.typ} for global_ in definitions_per_section["global"]],
                "func": [{"instructions": [{"args": i.args,
                                            "opcode": i.opcode} for i in func_.instructions],
                          "locals": func_.locals} for func_ in definitions_per_section["func"]],
                "type": [{"params": type_.params,
                          "results": type_.results} for type_ in definitions_per_section["type"]],
                "data": [(data_.data, data_.offset) for data_ in definitions_per_section["data"]]
            }
            wasm_temp.file_size = information["file size"]
            wasm_temp.imports = ";".join(information["imports"])
            wasm_temp.exports = ";".join(information["exports"])
            wasm_temp.tables = ";".join(json.dumps(i) for i in information["tables"])
            wasm_temp.memory = ";".join(json.dumps(i) for i in information["memory"])
            wasm_temp.num_global = len(information["global"])
            wasm_temp.num_func = len(information["func"])
            wasm_temp.num_type = len(information["type"])
            valid = True
        except ValueError as e:
            logging.info(e)
        # print(information)
        """
            print(
                "wasm imports:", information["imports"] + \n +
                "wasm exports:", information["exports"] + \n + 
                "wasm tables:", information["tables"] + \n + 
                "wasm memory:", information["memory"] + \n + 
                "wasm global:", information["global"] + \n + 
                "wasm num func:", len(information["func"]), [len(i) for i, _ in information["func"]] + \n + 
                "wasm max func:", max([len(i) for i, _ in information["func"]]) + \n + 
                "wasm min func:", min([len(i) for i, _ in information["func"]]) + \n + 
                "wasm avg func:", np.average([len(i) for i, _ in information["func"]]) + \n + 
                "wasm num type:", len(information["type"]) + \n + 
                "wasm num data sections:", len(information["data"]) + \n + 
                "wasm max data section:", max([len(i) for i, _ in information["data"]]) + \n + 
                "wasm min data section:", min([len(i) for i, _ in information["data"]]) + \n + 
                "wasm avg data section:", np.average([len(i) for i, _ in information["data"]]))
        """
        return wasm_temp, valid

    def analyze_script_src_for_wasm(self, script_files: List[str]) -> List:
        """
        Search the website scripts for wasm files
        :param script_files: found script files
        :return: list of wasm file names
        """
        result = []
        for src_file_link in script_files:
            wasm_files = []
            file_name = os.path.basename(urlparse(src_file_link).path)
            self.driver.get(src_file_link)
            for file_name_, file_path_ in self.find_web_assembly_files(_page_source=self.driver.page_source, _url=src_file_link):
                if file_name_:
                    wasm_temp = WasmFile(source_js_name=file_name, source_js_url=src_file_link)
                    wasm_temp.webassembly_func += self.find_web_assembly_func(self.driver.page_source)
                    wasm_temp.source_wasm_name = file_name_
                    wasm_temp.source_wasm_url = file_path_
                    self.driver.get(file_path_)
                    logging.info("\t\t\t\t\t\t\t-------->Download wasm file: %s from %s", file_name_, file_path_)
                    time.sleep(1)
                    self.wait_until_downloaded_wasm_file()
                    time.sleep(2)
                    local_file_name = self.rename_file(file_name_=file_name_)
                    wasm_temp.wasm_file_local_name = local_file_name
                    if local_file_name:
                        wasm_temp, valid = self.analyze_wasm_binary(file_name=local_file_name, wasm_temp=wasm_temp)
                        if valid:
                            wasm_files.append(wasm_temp)
            if wasm_files:
                result.append(wasm_files)
        self.delete_unwanted_files()
        if os.environ.get('RUN_IN_DOCKER_CONTAINER', False):
            if os.getcwd().split('/')[-2] == self.default_directory_path.split("/")[-2]:
                os.chdir('../')
        else:
            if os.getcwd().split('\\')[-1] == self.default_directory_path.split("\\")[-2]:
                os.chdir('..\\')
        return result
