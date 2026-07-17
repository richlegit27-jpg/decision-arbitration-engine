import re
import collections

with open("templates/mobile.html", encoding="utf-8") as f:
    text = f.read()

ids = re.findall(r'id="([^"]+)"', text)

for item, count in collections.Counter(ids).items():
    if count > 1:
        print(item, count)