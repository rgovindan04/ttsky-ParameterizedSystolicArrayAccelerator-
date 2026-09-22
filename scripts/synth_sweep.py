#!/usr/bin/env python3
"""Yosys architecture sweep; generic cell counts are not physical area/timing."""
import argparse
import json
import hashlib
from pathlib import Path
import subprocess
from configurations import CONFIGS, validate

ROOT = Path(__file__).resolve().parents[1]
TOP = 'tt_um_rishigovindan_systolic'
SOURCES = ['project.v', 'mac_pe.v', 'systolic_array.v', 'mac_accelerator.v']


def performance(p):
    r, c, k = p['ROWS'], p['COLS'], p['K']
    cycles = k+r+c-2
    serial_cycles = (r*k+k*c)*((p['DATA_W']+7)//8) + 1 + cycles + 1 + r*c*((p['ACC_W']+7)//8)
    return dict(macs=r*c*k, peak_macs_per_cycle=r*c, array_cycles=cycles,
                start_to_done_cycles=cycles+1, transaction_cycles=serial_cycles,
                macs_per_transaction_cycle=r*c*k/serial_cycles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configs', nargs='*', help='Configuration names; omit for the standard sweep')
    parser.add_argument('--liberty', type=Path, help='Optional technology library for mapped cell area, not routed timing')
    args = parser.parse_args()
    args.configs = args.configs or ['tiny', 'small', 'default', 'wide_acc', 'rectangular']
    for name in args.configs:
        if name not in CONFIGS:
            parser.error(f'Unknown configuration: {name}')
    dest = ROOT / 'reports' / 'synthesis'
    dest.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output(['yosys', '-V'], text=True).strip()
    rows = []
    for name in args.configs:
        p = CONFIGS[name]
        validate(p)
        defines = ' '.join(f'-DMAC_{k}={v}' for k, v in p.items())
        lines = [f'read_verilog -sv -I{ROOT / "src"} {defines} ' + ' '.join(str(ROOT / 'src' / f) for f in SOURCES),
                 f'synth -top {TOP} -flatten', 'check -assert']
        if args.liberty:
            lines += [f'dfflibmap -liberty {args.liberty.resolve()}', f'abc -liberty {args.liberty.resolve()}', 'clean']
        lines += [f'tee -o {dest / (name + ".json")} stat -json' + (f' -liberty {args.liberty.resolve()}' if args.liberty else '')]
        script = dest / (name + '.ys')
        script.write_text('\n'.join(lines)+'\n')
        subprocess.run(['yosys', '-Q', '-T', '-l', str(dest / (name+'.log')), str(script)], check=True, stdout=subprocess.DEVNULL)
        stats = json.loads((dest / (name+'.json')).read_text())['design']
        row = dict(name=name, **p, cells=stats['num_cells'], **performance(p))
        if 'area' in stats:
            row['mapped_cell_area_um2'] = stats['area']
        rows.append(row)
        print(f'{name}: {row}', flush=True)
    summary = dict(tool=version, liberty=args.liberty.name if args.liberty else None,
                   liberty_sha256=hashlib.sha256(args.liberty.read_bytes()).hexdigest() if args.liberty else None, configurations=rows,
                   note='Generic cells unless liberty specified. No placement, routing, STA or timing closure implied.')
    (ROOT / 'reports' / 'synthesis.json').write_text(json.dumps(summary, indent=2)+'\n')
    md = ['# Synthesis and schedule comparison', '', version, '',
          ('Mapped with `' + args.liberty.name + '`; library SHA-256: `' + summary['liberty_sha256'] + '`. ' if args.liberty else '') + summary['note'], '',
          '| Configuration | DATA/ACC | R×C×K | Cells | Mapped area (µm²) | Array cycles | START→DONE | Transaction cycles | MAC/cycle incl. IO |',
          '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        md.append(f'| {r["name"]} | {r["DATA_W"]}/{r["ACC_W"]} | {r["ROWS"]}×{r["COLS"]}×{r["K"]} | {r["cells"]} | {r.get("mapped_cell_area_um2", "—")} | {r["array_cycles"]} | {r["start_to_done_cycles"]} | {r["transaction_cycles"]} | {r["macs_per_transaction_cycle"]:.4f} |')
    md += ['', 'Transaction cycles include all input bytes, START, systolic fill/compute/drain, one result-capture edge, and all output acknowledgments. No host stalls or reset. One MAC is one multiply plus one add.', '']
    (ROOT / 'reports' / 'synthesis.md').write_text('\n'.join(md))


if __name__ == '__main__':
    main()
