# Standard-Cell Legalization Problem

本文档说明本教学项目中的 legalization 问题、输入数据、基本概念、合法性约束和优化目标。README 保持为快速入口；更具体的问题定义放在这里。

## 1. Legalization 在物理设计流程中的位置

在 standard-cell placement 流程中，global placement 通常先给出一个 wirelength 较好的连续坐标解。这个解会保留 cell 之间较好的相对位置，但它不一定满足制造和布局工具要求，例如：

- cell 可能互相 overlap；
- cell 的 `y` 坐标可能没有落在合法 placement row 上；
- cell 的 `x` 坐标可能没有对齐到 site grid；
- cell 可能超出 row 的合法范围；
- movable cell 可能压到 fixed terminal 或 macro 上。

Legalization 的任务是在尽量保留 global placement 结果的基础上，把所有 movable cells 移动到合法位置。Legalization 之后通常还会有 detailed placement 做更细的局部优化。

本项目关注的是一个教学用的 row-based standard-cell legalization 子问题：输入是 Bookshelf format 的 placement，输出是一个新的 `.pl` 文件，使所有 movable cells 满足合法性检查。

## 2. 输入和输出

### 输入

每个 benchmark case 通过一个 Bookshelf `.aux` 文件描述。`.aux` 文件会引用该 design 的其他 Bookshelf 文件：

- `.nodes`：定义每个 node 的 width、height，以及是否为 terminal；
- `.nets`：定义 net 和 pin，用于计算 HPWL；
- `.pl`：定义初始 placement 坐标；
- `.scl`：定义 placement rows、row height、site width、site spacing 和 row 范围；
- `.wts`、`.shapes`、`.route`：可选文件，本项目的核心 parser/checker 不依赖这些文件。

在本项目中，初始 `.pl` 被视为 legalization 的输入 placement。

### 输出

学生实现的 legalizer 需要返回一个更新后的 `Design` 对象。`main.py` 会把结果写成：

```text
results/<design>/<mode>/<design>.<mode>.pl
```

同时会生成 metrics：

```text
results/<design>/<mode>/metrics.json
results/summary.csv
```

## 3. 基本概念

### Node / Cell

Bookshelf 中的一个 node 可以表示 standard cell、fixed terminal 或 macro。本项目主要移动 standard cells。

每个 node 有：

- `width`：cell 宽度；
- `height`：cell 高度；
- `(x, y)`：cell 左下角坐标；
- `orient`：方向标记，教学项目中通常保持原值即可。

### Movable cell

Movable cell 是 legalizer 可以移动的对象。学生算法主要修改这些 cell 的坐标。

对于 movable cell，legalizer 可以改变：

- `x` 坐标；
- `y` 坐标，也就是选择哪一条 row。

### Fixed terminal / Macro

Fixed terminal 或 macro 是不能移动的对象。Legalizer 必须保持它们的位置不变，并避免 movable cell 与它们 overlap。

### Placement row

Placement row 是 standard cell 可以放置的水平带状区域。每条 row 有：

- `y`：row 的下边界坐标；
- `height`：row 高度；
- `x_start`：row 左边界；
- `x_end`：row 右边界；
- `site_width` 和 `site_spacing`：site grid 信息。

一个合法的 single-row standard cell 通常要求：

```text
cell.y == row.y
cell.height <= row.height
row.x_start <= cell.x
cell.x + cell.width <= row.x_end
```

### Site grid

Row 被离散成一系列 placement sites。Movable cell 的左下角 `x` 坐标必须对齐到 site grid。

如果 row 的 site pitch 为 `site_spacing`，则合法 `x` 一般满足：

```text
x = row.x_start + k * site_pitch
```

其中 `k` 是非负整数。

### Net, Pin, HPWL

`.nets` 文件定义 nets 和 pins。每个 pin 连接到一个 node，并可能带有相对于 node center 的 offset。

本项目使用 HPWL，也就是 half-perimeter wirelength，作为 wirelength 的近似指标。对一个 net，HPWL 定义为：

```text
HPWL(net) = (max_x - min_x) + (max_y - min_y)
```

其中 `max_x/min_x/max_y/min_y` 来自该 net 上所有 pin 的坐标。整个 design 的 HPWL 是所有 nets 的 HPWL 之和。

## 4. 合法性约束

本项目的 checker 主要检查以下条件。

### 4.1 Row alignment

每个 movable cell 的 `y` 坐标必须落在一条合法 row 上。

