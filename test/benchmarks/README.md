# Course benchmarks

本目录包含课程使用的 Bookshelf benchmark：

- `AES`
- `JPEG`
- `GCD`

每个 case 目录都应包含至少以下文件：

```text
<CASE>.aux
<CASE>.nodes
<CASE>.nets
<CASE>.pl
<CASE>.scl
```

运行前可检查 benchmark 完整性：

```bash
python check_benchmarks.py
```

运行全部 benchmark：

```bash
bash run.sh
```

只运行一个 benchmark：

```bash
bash run.sh AES
bash run.sh JPEG
bash run.sh GCD
```
