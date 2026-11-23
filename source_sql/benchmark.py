"""Reproduce the synthetic source-SQL benchmark with Python 3 and SQLite."""
import sqlite3, statistics, time, json, platform
from datetime import date,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent
db=sqlite3.connect(':memory:')
db.execute('CREATE TABLE holdings(mandate_id INTEGER, valuation_date TEXT, security_id INTEGER, value_cents INTEGER)')
start=date(2026,7,1)
def fixture():
    for n in range(120):
        day=(start+timedelta(days=n)).isoformat()
        for mandate in range(1,13):
            for sec in range(200):
                yield mandate,day,sec,100000+mandate*1873+sec*131+n*37
db.executemany('INSERT INTO holdings VALUES (?,?,?,?)',fixture())
params=(7,'2026-09-01','2026-10-01')
original="""SELECT valuation_date, COUNT(*) AS positions, SUM(value_cents) AS total_cents
FROM holdings WHERE mandate_id = ? AND date(valuation_date) >= date(?) AND date(valuation_date) < date(?)
GROUP BY valuation_date ORDER BY valuation_date"""
revised=original.replace('date(valuation_date)','valuation_date').replace('date(?)','?')
def run(sql):
    plan=[r[-1] for r in db.execute('EXPLAIN QUERY PLAN '+sql,params)]
    for i in range(2): result=db.execute(sql,params).fetchall()
    times=[]
    for i in range(9):
        t=time.perf_counter_ns(); result=db.execute(sql,params).fetchall(); times.append(round((time.perf_counter_ns()-t)/1e6,3))
    return {'median_ms':round(statistics.median(times),3),'runs_ms':times,'plan':plan},result
base,a=run(original)
db.execute('CREATE INDEX ix_holdings_mandate_date ON holdings(mandate_id, valuation_date)')
db.execute('ANALYZE')
tuned,b=run(revised)
assert a==b and len(a)==30 and sum(r[1] for r in a)==6000
result=dict(engine='SQLite '+sqlite3.sqlite_version,python=platform.python_version(),rows=288000,median_runs=9,warmups=2,mandate=7,month='2026-09',groups=len(a),positions=sum(r[1] for r in a),equal=a==b,before=base,after=tuned,improvement=round((1-tuned['median_ms']/base['median_ms'])*100,1),sql_before=original,sql_after=revised)
(ROOT/'benchmark_results.json').write_text(json.dumps(result,indent=2))
print('Source SQL benchmark:',base['median_ms'],'ms →',tuned['median_ms'],'ms; exact daily results equal:',a==b)

