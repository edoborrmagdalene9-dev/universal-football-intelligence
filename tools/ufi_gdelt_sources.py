"""Keyless GDELT fallback for source-linked football news research."""
from __future__ import annotations
import json, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from urllib.parse import urlparse

class ArticleMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title_parts=[]
        self.in_title=False
        self.meta={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag.lower()=="title": self.in_title=True
        if tag.lower()=="meta":
            key=(attrs.get("property") or attrs.get("name") or "").lower()
            val=attrs.get("content","")
            if key and val:self.meta[key]=val
    def handle_endtag(self,tag):
        if tag.lower()=="title":self.in_title=False
    def handle_data(self,data):
        if self.in_title and data.strip():self.title_parts.append(data.strip())

def fetch_gdelt_sources(query: str, limit: int=5, timeout: float=8.0) -> list[dict]:
    now=datetime.now(timezone.utc)
    params={"query":query.strip()[:700],"mode":"ArtList","format":"json","maxrecords":str(max(1,min(10,int(limit)*2))),
            "sort":"HybridRel","startdatetime":(now-timedelta(days=7)).strftime("%Y%m%d%H%M%S"),
            "enddatetime":now.strftime("%Y%m%d%H%M%S")}
    req=urllib.request.Request("https://api.gdeltproject.org/api/v2/doc/doc?"+urllib.parse.urlencode(params),
        headers={"Accept":"application/json","User-Agent":"UFI-Source-Research/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        payload=json.loads(response.read().decode("utf-8","replace"))
    articles=payload.get("articles",[]) if isinstance(payload,dict) else []
    results=[];seen=set()
    for article in articles if isinstance(articles,list) else []:
        if not isinstance(article,dict):continue
        url=article.get("url")
        if not isinstance(url,str) or not url.startswith("https://") or url in seen:continue
        host=urlparse(url).hostname or ""
        if not host or host in ("localhost","127.0.0.1") or host.endswith(".local"):continue
        seen.add(url)
        title=str(article.get("title") or "").strip()
        description=""
        published=article.get("seendate") or article.get("date") or ""
        try:
            page_req=urllib.request.Request(url,headers={"Accept":"text/html","User-Agent":"Mozilla/5.0 UFI source metadata fetch"})
            with urllib.request.urlopen(page_req,timeout=timeout) as page:
                html=page.read(600000).decode("utf-8","replace")
            parser=ArticleMetadata();parser.feed(html)
            title=parser.meta.get("og:title") or parser.meta.get("twitter:title") or " ".join(parser.title_parts) or title
            description=parser.meta.get("description") or parser.meta.get("og:description") or parser.meta.get("twitter:description") or ""
            published=parser.meta.get("article:published_time") or parser.meta.get("datepublished") or published
        except Exception:
            pass
        text=" ".join(x for x in [title,description] if x).strip()
        if not text:continue
        results.append({"url":url,"timestamp":str(published or now.isoformat()),"retrieved_at":now.isoformat(),
                        "published_at":published or None,"source_name":article.get("domain") or host,
                        "text":text[:12000],"source_method":"GDELT headline/page metadata"})
        if len(results)>=max(1,min(5,int(limit))):break
    return results
