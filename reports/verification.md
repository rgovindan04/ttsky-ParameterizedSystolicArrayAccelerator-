# Verification results

- 40 cocotb test cases passed across ten configurations and three stages (PE, array, host).
- 470 directed/random matrix products were checked against NumPy, plus protocol/recovery cases and 250 cycle-by-cycle array wavefront trials.
- All ten configurations passed Verilator 5.044 lint without warnings.
- The small and wide-accumulator 20 ns physical builds and the final default 25 ns build each passed both functional gate-level tests. These simulations use cell models without SDF annotation; extracted timing is assessed separately by STA.
- The official TinyTapeout tool validated the final top-level ports and metadata and generated the floorplan configuration.
- The default build's separate layout precheck is recorded in [precheck.md](precheck.md). Physical timing and electrical warnings are recorded in [physical.md](physical.md).

Local tools: Python 3.11.9, cocotb 2.0.1, NumPy 1.26.2, Icarus Verilog 12.0, Verilator 5.044. CI installs the versions pinned in `test/requirements.txt`. No GitHub workflow was dispatched; all reported runs were local.

Reproduce with `python3 scripts/regress.py`. [verification.json](verification.json) records each simulation stage. Full XML and logs remain in ignored `test/sim_build/` directories.
