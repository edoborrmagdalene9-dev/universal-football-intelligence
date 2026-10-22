"""Bounded research-link discovery. It does not bypass robots, logins, paywalls or source terms."""
from __future__ import annotations
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
import hashlib, json, time

class _Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.title=[]; self.in_title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag.lower()=="a" and a.get("href"): self.links.append(a["href"])
        if tag.lower()=="title": self.in_title=True
    def handle_endtag(self,tag):
        if tag.lower()=="title": self.in_title=False
    def handle_data(self,data):
        if self.in_title: self.title.append(data.strip())

def crawl_source_graph(seeds, max_pages=30, max_depth=2, delay_seconds=.25, user_agent="UniversalFootballIntelligenceResearch/1.0"):
    """Fetch only HTML pages on seed domains, honor robots.txt, never download PDF/media or crawl external hosts."""
    if not 1<=max_pages<=100 or not 0<=max_depth<=3: raise ValueError("Use max_pages 1..100 and max_depth 0..3")
    normalized=[]
    for raw in seeds:
        url=urldefrag(str(raw))[0]
        if url.startswith("http://"): url="https://"+url[len("http://"):]
        if urlparse(url).scheme!="https" or not urlparse(url).hostname: continue
        normalized.append(url)
    allowed={urlparse(u).hostname.lower() for u in normalized}
    queue=deque((u,0) for u in normalized); seen=set(); rows=[]
    robots_cache={}
    while queue and len(rows)<max_pages:
        url,depth=queue.popleft()
        if url in seen: continue
        seen.add(url); parsed=urlparse(url); host=(parsed.hostname or "").lower()
        if host not in allowed or parsed.scheme!="https": continue
        robots_url=f"https://{host}/robots.txt"
        if host not in robots_cache:
            try:
                req=Request(robots_url,headers={"User-Agent":user_agent})
                with urlopen(req,timeout=8) as resp: robots_text=resp.read(256000).decode("utf-8","replace")
                rp=RobotFileParser(); rp.set_url(robots_url); rp.parse(robots_text.splitlines()); robots_cache[host]=rp
            except Exception:
                robots_cache[host]=None
        rp=robots_cache[host]
        if rp is None or not rp.can_fetch(user_agent,url):
            rows.append({"url":url,"depth":depth,"status":"skipped_robots_or_robots_unavailable","title":"","content_sha256":"","outbound_links":[]})
            continue
        try:
            req=Request(url,headers={"User-Agent":user_agent,"Accept":"text/html,application/xhtml+xml"})
            with urlopen(req,timeout=12) as resp:
                final=resp.geturl(); ctype=resp.headers.get("Content-Type","").lower(); raw=resp.read(2_000_000)
            if urlparse(final).hostname not in allowed:
                rows.append({"url":url,"depth":depth,"status":"redirected_outside_allowlist","title":"","content_sha256":"","outbound_links":[]}); continue
            if "html" not in ctype:
                rows.append({"url":url,"depth":depth,"status":"non_html_metadata_only","title":"","content_sha256":hashlib.sha256(raw).hexdigest(),"outbound_links":[]}); continue
            html=raw.decode("utf-8","replace"); parser=_Links(); parser.feed(html)
            links=[]
            for href in parser.links:
                target=urldefrag(urljoin(final,href))[0]; p=urlparse(target)
                if p.scheme=="http": target="https://"+target[len("http://"):]; p=urlparse(target)
                if p.scheme=="https" and (p.hostname or "").lower() in allowed:
                    links.append(target)
                    if depth<max_depth and target not in seen: queue.append((target,depth+1))
            rows.append({"url":final,"depth":depth,"status":"indexed_html","title":" ".join(parser.title)[:300],"content_sha256":hashlib.sha256(raw).hexdigest(),"outbound_links":sorted(set(links))})
        except Exception as exc:
            rows.append({"url":url,"depth":depth,"status":"fetch_error","error":str(exc)[:300],"title":"","content_sha256":"","outbound_links":[]})
        time.sleep(max(0,float(delay_seconds)))
    return {"seed_count":len(normalized),"allowed_hosts":sorted(allowed),"pages_indexed":len(rows),"max_depth":max_depth,"max_pages":max_pages,"pages":rows,
            "limitations":"Link graph and page metadata only; PDFs, paywalls, restricted sources, outbound domains and mathematical claims require separate authorized/manual review."}

def write_source_graph(result,path="research_source_graph.json"):
    with open(path,"w",encoding="utf-8") as f: json.dump(result,f,indent=2,ensure_ascii=False)
