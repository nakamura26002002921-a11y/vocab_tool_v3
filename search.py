import argparse
import re
import sys
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

def is_russian_text(text):
    if not text:
        return False
    cyrillic = len(re.findall(r"[А-Яа-яЁё]", text))
    mojibake = len(re.findall(r"[ÐÑÃÂ�]", text))
    return cyrillic > 0 and mojibake <= cyrillic

def clean_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    return " ".join(part for part in text.split() if is_russian_text(part))

def scrape(url, max_words=100, timeout=10):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"    [scrape error] {url}: {e}", file=sys.stderr)
        return ""
    try:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = clean_text(soup.get_text(" ", strip=True))
        return " ".join(text.split()[:max_words])
    except Exception as e:
        print(f"    [parse error] {url}: {e}", file=sys.stderr)
        return ""

def search_and_print(word, max_results=10, max_words=100, timeout=10):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query=word, region="wt-wt", safesearch="moderate", max_results=max_results))
    except Exception as e:
        print(f"[search error] query={word!r}: {e}", file=sys.stderr)
        return
    if not results:
        print(f"[search] no results for {word!r}", file=sys.stderr)
        return
    for i, result in enumerate(results, 1):
        title = result.get("title", "")
        href = result.get("href", "")
        print(f"\n[{i}] {title}")
        print(href)
        if href:
            text = scrape(href, max_words=max_words, timeout=timeout)
            if text:
                print(text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--word", required=True)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--max-words", type=int, default=100)
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()
    search_and_print(args.word, args.max_results, args.max_words, args.timeout)

if __name__ == "__main__":
    main()
