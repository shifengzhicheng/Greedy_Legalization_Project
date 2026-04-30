# Test data layout

This directory contains:

- `toy_tiny/`: a tiny Bookshelf example with intentional overlaps. It is small enough for students to debug by hand.
- `benchmarks/AES`, `benchmarks/JPEG`, `benchmarks/GCD`: placeholders for the three course benchmark cases.

For each benchmark case, put all Bookshelf files in the same directory and ensure the `.aux` file references the correct `.nodes`, `.nets`, `.pl`, and `.scl` files.

Expected example:

```text
test/benchmarks/AES/
  AES.aux
  AES.nodes
  AES.nets
  AES.pl        # pre-legalization placement, e.g. DreamPlace global placement output renamed or referenced here
  AES.scl
  AES.wts       # optional, parser ignores it
```
