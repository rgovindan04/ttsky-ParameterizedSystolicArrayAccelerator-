"""Public-pin tests, shared by RTL and the TinyTapeout gate-level action."""
import random
import cocotb
from helpers import DATA_W, ACC_W, ROWS, COLS, K, golden, signed, tick

NOP, WRITE, START, NEXT, CLEAR = range(5)
BUSY, DONE, READY, ERROR = 0x10, 0x20, 0x40, 0x80
IN_BYTES, OUT_BYTES = (DATA_W + 7) // 8, (ACC_W + 7) // 8
RUN_CYCLES = K + ROWS + COLS - 2


def status(dut):
    assert int(dut.uio_oe.value) == 0xf0
    assert int(dut.uio_out.value) & 0x0f == 0
    return int(dut.uio_out.value)


async def command(dut, cmd=NOP, byte=0, enable=1):
    dut.ena.value = enable
    dut.uio_in.value = cmd
    dut.ui_in.value = byte
    await tick(dut)


async def reset(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    await command(dut, enable=0)
    await command(dut, enable=0)
    dut.rst_n.value = 1
    await command(dut)
    assert status(dut) == READY
    assert int(dut.uo_out.value) == 0


def bytes_for(a, b):
    for matrix in (a, b):
        for row in matrix:
            for value in row:
                value &= (1 << DATA_W) - 1
                for i in range(IN_BYTES):
                    yield (value >> (8*i)) & 255


async def load(dut, a, b, rng=None):
    for index, byte in enumerate(bytes_for(a, b)):
        if rng and DATA_W % 8 and index % IN_BYTES == IN_BYTES-1:
            byte |= rng.randrange(1 << (8-DATA_W % 8)) << (DATA_W % 8)
        assert status(dut) & READY
        if rng and rng.randrange(3) == 0:
            await command(dut, WRITE, 255, enable=0)
            await command(dut, NOP)
        await command(dut, WRITE, byte)
    assert not status(dut) & READY


async def run(dut, stalls=False, expected_error=False):
    await command(dut, START)
    assert status(dut) & BUSY
    for cycle in range(RUN_CYCLES + 1):
        assert status(dut) & BUSY
        assert not status(dut) & DONE
        if stalls:
            before = status(dut)
            await command(dut, CLEAR, enable=0)
            assert status(dut) == before
        await command(dut)
        assert bool(status(dut) & DONE) == (cycle == RUN_CYCLES)
    assert not status(dut) & BUSY
    assert bool(status(dut) & ERROR) == expected_error


async def read(dut, expected, rng=None):
    for value in expected:
        raw = 0
        for byte_index in range(OUT_BYTES):
            assert status(dut) & DONE
            byte = int(dut.uo_out.value)
            if rng:
                for _ in range(rng.randrange(3)):
                    await command(dut)
                    assert int(dut.uo_out.value) == byte
                await command(dut, NEXT, enable=0)
                assert int(dut.uo_out.value) == byte
            raw |= byte << (8*byte_index)
            await command(dut, NEXT)
        assert raw >> ACC_W == 0, 'padding above accumulator must be zero'
        assert signed(raw, ACC_W) == value, (raw, value)
    assert status(dut) & READY
    assert not status(dut) & DONE
    assert int(dut.uo_out.value) == 0


@cocotb.test()
async def matrix_golden_model(dut):
    rng = random.Random(0x5A1701)
    await reset(dut)
    low, high = -(1 << (DATA_W-1)), (1 << (DATA_W-1))-1
    cases = []
    for av, bv in [(0, 0), (1, 1), (-1, 1), (low, low), (low, high), (high, high)]:
        cases.append(([[av]*K for _ in range(ROWS)], [[bv]*COLS for _ in range(K)]))
    cases.append(([[int(r == k) for k in range(K)] for r in range(ROWS)],
                  [[signed(k*COLS+c+1, DATA_W) for c in range(COLS)] for k in range(K)]))
    for _ in range(40):
        cases.append(([[rng.randint(low, high) for _ in range(K)] for _ in range(ROWS)],
                      [[rng.randint(low, high) for _ in range(COLS)] for _ in range(K)]))
    for i, (a, b) in enumerate(cases):
        await load(dut, a, b, rng)
        await run(dut, stalls=i % 3 == 0)
        await read(dut, golden(a, b), rng)
    dut._log.info('Verified %d matrix products against NumPy', len(cases))


@cocotb.test()
async def protocol_errors_abort_reset_and_reuse(dut):
    await reset(dut)
    a = [[signed(r*K+k+1, DATA_W) for k in range(K)] for r in range(ROWS)]
    b = [[signed(-k*COLS-c-1, DATA_W) for c in range(COLS)] for k in range(K)]
    for invalid in (START, NEXT, 5, 6, 7):
        await command(dut, invalid)
        assert status(dut) == READY | ERROR
        await command(dut, CLEAR)
        assert status(dut) == READY
    data = list(bytes_for(a, b))
    for byte in data[:-1]:
        await command(dut, WRITE, byte)
    await command(dut, START)
    assert status(dut) == READY | ERROR
    await command(dut, WRITE, data[-1])
    await command(dut, WRITE, 0)  # overflow must not replace operands
    await run(dut, expected_error=True)
    first = int(dut.uo_out.value)
    await command(dut, WRITE, 0)
    assert status(dut) == DONE | ERROR
    assert int(dut.uo_out.value) == first
    if ROWS*COLS*OUT_BYTES > 1:
        await command(dut, NEXT)
    await run(dut, expected_error=True)  # replay loaded matrices from DONE
    await read(dut, golden(a, b))
    await command(dut, CLEAR)
    await load(dut, a, b)
    await command(dut, START)
    await command(dut, WRITE, 255)  # illegal while busy; computation continues
    assert status(dut) & ERROR
    for _ in range(RUN_CYCLES):
        await command(dut)
    assert status(dut) == DONE | ERROR
    await read(dut, golden(a, b))
    # Abort at every possible compute/capture position and verify recovery.
    for delay in range(RUN_CYCLES+1):
        await command(dut, CLEAR)
        await load(dut, a, b)
        await command(dut, START)
        for _ in range(delay):
            await command(dut)
        await command(dut, CLEAR)
        assert status(dut) == READY
        await load(dut, a, b)
        await run(dut)
        await read(dut, golden(a, b))
    await load(dut, a, b)
    await command(dut, START)
    await reset(dut)  # reset takes priority even with ena low
    await load(dut, a, b)
    await run(dut)
    await read(dut, golden(a, b))
