# 数据来源与使用说明

发布方：RetailRocket。原始发布页：[Retailrocket recommender system dataset](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)。

分析使用原始数据集的 `events.csv`，不使用商品属性和类目树。原始数据不包含在此 GitHub 发布版本中。运行 `python src/download_data.py` 可从发布方的 Kaggle 接口获取归档，并将其中的行为文件无损压缩为 `data/events.csv.gz`。

数据获取及许可核对日期为 2026-10-15，发布页与数据集元信息当时标注许可为 **CC BY-NC-SA 4.0**。许可链接：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)。数据及衍生输出保留此来源与许可说明，代码不替代数据许可。

原始 CSV 校验和、当时下载的 gzip 副本校验和、参考仓库及版本见 `results/source.json`。gzip 重新压缩可能生成不同文件校验和，可通过解压后原始 CSV 的校验和核对内容。

分析转换包括字段类型解析、有效性检查、完全重复行去重、访客与会话分组、指标聚合和可视化。数据窗口为 2015-05-03 至 2015-09-18 UTC。数据为匿名历史行为，不能代表当前平台或某个特定行业和人群。
