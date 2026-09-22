module alu (
    input  wire [3:0] a,
    input  wire [3:0] b,
    input  wire [2:0] op,
    output wire [3:0] y,
    output wire       carry
);

wire [4:0] add_res;
wire [4:0] sub_res;

assign add_res = a + b;
assign sub_res = a - b;

assign y =
       (op == 3'b000) ? add_res[3:0] :
       (op == 3'b001) ? sub_res[3:0] :
       (op == 3'b010) ? (a & b) :
       (op == 3'b011) ? (a | b) :
       (op == 3'b100) ? (a ^ b) :
       (op == 3'b101) ? (~a) :
       (op == 3'b110) ? (a << 1) :
       (op == 3'b111) ? (a >> 1) :
                        4'b0000;

assign carry =
       (op == 3'b000) ? add_res[4] :
       (op == 3'b001) ? sub_res[4] :
                        1'b0;

endmodule