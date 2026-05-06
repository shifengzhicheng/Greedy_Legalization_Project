# Third-party notices

The optional reference baseline in [src/baseline/](src/baseline/) reuses and adapts legalization operators from DREAMPlace.

Upstream project:

- DREAMPlace
- Author / maintainer: Yibo Lin and contributors
- Upstream repository: `limbo018/DREAMPlace`
- Upstream license: BSD 3-Clause License

Locally reused or adapted areas include:

- `src/baseline/ops/greedy_legalize/`
- `src/baseline/ops/abacus_legalize/`
- supporting utility code required to build those operators

Indicators of DREAMPlace-derived source in this repository include:

- author headers such as `Yibo Lin`
- `DREAMPLACE_BEGIN_NAMESPACE`
- operator structure and naming aligned with DREAMPlace

This teaching repository keeps only the minimal subset needed to build the optional reference baseline used for comparison and debugging.

If you publish this repository externally, keep this notice together with the relevant upstream license text and preserve attribution for reused DREAMPlace-derived files.
