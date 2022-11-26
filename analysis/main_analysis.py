import os
import webbrowser
from typing import List, Any

from database.database_manager import DatabaseManager
from flask import Flask, render_template, request
from redis import Redis

from utility.input_reader import get_config

app = Flask(__name__)
redis = Redis(host='redis', port=6379)


def make_table() -> str:
    """
    :return: HTML for the result table
    """
    return """<table class ="table" style="table-layout: fixed; width: 100%;">
                        {% if columns %}
                            <thead>
                                <tr>
                                    {% for i in columns %}
                                        <th style="text-align: center; vertical-align: middle;" scope="col"> {{ i }}</th>
                                    {% endfor %}   
                                </tr>
                           </thead>
                        {% endif %}
                        {% if rows %}
                           <tbody>
                                <tr>
                                    {% for i in rows %}
                                        <tr style="word-wrap: break-word; overflow-wrap: break-word; ">
                                        {% for j in i %}
                                                <td style="word-wrap: break-word; overflow-wrap: break-word; "> {{ j }} </td>
                                        {% endfor %}
                                        </tr>
                                    {% endfor %}
                                </tr> 
                           </tbody>
                       {% endif %}
                    </table>"""


def make_input_form() -> str:
    """
    :return: HTML for the input form
    """
    return """
            <form action="{{ url_for('index') }}" method="POST">         
                <div class="form-group">
                    <label for='select'>Select statement</label>
                    <textarea class="form-control" name="select" id="select_id" rows="3" placeholder='Enter Select statement (example: "SELECT * FROM Website WHERE root=?;")'>{% if textarea %}{{ textarea }}{% endif %}</textarea>
               </div>
               <input type="submit" name="submit" value="Submit" class="btn btn-primary btn-sm btn-block">
            </form>
            """


def make_html_content(examples: List[str]) -> str:
    """
    Make HTML structure for the form and result table
    :param examples: examples for a select statement for info box
    :return: html string
    """
    return """
        <div class="container">
            <div class="panel panel-default">
                <div class="panel-heading">Examples</div>
                <div class="panel-body" style="font-family: monospace"> """ + "<br>".join(examples) + """</div>
            </div>
            """ + make_input_form() + """
            <div class="panel panel-default" style=" margin-top: 2%; ">
                <div class="panel-body">
                    {% if exception %}
                        {{ exception }}
                    {% endif %}
                    """ + make_table() + """
                </div>
            </div> 
        </div>"""


def add_scripts() -> str:
    """
    :return: scripts used for the HTML
    """
    return """
        <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"></script>
        """


def add_mark(in_: str, color_: str) -> str:
    """
    :param in_: input text
    :param color_: input color
    :return: color highlighted text
    """
    return '<mark style="color:' + color_ + '">' + in_ + '</mark>'


