import asyncio
import json
import os
import shutil
from collections import defaultdict
from http.server import HTTPServer, SimpleHTTPRequestHandler

import typer

from .config import base_url, catalog_path, public_path
from .elements import build_element_tree, gather_elements
from .utils import copy_static, download_assets, gather_files, get_template_env

app = typer.Typer()
template_env = get_template_env()

@app.command()
def build():
    index()
    elements()
    element()
    static()
    assets()


@app.command()
def index():
    template = template_env.get_template('index.html')
    xml_files = gather_files(catalog_path)
    elements = gather_elements(xml_files)

    html = template.render(base_url=base_url, elements=elements)
    html_path = public_path / 'index.html'
    html_path.parent.mkdir(exist_ok=True, parents=True)
    html_path.write_text(html)
    html_path.with_suffix('.json').write_text(json.dumps(elements, indent=2))


@app.command()
def elements():
    module_elements = defaultdict(list)
    xml_files = gather_files(catalog_path)
    for element in gather_elements(xml_files):
        module_elements[element['module']].append(element)

    for module, elements in module_elements.items():
        template = template_env.get_template('elements.html')

        html = template.render(base_url=base_url, module=module, elements=elements)
        html_path = public_path / module
        html_path.mkdir(exist_ok=True, parents=True)
        html_path.joinpath('index.html').write_text(html)
        html_path.joinpath('index.json').write_text(json.dumps(elements, indent=2))


@app.command()
def element():
    xml_files = gather_files(catalog_path)
    elements = gather_elements(xml_files)
    elements_by_uri = {element["uri"]: element for element in elements}

    for element in elements:
        if element.get("type") == "catalog":
            tree = build_element_tree(element["uri"], elements_by_uri)
            if tree:
                element["tree"] = tree

        template = template_env.get_template('element.html')

        html = template.render(base_url=base_url, element=element)
        html_path = public_path / element['module'] / element.get('uri_path', element.get('path', ''))
        html_path.mkdir(exist_ok=True, parents=True)
        html_path.joinpath('index.html').write_text(html)
        html_path.with_suffix('.json').write_text(json.dumps(element, indent=2))


@app.command()
def static():
    copy_static(public_path / 'static')


@app.command()
def assets():
    asyncio.run(download_assets(public_path / 'static' / 'assets'))


@app.command()
def clean():
    shutil.rmtree(public_path)


@app.command()
def serve():
    os.chdir(public_path)

    server = HTTPServer(('127.0.0.1', 4000), SimpleHTTPRequestHandler)
    server.serve_forever()
