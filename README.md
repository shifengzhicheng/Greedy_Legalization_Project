# Greedy Legalization Teaching Repo

这个仓库是一个基于 Bookshelf format 的 standard-cell legalization 教学项目。目标是：**在满足合法布局约束的前提下，尽量减小 `delta_hpwl`**。学生主要实现自己的 custom legalizer，并和内置 baseline 在 AES / JPEG / GCD benchmark 上比较结果。

## Repo purpose

这个 REPO 的目的有两点：

1. 提供一个可直接运行的 legalization 框架。
2. 专注于 legalizer 本身，而不是自己重写 parser、metric、checker 或 benchmark runner。

仓库已经内置：

- Bookshelf `.aux/.nodes/.nets/.pl/.scl` 解析器
- HPWL、displacement、legality checker
- baseline mode：DREAMPlace greedy legalization + abacus legalization 的最小复用版本
- custom mode：学生自己的 legalization 入口
- `run.sh`：调用 `main.py` 跑一个 case 的 baseline/custom
- `checkplacement.py`：独立检查某个 placement 是否 legal
- `test/toy_tiny`：极小调试样例
- `test/benchmarks/AES|JPEG|GCD`：课程 benchmark

## Legalization problem overview

legalization 的输入通常是 global placement 之后的 placement。此时 cell 的相对位置通常已经不错，但可能存在 overlap、未对齐 row/site、超出 row 边界等问题。legalizer 的任务是把所有 movable cell 调整到**合法**位置。

这个问题的核心目标是：

- **Primary objective**：legalize 所有 cell，同时尽量减小 `delta_hpwl`

常见参考优化目标包括：

- `avg_disp_l1`
- `max_disp_l1`
- `runtime_sec`

你通常需要在 **wirelength**、**displacement** 和 **runtime** 之间做 trade-off。

## Basic concepts

### Cell height

standard cell 有固定的 width 和 height。这个项目默认教学子集主要关注 single-row movable cell，也就是 movable cell 的高度不能超过 row height。

### Row

placement row 是可以放置 standard cell 的水平带状区域。cell 的 `y` 必须落在合法 row 上。

### Site / site pitch

row 被离散成一个个 site。cell 的左下角 `x` 需要对齐到 site grid，不能落在任意实数位置。

## Legality constraints

当前 checker 会检查：

- movable cell 的 `y` 是否落在合法 row 上
- cell height 是否不超过 row height
- `x` 是否在 row 范围内
- `x` 是否 snap 到 site grid
- 同一 row 内 movable cell 是否无 overlap
- movable cell 是否与 fixed terminal / macro overlap

如果任意一条不满足，则该 placement 不是 legal placement。

## Directory layout

```text
GreedyLegalization/
├── README.md
├── requirements.txt
├── run.sh
├── checkplacement.py
├── configs/
│   └── cases.json
├── results/
├── main.py
├── check_benchmarks.py
├── src/
│   ├── custom_legalizer.py
│   ├── baseline/
│   │   ├── __init__.py
│   │   ├── abacus_legalizer.py
│   │   ├── CMakeLists.txt
│   │   └── ops/
│   └── database/
│       ├── bookshelf.py
│       ├── design.py
│       └── metrics.py
└── test/
    ├── toy_tiny/
    └── benchmarks/
        ├── AES/
        ├── JPEG/
        └── GCD/
```

## Installation / dependencies

### Custom mode only

如果只做自己的 legalizer，基础 Python 环境即可：

```bash
python --version
python check_benchmarks.py
```

推荐 Python >= 3.9。`requirements.txt` 主要是为了 baseline mode 准备的；custom mode 本身不依赖额外 pip 包。

### Baseline mode

如果你还想运行 baseline，需要额外准备：

- `torch`
- `cmake`
- 支持 OpenMP 的本地 C++ 编译环境

运行 baseline 所需的最小源码已经放在仓库里，本地构建即可。
仓库根目录也提供了 `CMakeLists.txt`，可以直接在 repo root 发起 build。

## TODO for students

你的主要修改应该集中在文件：

```text
src/custom_legalizer.py
```

默认实现只是直接返回输入 placement，因此通常不会 legal。你需要自己完成 legalization。

1. 选择合法 row。
2. 将 `x` snap 到 site grid。
3. 按 row 内顺序消除 overlap。
4. 必要时在相邻 row 之间 spill。
5. 用 HPWL / displacement 作为 tie-breaker。
6. 保持 fixed objects 不动。

## How to run experiments

### Run a single custom experiment

```bash
python main.py --aux test/toy_tiny/toy_tiny.aux --mode custom --out-dir results
```

### Run a single baseline experiment

先构建 baseline：

```bash
cmake -S . -B build/baseline_ops -DPython3_EXECUTABLE="$(which python)"
cmake --build build/baseline_ops -j
```

然后运行：

```bash
python main.py --aux test/toy_tiny/toy_tiny.aux --mode baseline --out-dir results
```

### Run a case with `run.sh`

`run.sh` 会清晰地调用两条 `python main.py` 指令：一条跑 baseline，一条跑 custom。

```bash
bash run.sh
bash run.sh AES
```

不带参数时，`run.sh` 读取 `configs/cases.json` 里的单个默认 case。带参数时，直接运行你指定的那个 case。

如果 baseline 尚未构建，`run.sh` 会跳过 baseline，只继续跑 custom。

## How to check legality

可以单独检查某个 placement 是否 legal：

```bash
python checkplacement.py --aux test/toy_tiny/toy_tiny.aux --pl results/toy_tiny/custom/toy_tiny.custom.pl
```

也可以输出 JSON：

```bash
python checkplacement.py --aux test/toy_tiny/toy_tiny.aux --pl results/toy_tiny/custom/toy_tiny.custom.pl --json
```

## Metrics

`main.py` 和 `run.sh` 会输出：

- `original_hpwl`
- `final_hpwl`
- `delta_hpwl`
- `delta_hpwl_pct`
- `avg_disp_l1`
- `max_disp_l1`
- `avg_disp_l2`
- `max_disp_l2`
- `runtime_sec`
- `legalized`

先要求 `legalized=True`，再比较 `delta_hpwl`、displacement 和 runtime。

## Output files

```text
results/<design>/<mode>/<design>.<mode>.pl
results/<design>/<mode>/metrics.json
results/summary.csv
```
