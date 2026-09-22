// SPDX-License-Identifier: Apache-2.0
`default_nettype none

// A[ROWS,K] @ B[K,COLS]. Byte-serial host interface, parallel systolic edges.
module mac_accelerator #(
    parameter DATA_W = 8,
    parameter ACC_W = 24,
    parameter ROWS = 2,
    parameter COLS = 2,
    parameter K = 2
) (
    input wire clk, rst_n, enable,
    input wire [2:0] command,
    input wire [7:0] data_in,
    output wire [7:0] data_out,
    output wire busy, done, load_ready,
    output reg error
);
    generate
        if (K < 1) begin: invalid_inner_dimension
            initial $fatal(1, "mac_accelerator requires K >= 1");
        end
    endgenerate
    localparam IN_BYTES = (DATA_W+7)/8;
    localparam OUT_BYTES = (ACC_W+7)/8;
    localparam WORDS = ROWS*K + K*COLS;
    localparam RESULT_BYTES = ROWS*COLS*OUT_BYTES;
    localparam RUN_CYCLES = K+ROWS+COLS-2;
    localparam WORD_CW = (WORDS < 2) ? 1 : $clog2(WORDS+1);
    localparam ADDR_W = (WORDS < 2) ? 1 : $clog2(WORDS);
    localparam BYTE_CW = (IN_BYTES < 2) ? 1 : $clog2(IN_BYTES);
    localparam OUT_CW = (RESULT_BYTES < 2) ? 1 : $clog2(RESULT_BYTES);
    localparam STEP_CW = (RUN_CYCLES < 2) ? 1 : $clog2(RUN_CYCLES);
    localparam LAST_INPUT_BYTE = IN_BYTES-1;
    localparam LAST_OUTPUT_BYTE = RESULT_BYTES-1;
    localparam LAST_STEP = RUN_CYCLES-1;
    localparam LOAD = 2'd0, RUN = 2'd1, CAPTURE = 2'd2, DONE = 2'd3;
    localparam NOP = 3'd0, WRITE = 3'd1, START = 3'd2, NEXT = 3'd3, CLEAR = 3'd4;

    reg [1:0] state;
    reg [WORD_CW-1:0] word_index;
    reg [BYTE_CW-1:0] byte_index;
    reg [OUT_CW-1:0] output_index;
    reg [STEP_CW-1:0] step;
    // Every byte must be written before START; no reset network on operand storage.
    reg [IN_BYTES*8-1:0] operands [0:WORDS-1];
    reg [RESULT_BYTES*8-1:0] output_buffer;
    wire [ROWS*COLS*ACC_W-1:0] results;
    wire [RESULT_BYTES*8-1:0] padded_results;
    wire start_ok = command == START &&
                    ((state == LOAD && word_index == WORDS) || state == DONE);
    wire array_clear = command == CLEAR || start_ok;
    reg [ROWS*DATA_W-1:0] a_edge;
    reg [COLS*DATA_W-1:0] b_edge;
    reg [ROWS-1:0] a_valid;
    reg [COLS-1:0] b_valid;
    wire [31:0] step_value = {{(32-STEP_CW){1'b0}}, step};
    integer r, c;

    assign busy = state == RUN || state == CAPTURE;
    assign done = state == DONE;
    assign load_ready = state == LOAD && word_index < WORDS;
    assign data_out = done ? output_buffer[output_index*8 +: 8] : 8'd0;
    // At enabled step t, inject A[r,t-r] and B[t-c,c]. A and B for term k
    // meet in PE(r,c) at t=k+r+c, after r+c registered hops in total.
    always @* begin
        a_edge = 0;
        b_edge = 0;
        a_valid = 0;
        b_valid = 0;
        for (r = 0; r < ROWS; r = r+1) begin
            if (state == RUN && step_value >= r && step_value < r+K) begin
                a_edge[r*DATA_W +: DATA_W] = operands[r*K+step_value-r][DATA_W-1:0];
                a_valid[r] = 1'b1;
            end
        end
        for (c = 0; c < COLS; c = c+1) begin
            if (state == RUN && step_value >= c && step_value < c+K) begin
                b_edge[c*DATA_W +: DATA_W] = operands[ROWS*K+(step_value-c)*COLS+c][DATA_W-1:0];
                b_valid[c] = 1'b1;
            end
        end
    end
    systolic_array #(.DATA_W(DATA_W), .ACC_W(ACC_W), .ROWS(ROWS), .COLS(COLS)) array (
        .clk(clk), .rst_n(rst_n), .enable(enable && (state == RUN || array_clear)),
        .clear(array_clear), .a_edge(a_edge), .b_edge(b_edge),
        .a_valid(a_valid), .b_valid(b_valid), .results(results)
    );
    genvar i;
    generate
        for (i = 0; i < ROWS*COLS; i = i+1) begin: pad
            assign padded_results[i*OUT_BYTES*8 +: OUT_BYTES*8] =
                {{(OUT_BYTES*8-ACC_W){1'b0}}, results[i*ACC_W +: ACC_W]};
        end
    endgenerate

    always @(posedge clk) begin
        if (!rst_n) begin
            state <= LOAD;
            word_index <= 0;
            byte_index <= 0;
            output_index <= 0;
            output_buffer <= 0;
            step <= 0;
            error <= 0;
        end else if (enable) begin
            if (command == CLEAR) begin
                state <= LOAD;
                word_index <= 0;
                byte_index <= 0;
                output_index <= 0;
                output_buffer <= 0;
                step <= 0;
                error <= 0;
            end else begin
                if (state == RUN) begin
                    if (step == LAST_STEP[STEP_CW-1:0])
                        state <= CAPTURE;
                    else
                        step <= step + 1'b1;
                end
                if (state == CAPTURE) begin
                    output_buffer <= padded_results;
                    output_index <= 0;
                    state <= DONE;
                end
                case (command)
                    NOP: begin end
                    WRITE: begin
                        if (load_ready) begin
                            operands[word_index[ADDR_W-1:0]][byte_index*8 +: 8] <= data_in;
                            if (byte_index == LAST_INPUT_BYTE[BYTE_CW-1:0]) begin
                                byte_index <= 0;
                                word_index <= word_index + 1'b1;
                            end else
                                byte_index <= byte_index + 1'b1;
                        end else error <= 1;
                    end
                    START: begin
                        if (start_ok) begin
                            state <= RUN;
                            step <= 0;
                            output_index <= 0;
                        end else error <= 1;
                    end
                    NEXT: begin
                        if (done) begin
                            if (output_index == LAST_OUTPUT_BYTE[OUT_CW-1:0]) begin
                                state <= LOAD;
                                word_index <= 0;
                                byte_index <= 0;
                                output_index <= 0;
                            end else output_index <= output_index + 1'b1;
                        end else error <= 1;
                    end
                    default: error <= 1;
                endcase
            end
        end
    end
endmodule
