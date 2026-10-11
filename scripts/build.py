import base64, os, re, subprocess, zlib
from pathlib import Path

abs_path = lambda path: os.path.join(os.path.dirname(__file__), Path(path))
compress_base64 = lambda s: base64.b64encode(zlib.compress(s.encode("utf-8"), 9)).decode("utf-8").replace("+", "-").replace("/", "_").rstrip("=")

with open(abs_path("../src/index.html")) as f:
    index_html = f.read()
    dev_html = index_html



with open(abs_path("../src/fonts.json")) as f:
    fonts_json = f.read()
    dev_html = dev_html.replace('"%FONTS_JSON%"', fonts_json)
    index_html = index_html.replace('"%FONTS_JSON%"', f'JSON.parse(await decompressBase64("{compress_base64(fonts_json)}", true))')

with open(abs_path("../src/gif.js")) as f:
    gif_js = f.read()
    dev_html = dev_html.replace('"%GIF_JS%"', gif_js)
    index_html = index_html.replace('"%GIF_JS%"', '''const script = document.createElement("script");
                script.textContent = await decompressBase64("%GIF_JS%", true);
                document.body.appendChild(script);
                script.remove()'''.replace("%GIF_JS%", compress_base64(gif_js)))

with open(abs_path("../src/gif.worker.js")) as f:
    gif_worker_js = f.read()
    dev_html = dev_html.replace('"%GIF_WORKER_JS%"', f"`{gif_worker_js}`")
    index_html = index_html.replace('"%GIF_WORKER_JS%"', f'await decompressBase64("{compress_base64(gif_worker_js)}")')

index_html = index_html.replace("// %ASYNC_HEADER%", "(async () => {").replace("// %ASYNC_FOOTER%", "})();").replace("/* async */", "async")

with open(abs_path("../src/512kb-club.svg")) as f:
    club_svg = f.read()
    dev_html = dev_html.replace('"%512KB_CLUB%"', f"`{club_svg}`")
    index_html = index_html.replace('"%512KB_CLUB%"', f'await decompressBase64("{compress_base64(club_svg)}", true)')



# Minify template literals in index.html
for m in re.findall(r"(?<=/\* <html> \*/`)[\s\S]*?(?=`/\* <\/html> \*/)", index_html):
    match = m
    layer, end, pos, templates = -1, None, len(match), []
    while pos > 0:
        pos -= 1
        if match[pos] == "}":
            if layer == -1:
                end = pos + 1
                layer = 0
            layer += 1
        elif match[pos] == "{":
            layer -= 1
        if layer == 0:
            templates.append(match[pos-1:end])
            match = match[:pos-1] + f"__template_{len(templates) - 1}__" + match[end:]
            layer = -1
    assert layer == -1

    with open(abs_path("../_template_literal.html"), "w") as f:
        f.write(match)
    subprocess.run(["html-minifier-next", "-i", abs_path("../_template_literal.html"), "-o", abs_path("../_template_literal.html"), "-c", abs_path("../scripts/html-minifier-next.config.json")])
    with open(abs_path("../_template_literal.html")) as f:
        minified = f.read()
    for i, template in enumerate(templates):
        assert f"__template_{i}__" in minified
        minified = minified.replace(f"__template_{i}__", template)

    index_html = index_html.replace(m, minified)
os.remove(abs_path("../_template_literal.html"))



with open(abs_path("../index.dev.html"), "w") as f:
    f.write(dev_html)
with open(abs_path("../src/index.unmin.html"), "w") as f:
    f.write(index_html)

subprocess.run(["html-minifier-next", "-v", "-i", abs_path("../src/index.unmin.html"), "-o", abs_path("../index.html"), "-c", abs_path("../scripts/html-minifier-next.config.json")])