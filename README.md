# Greedy Legalization Teaching Repo

这个仓库是一个基于 Bookshelf format 的 standard-cell legalization 教学 skeleton。

**主要目标**是输出一个 legal placement。`delta_hpwl`、displacement 和 runtime 作为分析算法 trade-off 的参考指标。

仓库内置的 baseline 是一个 **optional reference implementation**，用于帮助理解流程、输出格式和调试方法；课程不强制要求 beat baseline。

## Repo purpose

这个仓库提供：

- Bookshelf `.aux/.nodes/.nets/.pl/.scl` 解析器
- legality checker 和常用 metrics
- `main.py`：统一运行 custom / reference baseline
- `src/custom_legalizer.py`：学生实现入口
- `run.sh`：一键运行配置好的 benchmark case
- `checkplacement.py`：独立检查某个 placement 是否 legal
- `test/toy_tiny`：极小调试样例
- `test/benchmarks/AES|JPEG|GCD`：课程 benchmark

## Problem definition

Legalization 的问题定义、基本概念、合法性约束和优化目标详见：

[docs/legalization.md](docs/legalization.md)

该文档介绍 cell、row、site grid、fixed objects、net / pin / HPWL、displacement、runtime，以及本项目 checker 采用的合法性条件。README 只保留运行和提交所需的最小说明。

## Quick start

先确认 benchmark 文件齐全：

```bash
python --version
python check_benchmarks.py
```

运行一个最小 custom 示例：

```bash
python main.py --aux test/toy_tiny/toy_tiny.aux --mode custom --out-dir results
```

## Student task

学生主要修改：

```text
src/custom_legalizer.py
```

默认实现只是返回输入 placement，因此通常不会 legal。你需要实现自己的 legalization 算法，让输出先满足 `legalized=True`。

建议优先完成：

1. 保持 fixed terminals / macros 不动。
2. 给每个 movable cell 选择合法 row。
3. 将 `x` 对齐到 site grid。
4. 消除 row 内 overlap。
5. 尽量避免不必要的 HPWL / displacement 增长。

## Run benchmarks

运行单个 benchmark：

```bash
bash run.sh AES
bash run.sh JPEG
bash run.sh GCD
```

运行全部配置好的 benchmark：

```bash
bash run.sh all
```

需要一次干净运行时，可以清空旧结果后再生成 `results/summary.csv`：

```bash
bash run.sh all --clean
```

`run.sh` 也支持调试样例：

```bash
bash run.sh toy_tiny
```

不带参数时，`run.sh` 会读取 `configs/cases.json` 里的默认 case。

## Optional reference baseline

如果你想运行 reference baseline，请先确认已经安装好 `requirements.txt` 中的依赖，然后构建 baseline ops：

```bash
cmake -S . -B build/baseline_ops -DPython3_EXECUTABLE="$(which python)"
cmake --build build/baseline_ops -j
```

构建完成后可以直接运行：

```bash
python main.py --aux test/toy_tiny/toy_tiny.aux --mode baseline --out-dir results
```

如果 baseline 尚未构建，`run.sh` 会跳过 baseline，只继续跑 custom。

## How to check legality

```bash
python checkplacement.py --aux test/toy_tiny/toy_tiny.aux --pl results/toy_tiny/custom/toy_tiny.custom.pl
```

输出 JSON：

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

功能要求是：

```text
legalized=True
```

在满足合法性之后，再使用 `delta_hpwl`、displacement 和 runtime 分析算法表现。baseline 只是参考点，不是必须达到的目标。

## Installation / dependencies

### Installation

建议先安装仓库依赖：

```bash
pip install -r requirements.txt
```

其中包含 reference baseline 所需的 Python 包。除此之外，baseline 还需要：

- `cmake`
- `ninja`
- 支持 OpenMP 的本地 C++ 编译环境

## Directory layout

```text
.
├── README.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── requirements.txt
├── run.sh
├── checkplacement.py
├── check_benchmarks.py
├── configs/
│   └── cases.json
├── docs/
│   └── legalization.md
├── main.py
├── src/
│   ├── custom_legalizer.py
│   ├── baseline/
│   └── database/
├── test/
│   ├── README.md
│   ├── toy_tiny/
│   └── benchmarks/
│       ├── README.md
│       ├── AES/
│       ├── JPEG/
│       └── GCD/
└── results/
```

## Output files

```text
results/<design>/<mode>/<design>.<mode>.pl
results/<design>/<mode>/metrics.json
results/summary.csv
```

`results/summary.csv` 汇总当前 `results/` 目录下已有的 metrics。若想得到干净 summary，请使用 `bash run.sh ... --clean`，或手动删除旧结果后再运行。
