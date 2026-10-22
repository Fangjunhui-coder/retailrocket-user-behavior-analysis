# 原始数据

此仓库不包含原始数据。请从项目根目录运行：

```bash
python src/download_data.py
```

该脚本从 RetailRocket 的 Kaggle 数据集下载归档，仅保留 `data/events.csv.gz`。下载接口不可用时，可在[发布页面](https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset)手动下载，将 `events.csv` 压缩为上述路径，或使用 `python src/run_analysis.py --data /path/to/events.csv` 运行分析。

数据许可及来源见项目根目录的 `DATA_SOURCE.md`。
