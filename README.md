# 铁路图片分类数据集

用于铁路部件（轨道 / 轨枕 / 扣件）正常/异常分类，支持模型微调与能力评测。

## 目录结构

```text
.
├── raw/                     # 原始数据，只读，不直接用于训练（图片不提交 git）
├── dataset/                 # 由脚本生成的训练数据（图片不提交 git）
│   ├── train/
│   │   ├── track_normal/
│   │   ├── track_abnormal/
│   │   ├── sleeper_normal/
│   │   ├── sleeper_abnormal/
│   │   ├── fastener_normal/
│   │   └── fastener_abnormal/
│   ├── val/                 # 与 train 同构（6 类）
│   └── test/                # 与 train 同构，冻结用于最终评测
├── metadata/
│   └── dataset.csv          # 唯一数据索引（标签、区段、划分的唯一来源）
└── scripts/
    ├── build_split.py       # 按区段划分并生成 dataset/{split}/{class}/
    └── validate.py          # 校验结构 + 检查 train/val/test 泄漏
```

6 个类别：`{track|sleeper|fastener}_{normal|abnormal}`。类别即目录名，可直接用
`torchvision.datasets.ImageFolder` 或 YOLO 分类目录加载，无需自定义代码。

## 工作流

1. 把原始图片放进 `raw/<section>/<component>/<condition>/`。
2. 在 `metadata/dataset.csv` 登记每张图（字段见下）。
3. 生成划分：
   ```bash
   python scripts/build_split.py --clear            # 默认 8:1:1，按 section_id 分组
   # 可选: --ratios 0.7,0.15,0.15  --mode symlink  --seed 42
   ```
4. 校验（务必在提交前运行）：
   ```bash
   python scripts/validate.py
   ```

## metadata/dataset.csv 字段

| 字段 | 说明 |
| --- | --- |
| `filepath` | 相对仓库根目录的原始图片路径，放在 `raw/` 下 |
| `component` | `track` / `sleeper` / `fastener` |
| `label` | `normal` / `abnormal` |
| `split` | 由 `build_split.py` 写入，无需手填 |
| `section_id` | **同一线路区段/采集批次共用一个 id，划分以它为最小单位** |
| `capture_batch` | 采集批次，便于追溯 |
| `camera` | 相机编号 |
| `timestamp` | 采集时间（ISO8601） |
| `annotator` | 标注/复核人 |
| `annotation_version` | 标注版本，重标时递增，不覆盖历史 |

## 关键约定

- **划分按 `section_id` 分组，绝不按单张图随机分**，避免同一区段连续帧同时进入
  训练集和测试集导致指标虚高。
- **`raw/` 不可变；`dataset/` 是可重生成的产物。** 增删数据只改 `raw/` 和 csv，
  重跑 `build_split.py --clear` 即可，不要手动移动文件。
- **`test/` 冻结**：标注确认后不再改动，保证历史指标可比。
- **图片不进 git**：用 Git LFS 或 DVC 管理，仓库只提交脚本、csv 和 README。
  `.gitignore` 已忽略常见图片扩展名，仅保留 `.gitkeep` 占位。

## 常用改动

- **加一个新部件类别**：编辑 `scripts/build_split.py` 与 `scripts/validate.py` 的
  `CLASSES`，重建对应目录，再跑 `build_split.py --clear`。
- **换划分比例**：`--ratios`，无需改代码。
- **换标注版本**：在 csv 里改 `annotation_version`，旧版本记录保留。
