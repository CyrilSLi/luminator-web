import os, subprocess
from pathlib import Path

abs_path = lambda path: os.path.join(os.path.dirname(__file__), Path(path))

with open(abs_path("../src/index.html")) as f:
    index_html = f.read()

for [src, dest] in (
    ("../src/fonts.json", "FONTS_JSON"),
    ("../src/gif.js", "GIF_JS"),
    ("../src/gif.worker.js", "GIF_WORKER_JS")
):
    with open(abs_path(src)) as f:
        index_html = index_html.replace(f'"%{dest}%"', f.read())

with open(abs_path("../src/index.unmin.html"), "w") as f:
    f.write(index_html)

subprocess.run(["npx", "html-minifier-next", "-v", "-i", abs_path("../src/index.unmin.html"), "-o", abs_path("../index.html"), "-c", abs_path("../scripts/html-minifier-next.config.json")])