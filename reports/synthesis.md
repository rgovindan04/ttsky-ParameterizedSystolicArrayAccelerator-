# Synthesis and schedule comparison

Yosys 0.63 (git sha1 70a11c6bf0e8dd669f56c7da3587f78b405138e2, clang++ 17.0.0 -fPIC -O3)

Mapped with `sky130_fd_sc_hd__tt_025C_1v80.lib`; library SHA-256: `8e78e14442062dba34d414fca6490b2f6b96038d4510d1438ca44fee31487135`. Generic cells unless liberty specified. No placement, routing, STA or timing closure implied.

| Configuration | DATA/ACC | R×C×K | Cells | Mapped area (µm²) | Array cycles | START→DONE | Transaction cycles | MAC/cycle incl. IO |
|---|---|---|---:|---:|---:|---:|---:|---:|
| tiny | 4/12 | 1×1×2 | 374 | 3225.5936 | 2 | 3 | 10 | 0.2000 |
| small | 4/16 | 2×2×2 | 1453 | 12939.9104 | 4 | 5 | 22 | 0.3636 |
| default | 8/24 | 2×2×2 | 3172 | 27732.848 | 4 | 5 | 26 | 0.3077 |
| wide_acc | 8/32 | 2×2×2 | 4123 | 33677.2992 | 4 | 5 | 30 | 0.2667 |
| rectangular | 8/24 | 2×3×4 | 5252 | 45592.4768 | 7 | 8 | 47 | 0.5106 |

Transaction cycles include all input bytes, START, systolic fill/compute/drain, one result-capture edge, and all output acknowledgments. No host stalls or reset. One MAC is one multiply plus one add.
