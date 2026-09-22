/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_rishigovindan_alu (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,    // Dedicated outputs
    input  wire [7:0] uio_in,    // IOs: Input path
    output wire [7:0] uio_out,   // IOs: Output path
    output wire [7:0] uio_oe,    // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,       // ignore for combinational ALU
    input  wire       clk,       // ignore for combinational ALU
    input  wire       rst_n       // ignore for combinational ALU
);

  // Map TinyTapeout pins to ALU signals
  wire [3:0] a  = ui_in[3:0];
  wire [3:0] b  = ui_in[7:4];
  wire [2:0] op = uio_in[2:0];

  wire [3:0] y;
  wire       carry;

  // Instantiate ALU from src/alu.v
  alu u_alu (
      .a(a),
      .b(b),
      .op(op),
      .y(y),
      .carry(carry)
  );

  // Drive outputs
  assign uo_out[3:0] = y;
  assign uo_out[4]   = carry;
  assign uo_out[7:5] = 3'b000;

  // Keep all uio pins as inputs (only read uio_in)
  assign uio_out = 8'b0000_0000;
  assign uio_oe  = 8'b0000_0000;

  // Prevent unused warnings
  wire _unused = &{ena, clk, rst_n, uio_in[7:3], 1'b0};

endmodule