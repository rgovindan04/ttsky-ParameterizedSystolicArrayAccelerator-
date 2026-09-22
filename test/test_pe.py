import random
import cocotb
from helpers import DATA_W, ACC_W, signed, tick


@cocotb.test()
async def signed_mac_forwarding_stalls_and_wrap(dut):
    rng = random.Random(721)
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.enable.value = 0
    dut.clear.value = 0
    dut.a_in.value = 0
    dut.b_in.value = 0
    dut.a_valid_in.value = 0
    dut.b_valid_in.value = 0
    await tick(dut)
    dut.rst_n.value = 1
    expected = (0, 0, 0, 0, 0)
    low, high = -(1 << (DATA_W-1)), (1 << (DATA_W-1))-1
    cases = [(a, b, 1, 1, 1, 0) for a in [low, high, -1, 0, 1] for b in [low, high, -1, 0, 1]]
    cases += [(low, low, 1, 1, 1, 0)] * 32
    cases += [(rng.randint(low, high), rng.randint(low, high), rng.randrange(2),
               rng.randrange(2), rng.randrange(2), int(rng.randrange(10) == 0)) for _ in range(400)]
    for a, b, av, bv, en, clear in cases:
        dut.a_in.value = a & ((1 << DATA_W)-1)
        dut.b_in.value = b & ((1 << DATA_W)-1)
        dut.a_valid_in.value, dut.b_valid_in.value = av, bv
        dut.enable.value, dut.clear.value = en, clear
        if en:
            expected = (0, 0, 0, 0, 0) if clear else (
                a, b, av, bv, signed(expected[4] + (a*b if av and bv else 0), ACC_W))
        await tick(dut)
        got = (signed(int(dut.a_out.value), DATA_W), signed(int(dut.b_out.value), DATA_W),
               int(dut.a_valid_out.value), int(dut.b_valid_out.value), signed(int(dut.acc.value), ACC_W))
        assert got == expected, (got, expected)
