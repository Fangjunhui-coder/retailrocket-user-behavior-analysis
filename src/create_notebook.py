"""Create a readable executable companion notebook from the project's modules."""
from pathlib import Path
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
nb=nbf.v4.new_notebook()
nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
nb.cells=[md('''# RetailRocket 电商用户行为与转化分析

## 结果摘要
全量公开数据有 2,756,101 条记录。去除 460 条完全重复记录后，严格顺序浏览→加购率为 2.35%，浏览→购买率为 0.71%。仅使用完整首次观察周和完整随访周，次周活动留存为 3.28%。后续会话转化高于首次观察会话，差异为观察性结果。

## 背景与方法
为数据分析和数据运营实习准备的公开数据个人项目。研究浏览、加购、购买路径，识别值得调查的转化环节。

### 关键假设
- UTC 时间；匿名访客不等于实名账户，首次观察不等于真实新客。
- 完全重复行去重；主漏斗严格递增，可跨会话和商品，另做同商品口径。
- 相邻事件间隔超过 30 分钟开启新会话；同毫秒事件不强行确定先后。
- 留存采用自然周队列，观察不足的单元格不记为零。
- 无收入、投放、实验和人口属性数据；不推断运营提升或因果机制。

原始来源：[RetailRocket / Kaggle](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)
参考研究问题：[product-funnel-activation-sql](https://github.com/jacobmackey01/product-funnel-activation-sql)
本项目重新编写 SQL、执行原始数据，并增加会话、同商品转化、商品对比和独立校验。
'''),md('### 1 加载环境与全量数据'),code('''from pathlib import Path
import sys, json
root = Path.cwd()
if root.name == 'notebooks': root = root.parent
assert (root / 'sql').exists(), '请从项目根目录或 notebooks 目录运行'
sys.path.insert(0, str(root / 'src'))
import pandas as pd
from IPython.display import display
import matplotlib.pyplot as plt
import run_analysis, validate, plot_results
%matplotlib inline
receipt = run_analysis.run(root / 'data/events.csv.gz')
print('已重新执行 SQL，耗时', receipt['seconds'], '秒')
def read(name): return pd.read_csv(root / f'results/tables/{name}.csv')
plot_results.style()
'''),md('## 数据\n### 2 审计数据质量'),code("display(read('01_quality').T.rename(columns={0:'值'}))\nvalidation = {'fixtures': validate.fixture_checks(), 'pandas': validate.independent_checks(root/'data/events.csv.gz')}\nprint(json.dumps(validation,ensure_ascii=False,indent=2))"),md('## 分析结果\n### 3 按时间顺序计算访客漏斗'),code("display(read('02_funnel').round(3))\ndisplay(read('03_funnel_sensitivity'))\ndisplay(plot_results.funnel())\nplt.close('all')"),md('同商品严格漏斗购买访客为 9,641 人，低于可跨商品的 9,952 人。加购是所选路径的必要环节，存在直接购买和日志缺失，不能将所有未走完路径的访客解释为购买失败。'),md('### 4 比较首次观察会话与后续会话'),code("display(read('04_sessions').round(3))\ndisplay(plot_results.sessions())\nplt.close('all')"),md('首次观察会话按序购买率为 0.43%，后续会话为 1.32%。分组在会话开始时确定；同一访客可贡献多个会话，因此会话不相互独立。差异不能证明回访引起转化提升。'),md('### 5 完整周队列活动留存'),code("display(read('retention_weighted').round(3))\ndisplay(plot_results.retention())\nplt.close('all')"),md('次周留存的加权分母为 1,295,569 位访客，分子为 42,465 位。每个周龄的合格队列不同，不能把加权曲线视为同一批用户的追踪曲线。完整队列单元格已由 pandas 独立核对。'),md('### 6 固定观察窗口的首次购买'),code("display(read('06_activation').T.rename(columns={0:'值'}))"),md('至少有完整 7 天观察的 1,348,273 位访客中，10,165 位在首次观察后 7 天内购买，比例为 0.75%。这是首次观察活动起算的指标，不是注册激活率。'),md('### 7 高浏览商品和行为分层'),code("display(read('07_products').head(10).round(3))\ndisplay(plot_results.products())\nplt.close('all')\ndisplay(read('08_profiles').round(2))"),md('### 8 高活跃访客敏感性分析'),code("display(read('09_activity_sensitivity').round(3))"),md('超过第 99.9 百分位阈值 47 条事件的 1,351 位访客暂时排除后，加购比例从 2.35% 变为 2.29%，严格顺序购买比例从 0.71% 变为 0.67%。这只是敏感性分析，不认定这些访客是机器人。'),md('## 结论与下一步\n优先调查浏览后未加购的行为路径，针对高浏览低购买商品检查可购买状态、页面说明和日志覆盖；通过真实访谈或可用性测试补充动机证据。可设计推荐模块实验，以访客随机分组、浏览后加购为主指标、购买转化与页面性能为护栏。当前只完成分析和实验方案，没有执行线上实验，也没有已实现的收入或转化提升。')]
nbf.validate(nb)
nbf.write(nb,ROOT/'notebooks/retailrocket_analysis.ipynb')
print('Notebook created')
