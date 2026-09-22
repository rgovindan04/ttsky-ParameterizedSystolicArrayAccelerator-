# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer


def golden(a: int, b: int, op: int):
    """Return (y, carry) matching alu.v behavior."""
    a &= 0xF
    b &= 0xF
    op &= 0x7

    if op == 0b000:  # add
        r = a + b
        return (r & 0xF, (r >> 4) & 1)
    if op == 0b001:  # sub (matches your sub_res[4])
        r = (a - b) & 0x1F
        return (r & 0xF, (r >> 4) & 1)
    if op == 0b010:
        return (a & b, 0)
    if op == 0b011:
        return (a | b, 0)
    if op == 0b100:
        return (a ^ b, 0)
    if op == 0b101:
        return ((~a) & 0xF, 0)
    if op == 0b110:
        return ((a << 1) & 0xF, 0)
    if op == 0b111:
        return ((a >> 1) & 0xF, 0)
    return (0, 0)


@cocotb.test()
async def test_alu_exhaustive(dut):
    dut._log.info("Start ALU exhaustive test")

    # Clock (tb.v provides clk even if design is combinational)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    tests = 0

    for op in range(8):
        for a in range(16):
            for b in range(16):
                # Pack A/B into ui_in: ui_in[3:0]=A, ui_in[7:4]=B
                ui = (b << 4) | a

                # Put op in uio_in[2:0]
                uio = op

                dut.ui_in.value = ui
                dut.uio_in.value = uio

                # combinational: tiny delay is enough
                await Timer(1, unit="ns")

                got_y = int(dut.uo_out.value) & 0xF
                got_c = (int(dut.uo_out.value) >> 4) & 1

                exp_y, exp_c = golden(a, b, op)

                assert got_y == exp_y, (
                    f"Y mismatch op={op:03b} a={a} b={b} "
                    f"ui_in=0x{ui:02x} got_y=0x{got_y:x} exp_y=0x{exp_y:x}"
                )

                assert got_c == exp_c, (
                    f"CARRY mismatch op={op:03b} a={a} b={b} "
                    f"ui_in=0x{ui:02x} got_c={got_c} exp_c={exp_c}"
                )

                tests += 1

    dut._log.info(f"ALL TESTS PASSED ({tests} cases)")