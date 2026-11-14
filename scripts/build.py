"""Rakentaa sivun: site/template.html + data/deals.json -> dist/index.html"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl = open(os.path.join(ROOT, "site", "template.html"), encoding="utf-8").read()
data = open(os.path.join(ROOT, "data", "deals.json"), encoding="utf-8").read().replace("</", "<\\/")
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
open(os.path.join(ROOT, "dist", "index.html"), "w", encoding="utf-8").write(tpl.replace("__DATA__", data))
print("dist/index.html rakennettu")
