// SPDX-License-Identifier: Apache-2.0
`default_nettype none

// One output-stationary PE. Data and valid bits move one hop per enabled edge.
module mac_pe #(
    parameter DATA_W = 8,
    parameter ACC_W = 24
) (
    input wire clk, rst_n, enable, clear,
    input wire signed [DATA_W-1:0] a_in, b_in,
    input wire a_valid_in, b_valid_in,
    output reg signed [DATA_W-1:0] a_out, b_out,
    output reg a_valid_out, b_valid_out,
    output reg signed [ACC_W-1:0] acc
);
    generate
        if (DATA_W < 1 || ACC_W < 2*DATA_W) begin: invalid_parameters
            initial $fatal(1, "mac_pe requires DATA_W >= 1 and ACC_W >= 2*DATA_W");
        end
    endgenerate
    wire signed [2*DATA_W-1:0] product = a_in * b_in;
    wire signed [ACC_W-1:0] extended_product =
        {{(ACC_W-2*DATA_W){product[2*DATA_W-1]}}, product};
    always @(posedge clk) begin
        if (!rst_n) begin
            a_out <= 0;
            b_out <= 0;
            a_valid_out <= 0;
            b_valid_out <= 0;
            acc <= 0;
        end else if (enable) begin
            if (clear) begin
                a_out <= 0;
                b_out <= 0;
                a_valid_out <= 0;
                b_valid_out <= 0;
                acc <= 0;
            end else begin
                a_out <= a_in;
                b_out <= b_in;
                a_valid_out <= a_valid_in;
                b_valid_out <= b_valid_in;
                if (a_valid_in && b_valid_in)
                    acc <= acc + extended_product;
            end
        end
    end
endmodule
