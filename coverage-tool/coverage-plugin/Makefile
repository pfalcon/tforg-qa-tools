##############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

CPPFLAGS = -I${PVLIB_HOME}/include/fmruntime
CXXFLAGS = -fpic -Wall -Werror -g
LDFLAGS  =
CMAKE_CXX_FLAGS = -std=c++11 -O3

ifeq (${CROSS_COMPILE_32BIT},1)
CXXFLAGS += -m32
LDFLAGS  += -m32
endif

PLUGIN_NAME = coverage_trace

PLUGIN_LIB     = ${PLUGIN_NAME}.so
PLUGIN_OBJECTS = ${PLUGIN_NAME}.o plugin_utils.o

${PLUGIN_LIB}: ${PLUGIN_OBJECTS}
	${CXX} -shared -o $@ ${LDFLAGS} $^

.cc.o:
	${CXX} -c -o $@ ${CXXFLAGS} ${CMAKE_CXX_FLAGS} ${CPPFLAGS} $^

.PHONY: clean
clean:
	rm -f ${PLUGIN_OBJECTS} ${PLUGIN_LIB}
