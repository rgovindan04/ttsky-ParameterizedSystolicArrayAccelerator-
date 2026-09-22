SIM ?= icarus
TOPLEVEL_LANG = verilog
TOPLEVEL ?= mac_pe
COCOTB_TEST_MODULES ?= test_pe
VERILOG_SOURCES = $(CURDIR)/../src/mac_pe.v $(CURDIR)/../src/systolic_array.v
SIM_BUILD ?= sim_build/$(TOPLEVEL)
COMPILE_ARGS += -P$(TOPLEVEL).DATA_W=$(MAC_DATA_W) -P$(TOPLEVEL).ACC_W=$(MAC_ACC_W)
ifeq ($(TOPLEVEL),systolic_array)
COMPILE_ARGS += -Psystolic_array.ROWS=$(MAC_ROWS) -Psystolic_array.COLS=$(MAC_COLS)
endif
include $(shell cocotb-config --makefiles)/Makefile.sim
