// SPDX-License-Identifier: Apache-2.0
`default_nettype none
`include "config.vh"

module tt_um_rishigovindan_systolic (
    input wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input wire ena, clk, rst_n
);
    wire busy, done, load_ready, error;
    mac_accelerator #(
        .DATA_W(`MAC_DATA_W), .ACC_W(`MAC_ACC_W),
        .ROWS(`MAC_ROWS), .COLS(`MAC_COLS), .K(`MAC_K)
    ) accelerator (
        .clk(clk), .rst_n(rst_n), .enable(ena),
        .command(uio_in[2:0]), .data_in(ui_in), .data_out(uo_out),
        .busy(busy), .done(done), .load_ready(load_ready), .error(error)
    );
    assign uio_oe = 8'hf0;
    assign uio_out = {error, load_ready, done, busy, 4'b0000};
    wire _unused = &{uio_in[7:3], 1'b0};
endmodule
