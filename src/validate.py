"""Independent pandas recomputation and deterministic edge-case SQL fixtures."""
from pathlib import Path
import json
import duckdb, pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def fixture_checks():
    con=duckdb.connect()
    base=int(pd.Timestamp('2015-05-04',tz='UTC').timestamp()*1000)
    rows=[(base,1,'view',10,None),(base+1,1,'addtocart',10,None),(base+2,1,'transaction',10,1),
       (base,2,'addtocart',10,None),(base+1,2,'view',10,None),(base+2,2,'transaction',10,2),
       (base,3,'view',10,None),(base,3,'addtocart',10,None),(base,3,'transaction',10,3),
       (base,4,'view',10,None),(base+1,4,'addtocart',11,None),(base+2,4,'transaction',11,4),
       (base,1,'view',10,None), # one exact duplicate
       (base+1800003,1,'view',12,None), # second session, gap >30m
       (base+7*86400000,1,'view',10,None), # retained in week one
       (base+14*86400000,5,'view',10,None)] # final week incomplete
    df=pd.DataFrame(rows,columns=['timestamp','visitorid','event','itemid','transactionid'])
    con.register('fixture',df)
    con.execute('CREATE TABLE raw AS SELECT * FROM fixture')
    con.execute((ROOT/'sql/00_prepare.sql').read_text())
    assert con.execute('SELECT count(*) FROM visitor_funnel WHERE buy_after_cart_ms IS NOT NULL').fetchone()[0]==2
    assert len(rows)==16
    assert con.execute('SELECT count(*) FROM events').fetchone()[0]==15
    sensitivity=con.execute((ROOT/'sql/03_funnel_sensitivity.sql').read_text()).df().set_index('definition')
    assert sensitivity.loc['strict_same_item','buyer_visitors']==1
    assert sensitivity.loc['nondecreasing_cross_item','buyer_visitors']==3
    assert con.execute('SELECT count(*) FROM sessions WHERE visitor_id=1').fetchone()[0]==3
    cohort=con.execute((ROOT/'sql/05_retention.sql').read_text()).df()
    assert set(cohort.week_age)=={0,1}
    assert cohort.loc[cohort.week_age==1,'active_visitors'].iloc[0]==1
    assert cohort.cohort_size.iloc[0]==4
    return ['same-timestamp order','cart before view','cross-item vs same-item','exact duplicate','30-minute session boundary','immature cohort exclusion']

