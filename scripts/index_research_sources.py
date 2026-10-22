from dfs_optimizer.src.research_source_catalog import source_register
from dfs_optimizer.src.research_ingestion import crawl_source_graph, write_source_graph

if __name__ == '__main__':
    sources=source_register()
    # Respect known restrictions: no automated crawl of Football-Data.co.uk or RotoGrinders.
    blocked=('football-data.co.uk','rotogrinders.com')
    seeds=[s['url'] for s in sources if s['url'].startswith('https://') and not any(host in s['url'] for host in blocked) and not s['url'].lower().endswith('.pdf')]
    result=crawl_source_graph(seeds,max_pages=30,max_depth=2)
    write_source_graph(result,'research_source_graph.json')
    print(f"Indexed {result['pages_indexed']} pages across {len(result['allowed_hosts'])} allowlisted source hosts.")
    print("This is link discovery and metadata only; manually review source content, license and citations before implementing claims.")