```text
cell.y == row.y
```

教学项目默认关注 single-row movable cells，因此 movable cell 的高度不能超过 row height。

### 4.2 Row boundary

Movable cell 必须完整落在 row 的水平范围内：

```text
cell.x >= row.x_start
cell.x + cell.width <= row.x_end
```

### 4.3 Site alignment

Movable cell 的 `x` 坐标必须 snap 到 site grid：

```text
(cell.x - row.x_start) / site_pitch is an integer
```

### 4.4 No overlap among movable cells

同一条 row 内的 movable cells 不能重叠。若两个 cell 在同一 row，且它们的水平区间分别是 `[x1, x1 + w1]` 和 `[x2, x2 + w2]`，则必须满足：

```text
x1 + w1 <= x2    or    x2 + w2 <= x1
```

### 4.5 No overlap with fixed objects

Movable cell 不能与 fixed terminal 或 macro overlap。Fixed objects 不能被移动。

## 5. 优化目标

Legalization 是一个约束优化问题。最重要的是先满足合法性，然后再考虑解的质量。

### Primary objective: legality

本项目的首要目标是：

```text
legalized = True
```

也就是所有 movable cells 都满足 row alignment、row boundary、site alignment、no-overlap 和 fixed-object constraints。

### Secondary objective: preserve placement quality

在合法性满足之后，希望尽量少破坏 global placement 的质量。本项目报告以下指标用于分析算法。

#### Delta HPWL

```text
delta_hpwl = final_hpwl - original_hpwl
```

`delta_hpwl` 越小，说明 legalization 对 wirelength 的影响越小。它可以为负，也就是 legalization 后 HPWL 变小；但一般情况下，legalization 可能会带来一定 HPWL 增长。

#### Displacement

Displacement 衡量 cell 从初始位置移动了多少。本项目报告 L1 和 L2 displacement。

对一个 cell：

```text
L1 displacement = |x_final - x_original| + |y_final - y_original|
L2 displacement = sqrt((x_final - x_original)^2 + (y_final - y_original)^2)
```

常用汇总指标包括：

- `avg_disp_l1`：所有 movable cells 的平均 L1 displacement；
- `max_disp_l1`：最大 L1 displacement；
- `avg_disp_l2`：所有 movable cells 的平均 L2 displacement；
- `max_disp_l2`：最大 L2 displacement。

#### Runtime

`runtime_sec` 记录 legalizer 的运行时间。较大的 benchmark 上，算法复杂度会直接影响 runtime。

## 6. 常见算法思路

一个基础 greedy legalizer 通常可以按以下思路实现：

1. 对 movable cells 按初始 `x` 或 `(y, x)` 排序；
2. 为每个 cell 选择候选 row；
3. 将 cell 的 `x` snap 到该 row 的 site grid；
4. 在 row 内从左到右放置 cell，消除 overlap；
5. 如果当前 row 容量不足，尝试 spill 到相邻 row；
6. 使用 HPWL 或 displacement 作为 tie-breaker，选择代价较小的位置。

更高级的实现可以使用 cluster-based placement、Abacus-style legalization、局部重排、窗口优化等方法。但本教学项目不要求实现复杂工业级算法。

## 7. Baseline 的作用

仓库中的 baseline 是 optional reference implementation。它的作用是：

- 展示输入、输出和 metrics 的完整流程；
- 帮助学生调试自己的输出格式；
- 提供一个参考结果用于理解算法 trade-off。

Baseline 不是必须 beat 的目标。课程实现应优先保证结果 legal，并能够解释自己的算法如何处理 row selection、site snapping、overlap removal 和 fixed objects。

## 8. 建议的实现检查顺序

实现 `src/custom_legalizer.py` 时，建议按以下顺序调试：

1. 先在 `test/toy_tiny` 上跑通；
2. 确认所有 fixed objects 坐标保持不变；
3. 确认每个 movable cell 的 `y` 坐标对应合法 row；
4. 确认每个 movable cell 的 `x` 坐标 snap 到 site grid；
5. 检查 row 内是否仍有 overlap；
6. 检查是否与 fixed objects overlap；
7. 再观察 `delta_hpwl`、displacement 和 runtime。

可以使用：

```bash
python checkplacement.py --aux test/toy_tiny/toy_tiny.aux --pl results/toy_tiny/custom/toy_tiny.custom.pl
```

当 toy case 能稳定 legal 后，再运行 AES / JPEG / GCD benchmark。
