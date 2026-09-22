import random
import cocotb
from helpers import DATA_W, ACC_W, ROWS, COLS, K, packed, signed, golden, tick


@cocotb.test()
async def wavefront_partial_sums(dut):
    rng = random.Random(842)
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.enable.value = 1
    dut.clear.value = 0
    dut.a_edge.value = 0
    dut.b_edge.value = 0
    dut.a_valid.value = 0
    dut.b_valid.value = 0
    await tick(dut)
    dut.rst_n.value = 1
    for _ in range(25):
        a = [[rng.randrange(-(1 << (DATA_W-1)), 1 << (DATA_W-1)) for _ in range(K)] for _ in range(ROWS)]
        b = [[rng.randrange(-(1 << (DATA_W-1)), 1 << (DATA_W-1)) for _ in range(COLS)] for _ in range(K)]
        dut.clear.value = 1
        await tick(dut)
        dut.clear.value = 0
        expected = [0] * (ROWS*COLS)
        for t in range(K+ROWS+COLS):  # includes two drain bubbles
            av = [0 <= t-r < K for r in range(ROWS)]
            bv = [0 <= t-c < K for c in range(COLS)]
            dut.a_edge.value = packed([a[r][t-r] if av[r] else 0 for r in range(ROWS)], DATA_W)
            dut.b_edge.value = packed([b[t-c][c] if bv[c] else 0 for c in range(COLS)], DATA_W)
            dut.a_valid.value = packed(av, 1)
            dut.b_valid.value = packed(bv, 1)
            if rng.randrange(2):
                dut.enable.value = 0
                old = int(dut.results.value)
                await tick(dut)
                assert int(dut.results.value) == old
            dut.enable.value = 1
            await tick(dut)
            for r in range(ROWS):
                for c in range(COLS):
                    k = t-r-c
                    if 0 <= k < K:
                        i = r*COLS+c
                        expected[i] = signed(expected[i]+a[r][k]*b[k][c], ACC_W)
            assert int(dut.results.value) == packed(expected, ACC_W), f'Wavefront mismatch at t={t}'
        assert expected == golden(a, b)
