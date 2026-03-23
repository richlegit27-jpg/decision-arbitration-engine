import requests

def search_web(query):
    url = "https://duckduckgo.com/html/"
    params = {"q": query}

    try:
        res = requests.post(url, data=params, timeout=10)
        html = res.text

        results = []

        for line in html.split("\n"):
            if 'class="result__a"' in line:
                try:
                    href = line.split('href="')[1].split('"')[0]
                    title = line.split(">")[1].split("<")[0]

                    results.append({
                        "title": title,
                        "url": href
                    })
                except:
                    continue

            if len(results) >= 5:
                break

        return results

    except Exception as e:
        print("search error:", e)
        return []