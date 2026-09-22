## How it works

This accelerator computes signed `C[ROWS,COLS] = A[ROWS,K] × B[K,COLS]`.
The default configuration is DATA_W=8, ACC_W=24, ROWS=2, COLS=2, K=2.
Each processing element (PE) stores one sum, multiplies signed operands, and
forwards A to its right neighbor and B to its lower neighbor on each enabled
clock. Accumulators use two's-complement wraparound; there is no saturation.

At array step `t`, the controller injects `A[r,t-r]` into row r and `B[t-c,c]`
into column c, only when the inner index is within `[0,K)`. A matched pair for
term k therefore reaches PE(r,c) at `t=k+r+c`. Valid bits travel with operands;
bubbles do not accumulate. Inputs pass through neighboring PEs, so this is a
systolic fabric with registered movement and spatial reuse.

For the default matrix size, the four compute steps are:

| Array step | PE(0,0) | PE(0,1) | PE(1,0) | PE(1,1) |
|---|---|---|---|---|
| 0 | k=0 | — | — | — |
| 1 | k=1 | k=0 | k=0 | — |
| 2 | — | k=1 | k=1 | k=0 |
| 3 | — | — | — | k=1 |

START clears the fabric. The next `K+ROWS+COLS-2` enabled edges perform
fill/compute/drain, and one further edge captures the completed accumulators in
an output buffer and asserts DONE. Thus default DONE becomes high five enabled
edges after the START edge. The final MAC is captured on a separate edge to
respect registered accumulator updates.

### Parameters and buffering

The reusable PE and fabric accept width/dimension parameters; the controller also
accepts K. `src/config.vh` selects the TinyTapeout wrapper's synthesis defaults.
Parameters are fixed at synthesis, not programmable through pins. DATA_W must be
positive, ACC_W at least twice DATA_W, and ROWS/COLS/K positive. For guaranteed
full precision, allow `2*DATA_W + ceil(log2(K))` accumulator bits.

The implementation has one operand buffer and one result snapshot buffer; loading,
computing, and output consumption are sequential. It does not overlap independent
matrices. Peak fabric capacity is ROWS×COLS MACs per cycle, but fill/drain and the
byte interface reduce sustained throughput. One MAC means one multiply plus add.

A no-stall transaction costs:

`(ROWS*K + K*COLS)*ceil(DATA_W/8) + 1 + (K+ROWS+COLS-2) + 1 + ROWS*COLS*ceil(ACC_W/8)`

cycles, including input, START, computation, capture, and output acknowledgments.
The default performs eight MACs per 26 transaction cycles. Convert to MAC/s using
an actual timing-closed clock rate; the configured clock is a target.

### Pin interface

| Pins | Direction | Meaning |
|---|---|---|
| ui_in[7:0] | Input | One data byte |
| uo_out[7:0] | Output | Current result byte; zero unless DONE |
| uio_in[2:0] | Input | Command sampled on rising edges |
| uio_in[3] | Input | Reserved, ignored |
| uio_out[4] | Output | BUSY: array running or results being captured |
| uio_out[5] | Output | DONE: current result byte valid |
| uio_out[6] | Output | LOAD_READY: another input byte can be accepted |
| uio_out[7] | Output | ERROR: sticky protocol error |

`uio_oe=0xf0`; the host must not drive the upper four bidirectional pins. `ena=0`
freezes state, buffers, all PEs, and command processing. Status and output remain
stable. `rst_n=0` synchronously resets the controller and PEs regardless of ena.
Reset does not clear operand storage; START is blocked until every input byte is
written. Drive input/control signals synchronous to clk; no asynchronous CDC is
provided. Hold reset low across at least two rising edges before use.

### Commands

Commands are level sampled, **not edge detected**: holding WRITE or NEXT for
several enabled clocks transfers one byte each clock. Use NOP between transfers
when the host needs more time.

| CMD | Name | Effect |
|---|---|---|
| 0 | NOP | No host transfer; active computation continues |
| 1 | WRITE | If LOAD_READY, append ui_in byte to operand buffer |
| 2 | START | If all inputs loaded, clear PEs and begin; from DONE, rerun the retained inputs and discard the previous output snapshot |
| 3 | NEXT | Acknowledge the currently visible result byte; advance, or return to empty LOAD state after the last byte |
| 4 | CLEAR | Abort any operation; reset pointers, sums, and ERROR; return to LOAD |
| 5–7 | Reserved | Set ERROR |

WRITE without LOAD_READY, START before the full payload or while BUSY, and NEXT
without DONE set ERROR and do not perform that host operation. Computation keeps
running after illegal commands. ERROR stays set until CLEAR or reset. CLEAR has
priority even during computation or result capture. START while DONE is legal
until the last output byte has been acknowledged; afterward inputs must be
reloaded. Status outputs are state indicators even while ena is low.

### Byte order and worked example

Load every element of A in row-major order, then every element of B in row-major
order. Each element occupies `ceil(DATA_W/8)` bytes, least significant byte first.
Encode negative values in DATA_W-bit two's complement; unused upper input padding
bits are ignored. Results are row-major, each `ceil(ACC_W/8)` bytes, least
significant first. Unused high result padding bits are **zero**, even for negative
results; interpret the lower ACC_W bits as signed.

For A=`[[1,-2],[3,4]]` and B=`[[5,6],[-7,8]]`, write:

`01 fe 03 04 05 06 f9 08`

Pulse START for one enabled rising edge, then send NOP until DONE. The mathematical
result is `[[19,-10],[-13,50]]`. Observe each output byte before acknowledging it
with NEXT; the default 24-bit result stream is:

`13 00 00  f6 ff ff  f3 ff ff  32 00 00`

The first byte is already visible when DONE rises; do not issue NEXT before
reading it. The output holds indefinitely under backpressure. After the twelfth
NEXT edge, DONE drops and LOAD_READY rises for the next matrix.

## How to test

Install `test/requirements.txt`, then run `make -C test` for pin-level tests or
`python3 scripts/regress.py` for the complete regression. Tests use deterministic
random matrices plus zero, identity-like, extrema, negative, and overflow cases.
Separate PE tests check forwarding, valid bubbles, stall, clear, and wraparound;
array tests compare **every intermediate PE sum at every cycle** against the
staggered schedule. Public-pin tests cover load/output stalls, partial loads,
invalid commands, buffer overflow, reset during computation, abort at every
compute/capture position, input reuse, and consecutive transactions. The same
public-pin suite is used for TinyTapeout gate-level simulation.

## External hardware

Use a synchronous host such as an RP2040/FPGA to drive clk, reset, input bytes,
and commands, and read the output byte and status pins. No external memory is
required for the default buffered matrices.
