#!/usr/bin/env python3
"""Run PE, cycle-accurate array, and host-protocol tests for each configuration."""
import argparse
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from configurations import CONFIGS, validate

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configs', nargs='*', help='Configuration names; omit for the standard sweep')
    args = parser.parse_args()
    args.configs = args.configs or list(CONFIGS)
    for name in args.configs:
        if name not in CONFIGS:
            parser.error(f'Unknown configuration: {name}')
    for name in args.configs:
        config = CONFIGS[name]
        validate(config)
        env = dict(os.environ, **{f'MAC_{k}': str(v) for k, v in config.items()})
        defines = ' '.join(f'-DMAC_{k}={v}' for k, v in config.items())
        for stage, top, module in [('pe', 'mac_pe', 'test_pe'), ('array', 'systolic_array', 'test_array'), ('host', 'tb', 'test')]:
            dest = ROOT / 'test' / 'sim_build' / name / stage
            dest.mkdir(parents=True, exist_ok=True)
            result = dest / 'results.xml'
            result.unlink(missing_ok=True)
            cmd = ['make', '-B', '-C', str(ROOT / 'test'), '-f', 'Makefile' if stage == 'host' else 'unit.mk',
                   f'TOPLEVEL={top}', f'COCOTB_TEST_MODULES={module}', f'SIM_BUILD={dest}',
                   f'COCOTB_RESULTS_FILE={result}', f'EXTRA_DEFINES={defines}']
            with (dest / 'run.log').open('w') as log:
                proc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
            if proc.returncode or not result.exists() or ET.parse(result).findall('.//failure') or ET.parse(result).findall('.//error'):
                raise SystemExit(f'FAIL {name}/{stage}: see {dest / "run.log"}')
            print(f'PASS {name}/{stage}', flush=True)


if __name__ == '__main__':
    main()
