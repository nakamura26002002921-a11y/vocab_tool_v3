import argparse
import re
import sys
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

def scrape(url, max_chars=3000, timeout=10):
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout).text
    except requests.RequestException as e:
        print(f"    [scrape error] {url}: {e}", file=sys.stderr)
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        return text[:max_chars]
    except Exception as e:
        print(f"    [parse error] {url}: {e}", file=sys.stderr)
        return ""

def search_and_print(word, max_results=10, max_chars=3000, timeout=10):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query=word, region="wt-wt", safesearch="moderate", max_results=max_results))
    except Exception as e:
        print(f"[search error] query={word!r}: {e}", file=sys.stderr)
        return
    if not results:
        print(f"[search] no results for {word!r}", file=sys.stderr)
        return
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        href = r.get("href", "")
        print(f"\n[{i}] {title}")
        print(href)
        if href:
            print(scrape(href, max_chars, timeout))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--max-chars", type=int, default=3000)
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()
    search_and_print(args.word, args.max_results, args.max_chars, args.timeout)

if __name__ == "__main__":
    main()
