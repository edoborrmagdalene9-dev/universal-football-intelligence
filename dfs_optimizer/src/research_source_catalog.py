"""Research source register. This is a bibliography and crawl policy, not a claim of exhaustive ingestion."""
SOURCES = [
 {"name":"Hunter et al. (2016) DFS integer programming","url":"https://arxiv.org/abs/1604.01455","type":"paper","use":"integer programming/DFS portfolio formulation","ingestion":"reference registered; read and verify before implementation"},
 {"name":"Grody et al. (2024) DFS linear programming","url":"https://arxiv.org/abs/2411.11012","type":"paper","use":"DFS optimization","ingestion":"reference registered; verify metadata and methods"},
 {"name":"Hall et al. (2019) stochastic DFS portfolio","url":"http://www.columbia.edu/~mh2078/DFS_Revision_1_May2019.pdf","type":"paper","use":"stochastic portfolio/Dirichlet copula","ingestion":"PDF reference registered; requires document extraction and method review"},
 {"name":"Dixon & Coles football score model","url":"https://doi.org/10.1111/1467-9876.00065","type":"paper","use":"low-score correction/time-weighted football score model","ingestion":"implemented model; must validate against source and holdout data"},
 {"name":"Dixon-Coles implementation tutorial","url":"https://dashee87.github.io/football/python/predicting-football-results-with-statistical-modelling-dixon-coles-and-time-weighting/","type":"tutorial","use":"implementation cross-check","ingestion":"reference registered"},
 {"name":"PredictionEngine Dixon-Coles guide","url":"https://predictionengine.app/learn/dixon-coles-soccer-model","type":"tutorial","use":"model engineering cross-check","ingestion":"reference registered"},
 {"name":"Optionally Bayes DFS integer programming","url":"https://optionallybayes.com/posts/intprog_dfs/","type":"tutorial","use":"integer programming formulation","ingestion":"reference registered"},
 {"name":"RotoGrinders ownership/leverage","url":"https://rotogrinders.com/articles/dfs-strategy-predicting-ownership-1360237","type":"article","use":"ownership projection concepts","ingestion":"reference registered; terms may restrict automated access"},
 {"name":"StatsBomb Open Data","url":"https://github.com/statsbomb/open-data","type":"dataset","use":"selected match/event/lineup records","ingestion":"connector implemented for public repository; coverage selective"},
 {"name":"OpenFootball","url":"https://github.com/openfootball","type":"dataset","use":"open historical fixtures/results","ingestion":"manual/provider integration; inspect license and season coverage"},
 {"name":"Football-Data.co.uk","url":"https://www.football-data.co.uk/data.php","type":"dataset","use":"historical scores/odds/basic stats","ingestion":"manual download only unless current terms explicitly authorize automation; site notes restrict AI/bot use"},
 {"name":"PuLP guide","url":"https://benalexkeen.com/linear-programming-with-python-and-pulp-part-2/","type":"tutorial","use":"linear integer programming","ingestion":"reference registered"},
 {"name":"Unified football data ingestion gist","url":"https://gist.github.com/hungson175/b804219579b3c3f6deb53dd0421d071a","type":"code","use":"data ingestion architecture","ingestion":"reference registered"},
 {"name":"Open-Meteo API","url":"https://open-meteo.com/en/docs","type":"api","use":"weather forecast/reanalysis","ingestion":"live connector implemented; CC BY 4.0 attribution and terms apply"},
 {"name":"scikit-learn isotonic regression","url":"https://scikit-learn.org/stable/modules/generated/sklearn.isotonic.IsotonicRegression.html","type":"documentation","use":"probability calibration","ingestion":"library implementation used"},
]
def source_register():
    return [dict(x) for x in SOURCES]
