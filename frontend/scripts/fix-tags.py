"""Fix accidental motion tags -> div tags."""
import os
import re
import sys

root = sys.argv[1] if len(sys.argv) > 1 else "src"
pattern_open = re.compile(r"<motion(\s|>|/)")
pattern_close = re.compile(r"</motion>")

for dp, _, files in os.walk(root):
    for f in files:
        if f.endswith(".tsx"):
            p = os.path.join(dp, f)
            t = open(p, encoding="utf-8").read()
            n = pattern_open.sub(r"<div\1", t)
            n = pattern_close.sub("</div>", n)
            if n != t:
                open(p, "w", encoding="utf-8").write(n)
                print("fixed", p)
