class WebsiteData:
    def __init__(self, name: str, url: str, root: str):
        self.name = name
        self.url = url
        self.root = root
        self.web_assembly = WebAssembly()
        self.libraries = "None"
        self.languages = "None"
        self.frameworks = "None"
        self.hyperlink = "None"
        self.ad_tracking = AdTracking()


class AdTracking:
    def __init__(self):
        self.used = False
        self.cookies = 'None'
        self.tracking_pixel = 'None'
        self.utm_links = 'None'
        self.tag_manager = 'None'


class WebAssembly:
    def __init__(self):
        self.used = False
        self.use_case = 'None'
        self.src_lang = 'None'
        self.wasm_files = []

    def update_info(self, wasm_res_):
        if wasm_res_:
            self.used = True
        self.wasm_files = wasm_res_


class WasmFile:
    def __init__(self, source_js_name, source_js_url):
        self.source_js_name = source_js_name
        self.source_js_url = source_js_url
        self.source_wasm_url = "None"
        self.source_wasm_name = "None"
        self.webassembly_func = []
        self.wasm_file_local_name = "None"
        self.file_size = "None"
        self.imports = "None"
        self.exports = "None"
        self.tables = "None"
        self.memory = "None"
        self.num_global = "None"
        self.num_func = "None"
        self.num_type = "None"
