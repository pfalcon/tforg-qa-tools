/*!
##############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################
*/

#include "plugin_utils.h"

// Get a named trace source, create an event class from the named subset of
// event fields, register the event class and look up the field indexes, and
// register a user-provided MTI callback with the trace source.
// Writes to error_ss and returns false if anything fails.
bool RegisterCallbackForComponent(const MTI::ComponentTraceInterface *mti,
                         const char *trace_source,
                         ValueBind_t *value_bind, void *this_ptr,
                         MTI::CallbackT callback,
                         MTI::EventClass **ptr_event_class,
                         std::stringstream &error_ss)
{
    const MTI::TraceSource *source = mti->GetTraceSource(trace_source);
    if (!source) {
        error_ss << "Could not find " << trace_source << " source";
        return false;
    }

    MTI::FieldMask mask = 0;
    const MTI::EventFieldType *eft;

    for(unsigned i=0; value_bind[i].name != 0; i++) {
        if ((eft = source->GetField( value_bind[i].name )) != 0) {
            mask |= 1 << eft->GetIndex();
        } else {
            error_ss << "No field " << value_bind[i].name <<
                    " found in " << trace_source << " trace source";
            return false;
        }
    }

    MTI::EventClass *event_class = source->CreateEventClass(mask);
    if (!event_class) {
        error_ss << "Unable to register event class for " <<
                trace_source << " trace source.";
        return false;
    }
    for(unsigned i=0; value_bind[i].name != 0; i++)
    {
        MTI::ValueIndex idx = event_class->GetValueIndex(value_bind[i].name);
        if (idx != -1) {
            *(value_bind[i].index) = idx;
       } else {
           error_ss << "Unable to GetValueIndex for " << trace_source
                    << "." << value_bind[i].name << ".";
           return false;
       }
    }
    if (callback &&
        event_class->RegisterCallback(callback, this_ptr) != MTI::MTI_OK) {
        error_ss << "RegisterCallback failed for " << trace_source;
        return false;
    }
    *ptr_event_class = event_class;
    return true;
}
