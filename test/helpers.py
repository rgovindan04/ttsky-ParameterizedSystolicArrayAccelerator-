"""Deterministic edge driver; also leaves time for gate-level cell delays."""
import os
import json
from pathlib import Path
import re
import numpy as np
from cocotb.triggers import Timer

DEFAULTS = dict(re.findall(r'`define MAC_(\w+) (\d+)',
                           (Path(__file__).resolve().parents[1] / 'src/config.vh').read_text()))
DATA_W, ACC_W, ROWS, COLS, K = [
    int(os.getenv(f'MAC_{key}', DEFAULTS[key]))
    for key in ('DATA_W', 'ACC_W', 'ROWS', 'COLS', 'K')
]

PERIOD_NS = float(os.getenv("CLOCK_PERIOD_NS", str(json.loads(
    (Path(__file__).resolve().parents[1] / "src/config.json").read_text())["CLOCK_PERIOD"])))


def signed(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def golden(a, b):
    # Python integers inside NumPy avoid host int64 overflow for wider configs.
    product = np.asarray(a, dtype=object) @ np.asarray(b, dtype=object)
    return [signed(int(v), ACC_W) for v in product.flat]


async def tick(dut):
    dut.clk.value = 0
    await Timer(PERIOD_NS/2, unit='ns')
    dut.clk.value = 1
    await Timer(PERIOD_NS/2, unit='ns')
    dut.clk.value = 0


def packed(values, width):
    return sum((int(v) & ((1 << width) - 1)) << (i * width)
               for i, v in enumerate(values))