def independent_checks(path):
    data=pd.read_csv(path,dtype={'timestamp':'int64','visitorid':'int64','event':'category','itemid':'int64','transactionid':'Int64'})
    # All input records pass the required-field/domain checks in this dataset, verify rather than assume.
    assert data[['timestamp','visitorid','itemid','event']].notna().all().all()
    assert (data.timestamp>0).all() and (data.visitorid>=0).all() and (data.itemid>=0).all()
    assert data.event.isin(['view','addtocart','transaction']).all()
    assert data.loc[data.event=='transaction','transactionid'].notna().all()
    clean=data.drop_duplicates()
    quality=pd.read_csv(ROOT/'results/tables/01_quality.csv').iloc[0]
    assert len(data)==quality.raw_rows and len(clean)==quality.clean_rows
    assert len(data)-len(clean)==quality.exact_duplicates
    views=clean[clean.event=='view'].groupby('visitorid',observed=True).timestamp.min()
    carts=clean[clean.event=='addtocart'].join(views.rename('first_view'),on='visitorid')
    carts=carts[carts.timestamp>carts.first_view].groupby('visitorid',observed=True).timestamp.min()
    purchases=clean[clean.event=='transaction'].join(carts.rename('first_cart'),on='visitorid')
    buyers=purchases.loc[purchases.timestamp>purchases.first_cart,'visitorid'].nunique()
    funnel=pd.read_csv(ROOT/'results/tables/02_funnel.csv')
    assert [len(views),len(carts),buyers]==funnel.visitors.tolist()
    dates=pd.to_datetime(clean.timestamp,unit='ms',utc=True).dt.tz_localize(None)
    clean=clean.assign(week=dates.dt.to_period('W-SUN').dt.start_time)
    first_week=clean.groupby('visitorid',observed=True).week.min()
    sizes=first_week.value_counts()
    activity=clean[['visitorid','week']].drop_duplicates().join(first_week.rename('cohort_week'),on='visitorid')
    activity['age']=((activity.week-activity.cohort_week).dt.days//7)
    independently_retained=activity.groupby(['cohort_week','age'],observed=True).size()
    result=pd.read_csv(ROOT/'results/tables/05_retention.csv',parse_dates=['cohort_week'])
    for row in result.itertuples():
        assert row.cohort_size==sizes[row.cohort_week]
        assert row.active_visitors==independently_retained.get((row.cohort_week,row.week_age),0)
    # Independently recompute mature 7d first-purchase conversion.
    first=clean.groupby('visitorid',observed=True).timestamp.min()
    first_buy=clean[clean.event=='transaction'].groupby('visitorid',observed=True).timestamp.min()
    eligible=first[first+604800000<=clean.timestamp.max()]
    buy_within=first_buy.reindex(eligible.index)<eligible+604800000
    activation=pd.read_csv(ROOT/'results/tables/06_activation.csv').iloc[0]
    assert len(eligible)==activation.eligible_7d_visitors and buy_within.sum()==activation.buyers_7d
    # Rebuild sessions independently using pandas gaps rather than SQL window functions.
    session_data=clean.sort_values(['visitorid','timestamp'],kind='stable').copy()
    gaps=session_data.groupby('visitorid',observed=True).timestamp.diff()
    session_data['sid']=(gaps.isna() | (gaps>1800000)).cumsum()
    first_sid=session_data.groupby('visitorid',observed=True).sid.min()
    session_view=session_data[session_data.event=='view'].groupby('sid').timestamp.min()
    cart_events=session_data[session_data.event=='addtocart'].join(session_view.rename('view_ms'),on='sid')
    session_cart=cart_events[cart_events.timestamp>cart_events.view_ms].groupby('sid').timestamp.min()
    purchase_events=session_data[session_data.event=='transaction'].join(session_cart.rename('cart_ms'),on='sid')
    session_buy=purchase_events.loc[purchase_events.timestamp>purchase_events.cart_ms,'sid'].unique()
    summary=session_data.groupby('sid').visitorid.first().to_frame().join(first_sid.rename('first_sid'),on='visitorid')
    summary['segment']=summary.index.to_series().eq(summary.first_sid).map({True:'first_observed',False:'returning_observed'})
    summary['has_view']=summary.index.isin(session_view.index)
    summary['ordered_buy']=summary.index.isin(session_buy)
    session_results=pd.read_csv(ROOT/'results/tables/04_sessions.csv').set_index('segment')
    for segment,part in summary.groupby('segment'):
        assert len(part)==session_results.loc[segment,'sessions']
        assert part.has_view.sum()==session_results.loc[segment,'viewing_sessions']
        assert part.ordered_buy.sum()==session_results.loc[segment,'ordered_buy_sessions']
    # Product-level independent recomputation for every shipped high-traffic item.
    products=pd.read_csv(ROOT/'results/tables/07_products.csv')
    product_data=clean[clean.itemid.isin(products.item_id)]
    product_view=product_data[product_data.event=='view'].groupby(['visitorid','itemid'],observed=True).timestamp.min()
    product_cart=product_data[product_data.event=='addtocart'].join(product_view.rename('view_ms'),on=['visitorid','itemid'])
    product_cart=product_cart[product_cart.timestamp>product_cart.view_ms].groupby(['visitorid','itemid'],observed=True).timestamp.min()
    product_buy=product_data[product_data.event=='transaction'].join(product_cart.rename('cart_ms'),on=['visitorid','itemid'])
    product_buy=product_buy[product_buy.timestamp>product_buy.cart_ms].groupby(['visitorid','itemid'],observed=True).timestamp.min()
    product_any_buy=product_data[product_data.event=='transaction'].join(product_view.rename('view_ms'),on=['visitorid','itemid'])
    product_any_buy=product_any_buy[product_any_buy.timestamp>product_any_buy.view_ms].groupby(['visitorid','itemid'],observed=True).timestamp.min()
    def counts_per_item(series):return series.reset_index().groupby('itemid').visitorid.nunique()
    pv,pc,pb,pa=[counts_per_item(x) for x in [product_view,product_cart,product_buy,product_any_buy]]
    for row in products.itertuples():
        assert row.viewing_visitors==pv.get(row.item_id,0)
        assert row.cart_visitors==pc.get(row.item_id,0)
        assert row.buying_visitors==pb.get(row.item_id,0)
        assert row.buyers_after_view==pa.get(row.item_id,0)
    return {'raw_rows':len(data),'clean_rows':len(clean),'funnel':funnel.visitors.tolist(),
      'retention_cells_checked':len(result),'eligible_7d_visitors':len(eligible),'buyers_7d':int(buy_within.sum()),
      'sessions_checked':len(summary),'products_checked':len(products)}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=ROOT/'data/events.csv.gz');args=p.parse_args()
    result={'fixture_checks':fixture_checks(),'independent_pandas':independent_checks(args.data),'status':'passed'}
    (ROOT/'results/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))