def run_analysis(config_: dict):
    """
    run the flask app for running select statements in local host to access SQlite DB
    :param config_: analysis configuration
    """
    title = "Website Crawler Data Analysis"
    examples = [
        " ".join([add_mark("PRAGMA", "orange"), "table_info(Website)"]),
        " ".join([add_mark("SELECT", "orange"), "name",
                  add_mark("FROM", "orange"), "sqlite_master",
                  add_mark("WHERE", "orange"), "type='table';"]),
        " ".join([add_mark("SELECT", "orange"), add_mark("COUNT(", "red") + "name_" + add_mark(")", "red"),
                  add_mark("FROM", "orange"), "Website",
                  add_mark("WHERE", "orange"), "root='input_file';"]),
        " ".join([add_mark("SELECT", "orange"), "*",
                  add_mark("FROM", "orange"), "Website;"]),
        " ".join([add_mark("SELECT", "orange"), "name_",
                  add_mark("FROM", "orange"), "Framework;"]),
        " ".join([add_mark("SELECT", "orange"), "name_",
                  add_mark("FROM", "orange"), "SrcLanguage;"]),
        " ".join([add_mark("SELECT", "orange"), add_mark("COUNT(", "red") + "Website.website_id" + add_mark(")", "red"),
                  add_mark("FROM", "orange"), "Website",
                  add_mark("LEFT OUTER JOIN", "orange"), "WebAssembly",
                  add_mark("ON", "orange"), "Website.website_id = WebAssembly.website_id",
                  add_mark("WHERE", "orange"),  "WebAssembly.used = 1;"]),
        " ".join([add_mark("SELECT", "orange"), "Website.website_id, Website.name_",
                  add_mark("FROM", "orange"), "Website",
                  add_mark("LEFT OUTER JOIN", "orange"), "WebAssembly",
                  add_mark("ON", "orange"), "Website.website_id = WebAssembly.website_id",
                  add_mark("WHERE", "orange"),  "WebAssembly.used = 1;"]),
        " ".join([add_mark("SELECT", "orange"), "Framework.name_, Framework.framework_id,", add_mark("COUNT(", "red") + "ContainsFra.website_id" + add_mark(")", "red"),
                  add_mark("FROM", "orange"), "ContainsFra",
                  add_mark("INNER JOIN", "orange"), "Framework",
                  add_mark("ON", "orange"), "ContainsFra.framework_id = Framework.framework_id",
                  add_mark("WHERE", "orange"),  "Framework.name_ = 'Vue.js';"]),
        " ".join([add_mark("SELECT", "orange"), "SrcLanguage.name_, SrcLanguage.src_language_id,", add_mark("COUNT(", "red") + "ImplementsLang.website_id" + add_mark(")", "red"),
                  add_mark("FROM", "orange"), "ImplementsLang",
                  add_mark("INNER JOIN", "orange"), "SrcLanguage",
                  add_mark("ON", "orange"), "SrcLanguage.src_language_id = ImplementsLang.language_id",
                  add_mark("WHERE", "orange"),  "SrcLanguage.name_ = 'JavaScript';"])
    ]
    png_name = "DB_model.png"
    html = """ 
            <!doctype html>
            <html lang="en">
              <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
                <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
              </head>
              <body>
                <h1 style="text-align: center; width: 100%; padding: 10px;"> """ + title + """</h1>
                <div style="text-align: center; width: 100%; padding: 10px; display: inline;">
                """ + make_html_content(examples) + """
                </div>""" + add_scripts() + """
                <p style="text-align: center;">
                    <img src="{{url_for('static', filename='""" + png_name + """')}}" width="75%">
                </p>
              </body>
            </html> """

    if os.environ.get('RUN_IN_DOCKER_CONTAINER', False):
        f = open(config_["html_file_dict"] + "\\templates" + "\\" + config_["html_file"], 'w')
    else:
        f = open("templates" + "\\" + config_["html_file"], 'w')
    f.write(html)
    f.close()
    webbrowser.open(config_["url"])
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)


@app.route('/', methods=['GET', 'POST'])
def index():
    rows = False
    columns = False
    exception = False
    textarea = False
    if os.environ.get('RUN_IN_DOCKER_CONTAINER', False):
        config = get_config('config.yml')
        dbm = DatabaseManager(set_up=config["database"]["setup"], path=config["database"]["local_path"])
    else:
        config = get_config('../config.yml')
        dbm = DatabaseManager(set_up=config["database"]["setup"], path="." + config["database"]["local_path"])
    if request.method == 'POST':
        rows, columns, exception, textarea = get_select_data_result(dbm=dbm)
    return render_template(config["analysis"]["html_file"], rows=rows, columns=columns, exception=exception, textarea=textarea)


def get_select_data_result(dbm: DatabaseManager) -> Any:
    """
    Makes a SELECT SQL request and returns the result of that query
    :param dbm: Database Manager
    :return: result rows, result column names, optional also exception message
    """
    select = request.form['select']
    columns = []
    rows = []
    exception = None
    try:
        rows = dbm.select(select_statement=select)
        p = select.replace(";", " ").replace(",", " ").split(" ")
        if p[1] == "*":
            temp = dbm.select(select_statement="PRAGMA table_info(" + p[3] + ");")
            columns = [i[1] for i in temp]
        if p[1] != "*":
            if "FROM" in p:
                temp = p.index("FROM")
                columns = p[1:temp]
    except Exception as e:
        exception = e
    return rows, [i for i in columns if i], exception, select


if __name__ == "__main__":
    """
        Setup Main Configuration
    """
    if os.environ.get('RUN_IN_DOCKER_CONTAINER', False):
        config = get_config('config.yml')
    else:
        config = get_config('../config.yml')
    if config["analysis"]["start"]:
        run_analysis(config_=config["analysis"])
