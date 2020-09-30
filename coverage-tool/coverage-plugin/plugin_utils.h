/*!
##############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################
*/
#ifndef _COVERAGE_TOOL_COVERAGE_PLUGIN_PLUGIN_UTILS_H_
#define _COVERAGE_TOOL_COVERAGE_PLUGIN_PLUGIN_UTILS_H_

#include <sstream>
#include <map>
#include <vector>
#include <string>
#include "MTI/ModelTraceInterface.h"
using namespace eslapi;
using namespace MTI;
using namespace std;

typedef struct {
    const char *name;
    MTI::ValueIndex *index;
} ValueBind_t;

// Declare an MTI callback method and define a static thunk method to call
// into this from C code.
#define CALLBACK_DECL_AND_THUNK(class_name, name) \
    static void name##Thunk(void * user_data, const MTI::EventClass *event_class, const MTI::EventRecord *record) \
    {                                                                                                   \
        reinterpret_cast<class_name *>(user_data)->name(event_class, record);                           \
    }                                                                                                   \
    void name(const MTI::EventClass *event_class, const MTI::EventRecord *record)


// Get a named trace source, create an event class from the named subset of
// event fields, register the event class and look up the field indexes, and
// register a user-provided MTI callback with the trace source.
// Writes to error_ss and returns false if anything fails.
bool RegisterCallbackForComponent(const MTI::ComponentTraceInterface *mti,
                         const char *trace_source,
                         ValueBind_t *value_bind, void *this_ptr,
                         MTI::CallbackT callback,
                         MTI::EventClass **ptr_event_class,
                         std::stringstream &error_ss);

#endif // _COVERAGE_TOOL_COVERAGE_PLUGIN_PLUGIN_UTILS_H_
