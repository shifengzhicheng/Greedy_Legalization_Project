# Benchmark data

These benchmark cases are used for the greedy legalization teaching assignment.

Cases:

- `AES`
- `JPEG`
- `GCD`

Technology:

- `NG45`

Each case follows Bookshelf format and includes:

- `.aux`
- `.nodes`
- `.nets`
- `.pl`
- `.scl`

The `.pl` file is the input placement before legalization.

Useful commands:

```bash
python check_benchmarks.py
bash run.sh AES
bash run.sh JPEG
bash run.sh GCD
bash run.sh all
```

If you add or replace benchmark data, keep all Bookshelf component files in the same case directory and make sure the `.aux` file references the matching filenames.
