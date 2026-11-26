"""Downloads Noto Sans (SIL Open Font License) into ./fonts. Runs at build time."""
import os
import urllib.request

BASE = "https://github.com/notofonts/notofonts.github.io/raw/main/fonts/NotoSans/hinted/ttf/"
FILES = ["NotoSans-Regular.ttf", "NotoSans-Bold.ttf"]

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
os.makedirs(out, exist_ok=True)
for name in FILES:
    dest = os.path.join(out, name)
    if not os.path.exists(dest):
        urllib.request.urlretrieve(BASE + name, dest)
    print("ok", dest)
