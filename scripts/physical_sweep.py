#!/usr/bin/env python3
"""Run isolated native LibreLane builds using the official TinyTapeout floorplans.

Requires LibreLane and its EDA tools on PATH, an installed SKY130 PDK, and a
TinyTapeout tt-support-tools checkout. CI uses the standard GDS action instead.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
from configurations import CONFIGS
from select_config import TILES
from synth_sweep import performance, ROOT, SOURCES, TOP


def collect(name, run, passed, period):
    states = sorted(run.glob('*/state_out.json'))
    if not states:
        return dict(name=name, passed=False, last_step='none')
    state = states[-1]
    metrics = json.loads(state.read_text())['metrics']
    def worst(kind):
        values = [v for k, v in metrics.items() if k.startswith(f'timing__{kind}__ws__corner:')]
        return min(values) if values else metrics.get(f'timing__{kind}__ws')
    return dict(name=name, passed=passed, last_step=state.parent.name,
                parameters=CONFIGS[name], tiles=TILES[name], clock_period_ns=period,
                cell_area_um2=metrics.get('design__instance__area__stdcell'),
                area_including_fill_um2=metrics.get('design__instance__area'),
                timing_closed=worst('setup') is not None and worst('setup') >= 0 and worst('hold') >= 0,
                utilization=metrics.get('design__instance__utilization'),
                setup_ws_ns=worst('setup'), hold_ws_ns=worst('hold'),
                route_drc=metrics.get('route__drc_errors'),
                magic_drc=metrics.get('magic__drc_error__count'),
                lvs_errors=metrics.get('design__lvs_error__count'),
                max_slew_violations=metrics.get('design__max_slew_violation__count'),
                max_cap_violations=metrics.get('design__max_cap_violation__count'),
                **performance(CONFIGS[name]),
                transaction_mmac_s=1000/period*performance(CONFIGS[name])['macs_per_transaction_cycle'],
                run=str(run.relative_to(ROOT)))


def save(rows, tool, pdk, tt_commit):
    path = ROOT / 'reports' / 'physical.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    records = {(r['name'], r.get('clock_period_ns')): r for r in previous.get('configurations', [])}
    records.update({(r['name'], r.get('clock_period_ns')): r for r in rows})
    path.write_text(json.dumps(dict(tool=tool, pdk_version=pdk.name, tt_support_commit=tt_commit,
                                   configurations=list(records.values())), indent=2)+'\n')
    lines = ['# Physical implementation results', '',
             f'{tool}; SKY130A PDK `{pdk.name}`; TinyTapeout tools `{tt_commit}`.', '',
             'Area excludes filler cells. Setup and hold values are the worst across all nine extracted timing corners. One MAC is one multiply plus add. Throughput is derived from verified cycle counts at the configured clock, with no host stalls.', '',
             '| Profile | Clock (ns) | Tiles | Cell area (µm²) | Worst setup (ns) | Worst hold (ns) | DRC / LVS | Timing closed | Scheduled MAC/s incl. IO |',
             '|---|---:|---|---:|---:|---:|---|---|---:|']
    for row in records.values():
        if 'setup_ws_ns' not in row:
            continue
        closed = row.get('timing_closed', row['setup_ws_ns'] >= 0 and row['hold_ws_ns'] >= 0)
        throughput = f"{row['transaction_mmac_s']:.3f} M" if closed else 'target missed'
        lines.append(f"| {row['name']} | {row['clock_period_ns']:g} | {row['tiles']} | {row['cell_area_um2']:.1f} | {row['setup_ws_ns']:.3f} | {row['hold_ws_ns']:.3f} | {row['magic_drc']} / {row['lvs_errors']} | {'yes' if closed else 'no'} | {throughput} |")
    lines += ['', 'The initial 20 ns runs use the inherited template settings; the 25 ns default enables post-global-route design repair and checks setup/hold at every corner. The template can complete successfully while warning about timing failures outside its default checked corners. `passed` in JSON records the flow exit status; `timing_closed` separately records setup/hold closure.', '',
              'Electrical warnings remain: see `max_slew_violations` and `max_cap_violations` in [physical.json](physical.json). Positive setup/hold slack does not establish complete electrical signoff. Maximum-slew warnings must be reviewed before fabrication. The default template skips KLayout DRC/XOR; the separate TinyTapeout precheck runs its own KLayout geometry checks.', '',
              'The byte interface is the throughput bottleneck. The default processes eight useful MACs in 26 cycles, including load, START, fill/drain, result capture, and readout. It has no overlap between transactions.', '',
              'Run paths and exact configuration parameters are recorded in [physical.json](physical.json). Large generated netlists, GDS files, extraction data, and logs remain in ignored run directories. [precheck.md](precheck.md) records the default design’s separate TinyTapeout precheck.', '']
    (ROOT / 'reports/physical.md').write_text('\n'.join(lines))



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configs', nargs='+', choices=list(TILES))
    parser.add_argument('--pdk-root', type=Path, required=True, help='Parent of the installed sky130A directory')
    parser.add_argument('--tt-dir', type=Path, default=ROOT / 'tt')
    parser.add_argument('--librelane', default='librelane')
    parser.add_argument('--period', type=float, default=25)
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--tag', default='', help='Suffix for a fresh run after RTL/config changes')
    args = parser.parse_args()
    if args.tag and not re.fullmatch(r'[A-Za-z0-9_-]+', args.tag):
        parser.error('Tag may contain only letters, digits, underscores and hyphens')
    if args.period <= 0 or args.jobs < 1:
        parser.error('Period and job count must be positive')
    tool = subprocess.check_output([args.librelane, '--version'], text=True).splitlines()[0]
    tt_commit = subprocess.check_output(['git', '-C', str(args.tt_dir), 'rev-parse', 'HEAD'], text=True).strip()
    sizes = (args.tt_dir / 'tech/sky130A/tile_sizes.yaml').read_text()
    rows = []
    for name in args.configs:
        dest = ROOT / 'reports/physical-runs' / (f'{name}-{args.period:g}ns' + (f'-{args.tag}' if args.tag else ''))
        if (dest / 'runs' / name).exists():
            parser.error(f'Run already exists at {dest}; choose a fresh --tag')
        dest.mkdir(parents=True, exist_ok=True)
        config = json.loads((ROOT / 'src/config.json').read_text())
        config.pop('//', None)
        config.update(DESIGN_NAME=TOP,
                      VERILOG_FILES=[str(ROOT / 'src' / source) for source in SOURCES],
                      VERILOG_INCLUDE_DIRS=[str(ROOT / 'src')],
                      VERILOG_DEFINES=[f'MAC_{k}={v}' for k, v in CONFIGS[name].items()],
                      DIE_AREA=re.search(r'^'+TILES[name]+r': "([^"]+)"', sizes, re.M)[1],
                      FP_DEF_TEMPLATE=str((args.tt_dir / f'tech/sky130A/def/tt_block_{TILES[name]}_pg.def').resolve()),
                      VDD_PIN='VPWR', GND_PIN='VGND', RT_MAX_LAYER='met4', CLOCK_PERIOD=args.period)
        config_path = dest / 'config.json'
        config_path.write_text(json.dumps(config, indent=2)+'\n')
        # No --overwrite: previous measurements must not be silently discarded.
        with (dest / 'run.log').open('w') as log:
            result = subprocess.run([args.librelane, '--manual-pdk', '--pdk-root', str(args.pdk_root.resolve()),
                                     '--run-tag', name, '--condensed', '-j', str(args.jobs), str(config_path)],
                                    stdout=log, stderr=subprocess.STDOUT)
        rows.append(collect(name, dest / 'runs' / name, result.returncode == 0, args.period))
        save(rows, tool, args.pdk_root, tt_commit)
        print(json.dumps(rows[-1], indent=2), flush=True)
    raise SystemExit(0 if all(row['passed'] for row in rows) else 1)


if __name__ == '__main__':
    main()
