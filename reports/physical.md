# Physical implementation results

LibreLane v3.0.0; SKY130A PDK `8afc8346a57fe1ab7934ba5a6056ea8b43078e71`; TinyTapeout tools `01d5d2814fa9dd61e9d211e0b235a4a592a9316a`.

Area excludes filler cells. Setup and hold values are the worst across all nine extracted timing corners. One MAC is one multiply plus add. Throughput is derived from verified cycle counts at the configured clock, with no host stalls.

| Profile | Clock (ns) | Tiles | Cell area (µm²) | Worst setup (ns) | Worst hold (ns) | DRC / LVS | Timing closed | Scheduled MAC/s incl. IO |
|---|---:|---|---:|---:|---:|---|---|---:|
| small | 20 | 1x2 | 20601.0 | 4.408 | 0.104 | 0 / 0 | yes | 18.182 M |
| default | 20 | 2x2 | 44645.3 | -1.592 | 0.113 | 0 / 0 | no | target missed |
| wide_acc | 20 | 2x2 | 54710.0 | -3.205 | 0.106 | 0 / 0 | no | target missed |
| default | 25 | 2x2 | 44403.8 | 3.718 | 0.113 | 0 / 0 | yes | 12.308 M |

The initial 20 ns runs use the inherited template settings; the 25 ns default enables post-global-route design repair and checks setup/hold at every corner. The template can complete successfully while warning about timing failures outside its default checked corners. `passed` in JSON records the flow exit status; `timing_closed` separately records setup/hold closure.

Electrical warnings remain: see `max_slew_violations` and `max_cap_violations` in [physical.json](physical.json). Positive setup/hold slack does not establish complete electrical signoff. Maximum-slew warnings must be reviewed before fabrication. The default template skips KLayout DRC/XOR; the separate TinyTapeout precheck runs its own KLayout geometry checks.

The byte interface is the throughput bottleneck. The default processes eight useful MACs in 26 cycles, including load, START, fill/drain, result capture, and readout. It has no overlap between transactions.

Run paths and exact configuration parameters are recorded in [physical.json](physical.json). Large generated netlists, GDS files, extraction data, and logs remain in ignored run directories. [precheck.md](precheck.md) records the default design’s separate TinyTapeout precheck.
