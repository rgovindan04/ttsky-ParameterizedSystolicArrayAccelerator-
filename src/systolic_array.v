// SPDX-License-Identifier: Apache-2.0
`default_nettype none

module systolic_array #(
    parameter DATA_W = 8,
    parameter ACC_W = 24,
    parameter ROWS = 2,
    parameter COLS = 2
) (
    input wire clk, rst_n, enable, clear,
    input wire [ROWS*DATA_W-1:0] a_edge,
    input wire [COLS*DATA_W-1:0] b_edge,
    input wire [ROWS-1:0] a_valid,
    input wire [COLS-1:0] b_valid,
    output wire [ROWS*COLS*ACC_W-1:0] results
);
    generate
        if (ROWS < 1 || COLS < 1) begin: invalid_dimensions
            initial $fatal(1, "systolic_array requires positive ROWS and COLS");
        end
    endgenerate
    wire [DATA_W-1:0] a_link [0:ROWS*(COLS+1)-1];
    wire a_vlink [0:ROWS*(COLS+1)-1];
    wire [DATA_W-1:0] b_link [0:(ROWS+1)*COLS-1];
    wire b_vlink [0:(ROWS+1)*COLS-1];
    genvar r, c;
    generate
        for (r = 0; r < ROWS; r = r+1) begin: row
            assign a_link[r*(COLS+1)] = a_edge[r*DATA_W +: DATA_W];
            assign a_vlink[r*(COLS+1)] = a_valid[r];
            for (c = 0; c < COLS; c = c+1) begin: col
                mac_pe #(.DATA_W(DATA_W), .ACC_W(ACC_W)) pe (
                    .clk(clk), .rst_n(rst_n), .enable(enable), .clear(clear),
                    .a_in(a_link[r*(COLS+1)+c]), .b_in(b_link[r*COLS+c]),
                    .a_valid_in(a_vlink[r*(COLS+1)+c]),
                    .b_valid_in(b_vlink[r*COLS+c]),
                    .a_out(a_link[r*(COLS+1)+c+1]),
                    .b_out(b_link[(r+1)*COLS+c]),
                    .a_valid_out(a_vlink[r*(COLS+1)+c+1]),
                    .b_valid_out(b_vlink[(r+1)*COLS+c]),
                    .acc(results[(r*COLS+c)*ACC_W +: ACC_W])
                );
            end
        end
        for (c = 0; c < COLS; c = c+1) begin: boundary
            assign b_link[c] = b_edge[c*DATA_W +: DATA_W];
            assign b_vlink[c] = b_valid[c];
        end
    endgenerate
endmodule
