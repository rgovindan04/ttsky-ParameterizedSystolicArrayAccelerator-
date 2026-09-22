<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project implements a small 4-bit Arithmetic Logic Unit (ALU) in Verilog. The ALU performs several arithmetic and logical operations on two 4-bit inputs.

The inputs are two 4-bit numbers A and B, and a 3-bit operation code (op) that determines which operation the ALU performs. The result of the operation is a 4-bit output Y, along with a carry flag for arithmetic operations.

The ALU is purely combinational, meaning the output updates immediately when the inputs change. No clock is required.


## How to test

To test the ALU, apply values to the inputs A, B, and op, then observe the output Y.

A cocotb testbench is included in the repository that automatically applies several test cases and verifies the correct outputs.

To run the cocotb testbench:
cd test
make clean
make SIM=icarus

My testbench is suffecient enough because I exhaustivley test all possible outputs and compare it against a golden model.
## External hardware

No external hardware is required for this project.

The design is a simple combinational ALU that operates entirely on the TinyTapeout input and output pins.

Used GenAI tools to help configure Makefile
