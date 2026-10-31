"""Run inspectable SQL against the full public RetailRocket events file."""
from pathlib import Path
import argparse, datetime, hashlib, json, platform, time
import duckdb

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def run(data_path, db_path=None):
    start = time.perf_counter()
    tables = ROOT/'results/tables'
    tables.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path) if db_path else ':memory:')
    con.execute("SET TimeZone='UTC'")
    con.execute("SET threads=4")
    con.execute("CREATE OR REPLACE TABLE raw AS SELECT * FROM read_csv(?,header=true,all_varchar=true)", [str(data_path)])
    query_receipts=[]
    for path in sorted((ROOT/'sql').glob('*.sql')):
        sql=path.read_text(encoding='utf-8')
        result=con.execute(sql)
        if path.stem=='00_prepare':
            print('Prepared cleaned events, visitors and sessions',flush=True)
            continue
        frame=result.df()
        if path.stem=='10_metric_tree':
            collisions=con.execute("SELECT count(*) FROM (SELECT transaction_id FROM events WHERE event_name='transaction' GROUP BY transaction_id HAVING count(DISTINCT visitor_id)>1)").fetchone()[0]
            if collisions:
                raise ValueError(f'{collisions} transaction IDs belong to multiple visitors; tree would not reconcile')
            for col in ['buyer_reconciliation','segment_reconciliation','order_reconciliation','funnel_reconciliation','frequency_reconciliation']:
                assert frame[col].abs().le(1e-7).all(), col
            distinct_orders=con.execute("SELECT count(DISTINCT transaction_id) FROM events WHERE event_name='transaction'").fetchone()[0]
            assert frame.iloc[0]['orders']==distinct_orders
            weekly=con.execute('SELECT * EXCLUDE(scope) FROM metric_tree_weekly ORDER BY week_start').df()
            weekly.to_csv(tables/'11_metric_tree_weekly.csv',index=False)
            for col in ['buyer_reconciliation','segment_reconciliation','order_reconciliation','funnel_reconciliation','frequency_reconciliation','decomposition_reconciliation']:
                assert weekly[col].dropna().abs().le(1e-7).all(), col
            query_receipts.append({'sql':'sql/10_metric_tree.sql','output':'results/tables/11_metric_tree_weekly.csv','result_rows':len(weekly)})
        frame.to_csv(tables/f'{path.stem}.csv',index=False)
        query_receipts.append({'sql':str(path.relative_to(ROOT)),'sha256':sha256(path),'result_rows':len(frame),'output':f'results/tables/{path.stem}.csv'})
        print(f'{path.stem}: {len(frame)} result rows',flush=True)
    quality=con.execute((ROOT/'sql/01_quality.sql').read_text()).df().iloc[0].to_dict()
    assert quality['raw_rows']==quality['invalid_rows']+quality['exact_duplicates']+quality['clean_rows']
    assert quality['clean_rows']==quality['views']+quality['carts']+quality['transaction_lines']
    assert con.execute('SELECT count(*) FROM visitor_funnel WHERE buy_after_cart_ms IS NOT NULL AND first_cart_ms IS NULL').fetchone()[0]==0
    assert con.execute('SELECT count(*) FROM sessions WHERE ordered_buy_ms IS NOT NULL AND cart_ms IS NULL').fetchone()[0]==0
    retention=con.execute((ROOT/'sql/05_retention.sql').read_text()).df()
    assert (retention.active_visitors<=retention.cohort_size).all()
    assert (retention.loc[retention.week_age==0,'retention_pct']==100).all()
    retention.groupby('week_age')[['cohort_size','active_visitors']].sum().assign(
        retention_pct=lambda x:100*x.active_visitors/x.cohort_size).reset_index().to_csv(tables/'retention_weighted.csv',index=False)
    provenance={'source_url':'https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset',
       'download_url':'https://www.kaggle.com/api/v1/datasets/download/retailrocket/ecommerce-dataset',
       'input_file':str(data_path.relative_to(ROOT)) if data_path.is_relative_to(ROOT) else data_path.name,
       'input_sha256':sha256(data_path),'input_bytes':data_path.stat().st_size,
       'executed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'python':platform.python_version(),'duckdb':duckdb.__version__,'timezone':'UTC',
       'queries':query_receipts,'checks':'quality; nested funnel; retention bounds; metric-tree identities and weekly decomposition; transaction ID uniqueness',
       'seconds':round(time.perf_counter()-start,2)}
    (ROOT/'results/provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
    con.close()
    return provenance

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=ROOT/'data/events.csv.gz')
    parser.add_argument('--db',type=Path)
    args=parser.parse_args()
    print(json.dumps(run(args.data,args.db),ensure_ascii=False,indent=2))
