"""示例爬虫：抓取页面标题与 meta 描述（使用 requests + BeautifulSoup）。
功能改进：
- 支持多种 meta 描述位置（name, property=og:, itemprop 等）和模糊匹配
- 回退到正文首个有意义的 <p> 段落
- 支持命令行参数：URL、--verbose、--save-html、--timeout、--retries
- 在 --verbose 模式下输出状态码、响应长度与编码供排查使用
"""
import argparse
import json
import logging
import os
import sys
import datetime
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SimpleScraper/1.0; +http://www.pbc.gov.cn/rmyh/108976/109428/index.html)"
}


def make_session(retries=3, backoff=0.3):
    s = requests.Session()
    s.headers.update(HEADERS)
    retry = Retry(total=retries, backoff_factor=backoff, status_forcelist=(500, 502, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s


def fetch(url, timeout=10, retries=3, verbose=False):
    s = make_session(retries=retries)
    resp = s.get(url, timeout=timeout)
    if verbose:
        logging.info("Fetched %s -> status=%s, encoding=%s, content-length=%s",
                     url, resp.status_code, resp.encoding, resp.headers.get('Content-Length'))
    resp.raise_for_status()

    # 修正可能错误的编码检测（很多中文站点被误判为 ISO-8859-1）
    content = resp.content
    tried = []
    # 优先使用 requests 提供的 apparent_encoding（如果合理）
    if not resp.encoding or (resp.encoding and resp.encoding.lower() == 'iso-8859-1'):
        enc_candidates = []
        if resp.apparent_encoding:
            enc_candidates.append(resp.apparent_encoding)
        enc_candidates.extend(['utf-8', 'gb18030', 'gbk', 'gb2312'])
        for enc in enc_candidates:
            if not enc or enc in tried:
                continue
            tried.append(enc)
            try:
                # 尝试按候选编码解码字节内容
                content.decode(enc)
                resp.encoding = enc
                break
            except Exception:
                continue

    # 使用修正后的 encoding 来生成文本
    text = content.decode(resp.encoding or 'utf-8', errors='replace')
    return text, resp


def extract_description(soup):
    # 精确匹配优先
    candidates = [
        ("meta", {"name": "description"}),
        ("meta", {"property": "og:description"}),
        ("meta", {"itemprop": "description"}),
        ("meta", {"property": "twitter:description"}),
    ]
    for tag, attrs in candidates:
        m = soup.find(tag, attrs=attrs)
        if m and m.get("content"):
            return m["content"].strip()

    # 模糊匹配：任何 meta 的 name 或 property 包含 'desc'
    for m in soup.find_all("meta"):
        for key in ("name", "property", "itemprop"):
            val = m.get(key)
            if val and "desc" in val.lower() and m.get("content"):
                return m["content"].strip()

    # 回退到正文首个有意义的段落（长度阈值）
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) >= 40:
            return text[:300].strip()

    return ""


def parse(html, verbose=False):
    soup = BeautifulSoup(html, "html.parser")
    # title 优先 og:title，其次 <title>
    title = ""
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()

    description = extract_description(soup)

    if verbose:
        logging.info("Parsed title: %s", title)
        logging.info("Parsed description (len=%s): %s", len(description), (description[:120] + '...') if len(description) > 120 else description)

    return {"title": title, "description": description}


def scrape(url, timeout=10, retries=3, verbose=False, save_html=None):
    html, resp = fetch(url, timeout=timeout, retries=retries, verbose=verbose)

    if save_html:
        try:
            with open(save_html, "w", encoding=resp.encoding or "utf-8") as f:
                f.write(html)
            if verbose:
                logging.info("Saved HTML to %s", save_html)
        except Exception as e:
            logging.warning("Failed to save HTML to %s: %s", save_html, e)

    data = parse(html, verbose=verbose)
    data.update({"url": url, "status_code": resp.status_code})
    return data


def save_to_excel(data, path, verbose=False):
    try:
        import pandas as pd
    except Exception as e:
        raise RuntimeError("pandas 未安装，请运行: python -m pip install -r requirements.txt") from e

    # 带时间戳的行
    row = data.copy()
    row['saved_at'] = datetime.datetime.now()

    # 如果文件存在，读取并追加；否则创建新 DataFrame
    if os.path.exists(path):
        try:
            old = pd.read_excel(path, engine='openpyxl')
            df = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
        except Exception:
            # 读取失败则覆盖
            df = pd.DataFrame([row])
    else:
        df = pd.DataFrame([row])

    # 确保目录存在
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_excel(path, index=False, engine='openpyxl')
    if verbose:
        logging.info("Excel written with %d rows", len(df))


def main(argv=None):
    parser = argparse.ArgumentParser(description="简单网页抓取器：打印 title 与 description")
    parser.add_argument("url", nargs="?", default="https://www.pbc.gov.cn/rmyh/108976/109428/index.html", help="要抓取的 URL（默认 https://www.pbc.gov.cn/rmyh/108976/109428/index.html）")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出调试信息")
    parser.add_argument("--save-html", "-s", help="将抓取到的 HTML 保存到指定文件，便于排查")
    parser.add_argument("--save-excel", "-e", nargs='?', const='', help="将抓取结果保存到 Excel 文件（可选路径；不带值时默认保存到桌面 scrape_results.xlsx）")
    parser.add_argument("--timeout", type=int, default=10, help="请求超时秒数（默认 10）")
    parser.add_argument("--retries", type=int, default=3, help="请求重试次数（默认 3）")

    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        result = scrape(args.url, timeout=args.timeout, retries=args.retries, verbose=args.verbose, save_html=args.save_html)
    except requests.exceptions.RequestException as e:
        logging.error("Request failed: %s", e)
        sys.exit(2)

    # 输出友好的 JSON，保持 unicode
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 可选：保存到 Excel（默认路径为桌面）
    if args.save_excel is not None:
        try:
            save_path = args.save_excel
            # 如果用户只传了 --save-excel 而没有值，argparse 会把它当作 None; we default to Desktop
            if save_path == "":
                # 优先考虑存在的 D:\Desktop（你的自定义路径），否则回退到用户的桌面
                default_desktop = r"D:\Desktop"
                if os.path.exists(default_desktop):
                    save_path = os.path.join(default_desktop, "scrape_results.xlsx")
                else:
                    save_path = os.path.join(os.path.expanduser("~"), "Desktop", "scrape_results.xlsx")
            save_to_excel(result, save_path, verbose=args.verbose)
            if args.verbose:
                logging.info("Saved results to Excel: %s", save_path)
        except Exception as e:
            logging.error("Failed to save to Excel: %s", e)
            sys.exit(3)


if __name__ == "__main__":
    main()
