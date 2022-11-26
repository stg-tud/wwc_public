import json
import sqlite3
import logging
import traceback
from datetime import datetime
from typing import Any

from utility.website_data import WebsiteData


class DatabaseManager:
    def __init__(self, set_up: bool, path: str, timeout=10):
        self.c = None
        self.path = path
        self.timeout = timeout
        self.connect()
        logging.info("\t\t\t\t\t\t\t-------->  Init DatabaseManager")
        if set_up:
            self.set_up_tables()
            logging.info("\t\t\t\t\t\t\t-------->  DB setup Tables")
        self.disconnect()

    def connect(self):
        self.c = sqlite3.connect(self.path, timeout=self.timeout, check_same_thread=False)
        # logging.info("\t\t\t\t\t\t\t-------->  Connected DatabaseManager")

    def disconnect(self):
        self.c.commit()
        self.c.close()
        # logging.info("\t\t\t\t\t\t\t-------->  Disconnected DatabaseManager")

    def select(self, select_statement: str, args=None) -> Any:
        """
        execute a SELECT query to the database and return results
        :param select_statement: Select statement
        :param args: possible arguments for querying
        :return: result rows

        examples how to query:
        column_names = dbm.select(select_statement="PRAGMA table_info(Website);")
        rows = dbm.select(select_statement="SELECT * FROM Website WHERE root=?;", args=("input_file",))
        """
        self.connect()
        cur = self.c.cursor()
        if args:
            cur.execute(select_statement, args)
        else:
            cur.execute(select_statement)
        rows = cur.fetchall()
        self.disconnect()
        return rows

    def check_if_already_visited(self, url) -> bool:
        """
        Check if url was already visited before
        :param url: current url to crawl
        :return: bool if true or not
        """
        self.connect()
        cur = self.c.cursor()
        if url[-1] == "/":
            url = url[:-1]
        cur.execute("""SELECT website_id FROM Website WHERE url=?;""", (url,))
        res = cur.fetchall()
        self.disconnect()
        if len(res) > 0:
            return True
        else:
            return False

    def insert_data_in_db(self, data: WebsiteData):
        """
        Insert Website data into the website.
        First check for duplicates in the table either insert data in table and return new id or return id of existing entry.
        :param data: website data
        """
        try:
            self.connect()
            if data.name and data.url and data.libraries != "None" and data.languages != "None" and data.frameworks != "None" and data.hyperlink != "None":
                self.check_if_already_visited_hy(url=data.url)
                hy_ids = [
                    self.check_hy_table(url=i["href"], inner_html=i["innerHTML"], already_visited=i["already_visited"])
                    for i in data.hyperlink if "href" in i.keys()]
                la_ids = [self.check_src_lang_table(name=i) for i in data.languages]
                li_ids = [self.check_library_table(name=i["name"], url=i["website"], category=i["category_name"],
                                                   confidence=i["confidence"], version=i["version"]) for i in
                          data.libraries]
                fr_ids = [self.check_framework_table(name=i["name"], url=i["website"], category=i["category_name"],
                                                     confidence=i["confidence"], version=i["version"]) for i in
                          data.frameworks]
                wa_file_ids = [self.check_web_assembly_file_table(local_file_name=file.wasm_file_local_name,
                                                                  source_file_name=file.source_wasm_name,
                                                                  source_js_name=file.source_js_name,
                                                                  file_size=file.file_size,
                                                                  imports=file.imports,
                                                                  exports=file.exports,
                                                                  tables=file.tables,
                                                                  memory=file.memory,
                                                                  num_global=file.num_global,
                                                                  num_func=file.num_func,
                                                                  num_type=file.num_type)
                               for files in data.web_assembly.wasm_files for file in files]

                wa_func_ids = [self.check_webassemblyFunc_table(function_=fun) for files in data.web_assembly.wasm_files
                               for file in files for fun in file.webassembly_func]

                for wa_func_id in wa_func_ids:
                    for wa_file_id in wa_file_ids:
                        self.check_has_webassemblyFunc_table(web_assembly_func_id=wa_func_id,
                                                             web_assembly_file_id=wa_file_id)

                website_data_id = self.check_website_data_table(name=data.name, url=data.url, root=data.root,
                                                                date=datetime.today().strftime('%Y-%m-%d'))

                self.check_AdTracking_table(used=data.ad_tracking.used,
                                            cookies=data.ad_tracking.cookies,
                                            tracking_pixel=data.ad_tracking.tracking_pixel,
                                            utm_links=data.ad_tracking.utm_links,
                                            website_id_=website_data_id)

                for wa_file_id in wa_file_ids:
                    self.check_web_assembly_table(web_assembly_file_id=wa_file_id, website_id=website_data_id,
                                                  used=data.web_assembly.used, use_case=data.web_assembly.use_case)
                for hy_id in hy_ids:
                    self.check_has_hy_table(website_id=website_data_id, hyperlink_id=hy_id)
                for li_id in li_ids:
                    self.check_contains_lib_table(website_id=website_data_id, library_id=li_id)
                for la_id in la_ids:
                    self.check_implements_lang_table(website_id=website_data_id, language_id=la_id)
                for fr_id in fr_ids:
                    self.check_contains_fra_table(website_id=website_data_id, framework_id=fr_id)

                # print(website_data_id)
                logging.info("\t\t\t\t\t\t\t-------->  Successfully inserted website data for %s", data.url)
        except sqlite3.Error as error:
            logging.info("Database Error %s", error)
        except Exception as ex:
            logging.info("Database Exception %s", ex)
            logging.info(traceback.format_exc())
        self.disconnect()

    def check_if_already_visited_hy(self, url):
        select_cursor = self.c.cursor()
        select_cursor.execute(
            """SELECT hyperlink_id FROM Hyperlink WHERE url=? AND already_visited=?;""", (url, self.get_sql_bool_val(False)))
        res = select_cursor.fetchall()
        if len(res) > 0:
            select_cursor.execute("""UPDATE Hyperlink SET already_visited=? WHERE hyperlink_id=?;""",
                                  (self.get_sql_bool_val(True), res[0][0]))

    def insert_contains_lib(self, website_id: int, library_id: int) -> int:
        ex = self.c.execute("INSERT INTO ContainsLib VALUES (?, ?)", (website_id, library_id))
        return ex.lastrowid

    def insert_has_hy(self, website_id: int, hyperlink_id: int) -> int:
        ex = self.c.execute("INSERT INTO HasHyperlink VALUES (?, ?)", (website_id, hyperlink_id))
        return ex.lastrowid

    def insert_implements_lang(self, website_id: int, language_id: int) -> int:
        ex = self.c.execute("INSERT INTO ImplementsLang VALUES (?, ?)", (website_id, language_id))
        return ex.lastrowid

    def insert_contains_fra(self, website_id: int, framework_id: int) -> int:
        ex = self.c.execute("INSERT INTO ContainsFra VALUES (?, ?)", (website_id, framework_id))
        return ex.lastrowid

    def insert_website_data(self, name: str, url: str, root: str, date: str) -> int:
        ex = self.c.execute("INSERT INTO Website VALUES (NULL, ?, ?, ?, ?)", (name, url, root, date))
        return ex.lastrowid

    def insert_web_assembly_data(self, web_assembly_file_id: int, website_id: int, used: bool, use_case: str) -> int:
        if use_case not in ['None', 'Game', 'Compression', 'Cryptographic Utility', 'Other Application',
                            'Image Processing']:
            use_case = "Unknown"
        ex = self.c.execute("INSERT INTO WebAssembly VALUES (NULL, ?, ?, ? ,?)", (web_assembly_file_id, website_id, self.get_sql_bool_val(used), use_case))
        return ex.lastrowid

    def insert_library_data(self, name: str, url: str, category: str, version: str, confidence: float) -> int:
        ex = self.c.execute("INSERT INTO Library VALUES (NULL, ?, ?, ?, ?, ?)",
                            (name, category, url, version, confidence))
        return ex.lastrowid

    def insert_framework_data(self, name: str, url: str, category: str, version: str, confidence: float) -> int:
        ex = self.c.execute("INSERT INTO Framework VALUES (NULL, ?, ?, ?, ?, ?)",
                            (name, category, url, version, confidence))
        return ex.lastrowid

    def insert_src_language_data(self, name: str) -> int:
        ex = self.c.execute("INSERT INTO SrcLanguage VALUES (NULL, ?)", (name,))
        return ex.lastrowid

    def insert_hyperlink_data(self, inner_html: str, url: str, already_visited: bool) -> int:
        ex = self.c.execute("INSERT INTO Hyperlink VALUES (NULL, ?, ?, ?)",
                            (inner_html, url, self.get_sql_bool_val(already_visited)))
        return ex.lastrowid

    def insert_has_webassemblyFunc(self, web_assembly_func_id: int, web_assembly_file_id: int) -> int:
        ex = self.c.execute("INSERT INTO HasWebAssemblyFunction VALUES (?, ?)",
                            (web_assembly_func_id, web_assembly_file_id))
        return ex.lastrowid

    def insert_webassemblyFunc(self, function_: str) -> int:
        ex = self.c.execute("INSERT INTO WebAssemblyFunction VALUES (NULL, ?)", (function_,))
        return ex.lastrowid

    def insert_web_assembly_file_data(self, local_file_name: str, source_file_name: str, source_js_name: str,
                                      file_size: int, imports: str, exports: str, tables: str,
                                      memory: str, num_global: int, num_func: int, num_type: int) -> int:
        ex = self.c.execute("INSERT INTO WebAssemblyFile VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (local_file_name, source_file_name, source_js_name, file_size, imports, exports,
                             tables, memory, num_global, num_func, num_type))
        return ex.lastrowid

    def insert_adTracking(self, used: bool, cookies: str, tracking_pixel: str, utm_links: str, website_id_: int) -> int:
        ex = self.c.execute("INSERT INTO AdTracking VALUES (NULL, ?, ?, ?, ?, ?)", (self.get_sql_bool_val(used),
                                                                                    cookies, tracking_pixel, utm_links,
                                                                                    website_id_))
        return ex.lastrowid

    @staticmethod
    def get_sql_bool_val(val_: bool) -> int:
        """
        Convert boolean in to integer as SQLite does not support boolean values
        :param val_: boolean value
        :return: integer value
        """
        if val_:
            return 1
        else:
            return 0

    @staticmethod
    def check_if_null(val_: Any) -> str:
        """
        Check if a entry vale is None or not and add accordingly to SELECT statement
        :param val_: input value
        :return: string value
        """
        if val_ is None:
            return " IS NULL"
        else:
            return "=" + str(val_)

    @staticmethod
    def check_duplicates(res: list, func: Any, args: Any) -> int:
        """
        Check if a duplicate exist in a table, return either id of existing entry or insert data and return the id of new entry
        :param res: list of id of entries in the table
        :param func: insert function to insert data into table
        :param args: arguments for the insert function
        :return: row id in database
        """
        if len(res) > 0:
            # print("found id:", res[0][0], "for:", func.__name__)
            return res[0][0]
        else:
            return func(*args)

    def check_hy_table(self, inner_html: str, url: str, already_visited: bool) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute(
            """SELECT hyperlink_id FROM Hyperlink WHERE url=? AND inner_html=?;""",
            (url, inner_html))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_hyperlink_data, args=(inner_html, url, already_visited))

    def check_src_lang_table(self, name: str) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute("""SELECT src_language_id FROM SrcLanguage WHERE name_=?;""", (name,))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_src_language_data, args=(name,))

    def check_library_table(self, name: str, url: str, category: str, version: str, confidence: float) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute(
            """SELECT library_id FROM Library WHERE name_=? AND url=? AND category=? AND version=? AND confidence=?;""",
            (name, url, category, version, confidence))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_library_data, args=(name, url, category, version, confidence))

    def check_framework_table(self, name: str, url: str, category: str, version: str, confidence: float) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute(
            """SELECT framework_id FROM Framework WHERE name_=? AND url=? AND category=? AND version=? AND confidence=?;""",
            (name, url, category, version, confidence))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_framework_data, args=(name, url, category, version, confidence))

    def check_web_assembly_table(self, web_assembly_file_id: int, website_id: int, used: bool, use_case: str) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute(
            """SELECT web_assembly_id FROM WebAssembly WHERE web_assembly_file_id=? AND website_id=? AND used=? AND use_case=? ;""",
            (web_assembly_file_id, website_id, self.get_sql_bool_val(used), use_case))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_web_assembly_data, args=(web_assembly_file_id, website_id,
                                                                                        used, use_case))

    def check_web_assembly_file_table(self, local_file_name: str, source_file_name: str, source_js_name: str,
                                      file_size: int, imports: str, exports: str, tables: str, memory: str, num_global: int,
                                      num_func: int, num_type: int) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute(
            """SELECT web_assembly_file_id FROM WebAssemblyFile WHERE local_file_name=? AND source_file_name=? AND 
            source_js_name=? AND file_size=? AND imports=? AND exports=? AND tables=? AND memory=? AND num_global=? AND
            num_func=? AND num_type=?;""", (local_file_name, source_file_name, source_js_name, file_size, imports,
                                            exports, tables, memory, num_global, num_func, num_type))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_web_assembly_file_data,
                                     args=(local_file_name, source_file_name, source_js_name, file_size,
                                           imports, exports, tables, memory, num_global, num_func, num_type))

    def check_website_data_table(self, name: str, url: str, root: str, date: str) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute("""SELECT website_id FROM Website WHERE name_=? AND url=? AND root=? AND visited=?;""",
                              (name, url, root, date))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_website_data, args=(name, url, root, date))

    def check_contains_lib_table(self, website_id: int, library_id: int) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute("""SELECT * FROM ContainsLib WHERE website_id=? AND library_id=?;""",
                              (website_id, library_id))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_contains_lib, args=(website_id, library_id))

    def check_implements_lang_table(self, website_id: int, language_id: int) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute("""SELECT * FROM ImplementsLang WHERE website_id=? AND language_id=?;""",
                              (website_id, language_id))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_implements_lang, args=(website_id, language_id))

    def check_contains_fra_table(self, website_id: int, framework_id: int) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute("""SELECT * FROM ContainsFra WHERE website_id=? AND framework_id=?;""",
                              (website_id, framework_id))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_contains_fra, args=(website_id, framework_id))

    def check_has_hy_table(self, website_id: int, hyperlink_id: int) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute("""SELECT * FROM HasHyperlink WHERE website_id=? AND hyperlink_id=?;""",
                              (website_id, hyperlink_id))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_has_hy, args=(website_id, hyperlink_id))

    def check_has_webassemblyFunc_table(self, web_assembly_func_id: int, web_assembly_file_id: int) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute(
            """SELECT * FROM HasWebAssemblyFunction WHERE web_assembly_func_id=? AND web_assembly_file_id=?;""",
            (web_assembly_func_id, web_assembly_file_id))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_has_webassemblyFunc,
                                     args=(web_assembly_func_id, web_assembly_file_id))

    def check_webassemblyFunc_table(self, function_: str) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute("""SELECT * FROM WebAssemblyFunction WHERE function_=?;""", (function_,))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_webassemblyFunc, args=(function_,))

    def check_AdTracking_table(self, used: bool, cookies: str, tracking_pixel: str, utm_links: str, website_id_: int) -> int:
        select_cursor = self.c.cursor()
        select_cursor.execute("""SELECT * FROM AdTracking WHERE used=? AND cookies=? AND tracking_pixel=? AND utm_links=? AND 
        website_id_=?;""", (self.get_sql_bool_val(used), cookies, tracking_pixel, utm_links, website_id_))
        res = select_cursor.fetchall()
        return self.check_duplicates(res=res, func=self.insert_adTracking, args=(used, cookies, tracking_pixel,
                                                                                 utm_links, website_id_))

    def set_up_tables(self):
        self.c.execute('''CREATE TABLE IF NOT EXISTS Website (
                           website_id INTEGER PRIMARY KEY,
                           name_ TEXT,
                           url TEXT,
                           root TEXT,
                           visited TEXT,
                           unique (name_, url, root));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS WebAssembly (
                           web_assembly_id INTEGER PRIMARY KEY,
                           web_assembly_file_id INTEGER,
                           website_id INTEGER,
                           used INTEGER,
                           use_case TEXT CHECK(use_case IN ('None', 'Game','Compression','Cryptographic Utility','Other Application', 'Image Processing')) NOT NULL DEFAULT 'Unknown',
                           FOREIGN KEY(website_id) REFERENCES Website(website_id),
                           FOREIGN KEY(web_assembly_file_id) REFERENCES WebAssemblyFile(web_assembly_file_id),
                           unique (web_assembly_file_id, website_id, used, use_case));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS WebAssemblyFile (
                           web_assembly_file_id INTEGER PRIMARY KEY,
                           local_file_name TEXT,
                           source_file_name TEXT,
                           source_js_name TEXT,
                           file_size INTEGER,
                           imports TEXT,
                           exports TEXT,
                           tables TEXT,
                           memory TEXT,
                           num_global INTEGER,
                           num_func INTEGER,
                           num_type INTEGER,
                           unique (local_file_name, source_file_name, source_js_name));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS WebAssemblyFunction (
                           web_assembly_func_id INTEGER PRIMARY KEY,
                           function_ TEXT,
                           unique (function_));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS Hyperlink (
                           hyperlink_id INTEGER PRIMARY KEY,
                           inner_html TEXT,
                           url TEXT,
                           already_visited INTEGER,
                           unique (inner_html, url));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS SrcLanguage (
                           src_language_id INTEGER PRIMARY KEY,
                           name_ TEXT unique);
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS Library (
                           library_id INTEGER PRIMARY KEY,
                           name_ TEXT,
                           category TEXT,
                           url TEXT,
                           version TEXT, 
                           confidence INTEGER,
                           unique (name_, url, category, version, confidence));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS ContainsLib (
                           website_id INTEGER,
                           library_id INTEGER,
                           PRIMARY KEY (website_id, library_id),
                           unique (website_id, library_id));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS Framework (
                           framework_id INTEGER PRIMARY KEY,
                           name_ TEXT,
                           category TEXT,
                           url TEXT,
                           version TEXT, 
                           confidence INTEGER,
                           unique (name_, url, category, version, confidence));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS ContainsFra (
                           website_id INTEGER,
                           framework_id INTEGER,
                           PRIMARY KEY (website_id, framework_id),
                           unique (website_id, framework_id));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS ImplementsLang (
                           website_id INTEGER,
                           language_id INTEGER,
                           PRIMARY KEY (website_id, language_id),
                           unique (website_id, language_id));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS HasHyperlink (
                           website_id INTEGER,
                           hyperlink_id INTEGER,
                           PRIMARY KEY (website_id, hyperlink_id),
                           unique (website_id, hyperlink_id));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS HasWebAssemblyFunction (
                           web_assembly_func_id INTEGER,
                           web_assembly_file_id INTEGER,
                           PRIMARY KEY (web_assembly_func_id, web_assembly_file_id),
                           unique (web_assembly_func_id, web_assembly_file_id));
                           ''')

        self.c.execute('''CREATE TABLE IF NOT EXISTS AdTracking (
                           ad_tracking_id_ INTEGER PRIMARY KEY,
                           used INTEGER,
                           cookies TEXT,
                           tracking_pixel TEXT,
                           utm_links TEXT,
                           website_id_ INTEGER,
                           FOREIGN KEY(website_id_) REFERENCES Website(website_id),
                           unique (used, cookies, tracking_pixel, utm_links, website_id_));
                           ''')
