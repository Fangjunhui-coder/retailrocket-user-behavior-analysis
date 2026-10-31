from pathlib import Path
import duckdb
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

def test_metric_tree_and_weekly_decomposition():
    # Two complete weeks, plus boundary events establishing the observation span.
    rows = [
        ('2015-05-03', 90, 'view', 1, None),
        ('2015-05-04 01:00', 1, 'view', 1, None),
        ('2015-05-04 02:00', 1, 'addtocart', 1, None),
        ('2015-05-04 03:00', 1, 'transaction', 1, 1),
        ('2015-05-05', 2, 'transaction', 1, 2),
        ('2015-05-06', 2, 'transaction', 1, 3),
        ('2015-05-11 01:00', 3, 'view', 1, None),
        ('2015-05-11 02:00', 3, 'addtocart', 1, None),
        ('2015-05-11 03:00', 3, 'transaction', 1, 4),
        ('2015-05-12', 4, 'transaction', 1, 5),
        ('2015-05-13', 5, 'transaction', 1, 6),
        ('2015-05-18', 91, 'view', 1, None),
    ]
    df=pd.DataFrame(rows, columns=['date','visitorid','event','itemid','transactionid'])
    df['timestamp']=(pd.to_datetime(df.pop('date'),utc=True,format='mixed').astype('int64')//10**6)
    con=duckdb.connect(); con.register('raw',df)
    con.execute((ROOT/'sql/00_prepare.sql').read_text())
    overall=con.execute((ROOT/'sql/10_metric_tree.sql').read_text()).df().iloc[0]
    weeks=con.execute('select * from metric_tree_weekly order by week_start').df()
    assert overall.orders == 6
    assert overall.strict_buyers == 2 and overall.other_buyers == 3
    assert overall.single_buyers == 4 and overall.repeat_buyers == 1
    assert overall.repeat_orders == 2
    assert overall.order_reconciliation == pytest.approx(0)
    assert overall.buyer_reconciliation == 0
    w=weeks[weeks.week_start.astype(str)=='2015-05-11'].iloc[0]
    assert bool(w.is_complete)
    assert w.orders == 3 and w.order_change == 0
    assert sum(w[x] for x in ['traffic_effect','cart_rate_effect','purchase_rate_effect','other_buyer_effect','repeat_share_effect','repeat_frequency_effect']) == pytest.approx(w.order_change)
    assert w.decomposition_reconciliation == pytest.approx(0)
    assert not bool(weeks.iloc[0].is_complete) and not bool(weeks.iloc[-1].is_complete)

def test_zero_buyer_week_still_decomposes():
    rows=[('2015-05-03',1,'view',1,None),('2015-05-04',2,'view',1,None),
          ('2015-05-11',3,'transaction',1,10),('2015-05-18',4,'view',1,None)]
    df=pd.DataFrame(rows,columns=['date','visitorid','event','itemid','transactionid'])
    df['timestamp']=pd.to_datetime(df.pop('date'),utc=True).astype('int64')//10**6
    con=duckdb.connect();con.register('raw',df)
    con.execute((ROOT/'sql/00_prepare.sql').read_text())
    con.execute((ROOT/'sql/10_metric_tree.sql').read_text())
    row=con.execute("select * from metric_tree_weekly where week_start='2015-05-11'").df().iloc[0]
    assert row.order_change == 1
    assert row.other_buyer_effect == pytest.approx(1)
    assert row.decomposition_reconciliation == pytest.approx(0)
