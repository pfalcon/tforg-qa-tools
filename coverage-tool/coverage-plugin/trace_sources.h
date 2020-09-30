/*!
##############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################
*/

#ifndef _COVERAGE_TOOL_COVERAGE_PLUGIN_TRACE_SOURCES_H_
#define _COVERAGE_TOOL_COVERAGE_PLUGIN_TRACE_SOURCES_H_

#include <map>
#include <vector>
#include <string>
#include <algorithm>
#include "MTI/ModelTraceInterface.h"

using namespace MTI;
using namespace std;

struct InstStat {
    uint64_t cnt;
    uint64_t size;
};

typedef std::map<uint32_t, InstStat> InstStatMap;

//Defining types for fields
enum enum_types {u32, boolT};
typedef enum_types ValueTypes;

/*
 * Structure used to save field data
 */
struct TFields{
    ValueTypes t;
    MTI::ValueIndex index;
    void *value;
};
// Map of fields => Key -> Field name
typedef map<string, TFields> TraceFieldsMap;

/*
 * Structure used to pass field data between trace contexts
 */
struct TParams {
    void *value;
    ValueTypes t;
};
// Map of fields => Key -> Field name
typedef map<string, TParams> ParamsMap;

/*
 * Generic function to output errors
 */
bool Error(const char *msg)
{
    fprintf(stderr, "%s\n", msg);
    return false;
}

/*
 * Base class for Trace Source contexts
 *
 */
class TraceSourceContext {
    public:
        string name; //Trace source name
        TraceFieldsMap fields; //Fields to be used for the event
        MTI::EventClass *event_class; //Event object to register callback
        ParamsMap params; //List of parameters from another trace source

/*
 * Constructor that converts/stores the pairs of <field name, field type>
 * in the 'fields' member.
*/
TraceSourceContext(const char* tname,
                    vector<pair<string, ValueTypes>> fields_def) {
    name = tname;
    string key;
    // Referenced by field name => field type
    for (size_t i=0; i < fields_def.size(); ++ i) {
        key = fields_def[i].first;
        fields[key].t = fields_def[i].second;
    }
}

/*
 * Generic Callback that can be used by derived objects. It fills the
 * 'value' member in the 'fields' structure with a void* to the value
 * retrieved from the component.
*/
template <class T>
static T *TraceCallback(void* user_data,
                         const MTI::EventClass *event_class,
                         const MTI::EventRecord *record) {
    T *tc = static_cast<T*>(user_data);
    // Filled by Component
    TraceFieldsMap::iterator it;
    for (it = tc->fields.begin(); it != tc->fields.end(); ++it) {
       // Based in the type creates an object with initial
       // value retrieved from the component using the index
       // for that field.
        switch (it->second.t) {
            case u32: it->second.value = new uint32_t(
                record->Get<uint32_t>(event_class, it->second.index));
                break;
            case boolT: it->second.value = new bool(
                record->GetBool(event_class, it->second.index));
                break;
        }
    }
    return tc;
}

/*
 * Generic method to copy the fields from this trace source to the params
 * member in other trace source. Optionally a list of field names can be
 * passed to filter the list of field names copied.
 * The params member is a Map of with the Field Id (name)  as the key.
*/
void PassFieldstoParams(TraceSourceContext *target,
                            vector<string> field_names={}) {
        TraceFieldsMap::iterator it;
        for (it = fields.begin(); it != fields.end(); ++it) {
            bool found = std::find(field_names.begin(), field_names.end(),
                it->first) != field_names.end();
            if ((!field_names.empty()) && (!found))
                continue;
            target->params[it->first].t = it->second.t;
            switch (it->second.t) {
                case u32:
                    target->params[it->first].value =
                        new uint32_t(*((uint32_t*)it->second.value));
                    break;
                case boolT:
                    target->params[it->first].value =
                        new bool(*((bool*)it->second.value));
                    break;
            }
        }
}
/*
 * Method that creates an event object in the trace source based in the
 * fields given in the constructor. It then registers the given callback
 * to this event.
*/
MTI::EventClass *CreateEvent(ComponentTraceInterface **ptr_cti,
                MTI::CallbackT callback) {

    ComponentTraceInterface *cti = *ptr_cti;
    std::stringstream ss;
    ComponentTraceInterface *mti = 0;

    if (cti->GetTraceSource(name.c_str()) != 0) {
        TraceSource* ts = cti->GetTraceSource(name.c_str());
        printf("Trace source attached: %s\n", ts->GetName());

        size_t map_size = fields.size();
        ValueBind_t *values_array = new ValueBind_t[map_size + 1];
        TraceFieldsMap::iterator it;
        int i = 0;
        for (it = fields.begin(); it != fields.end(); ++it) {
            values_array[i]= ((ValueBind_t) { it->first.c_str(),
                &it->second.index });
            ++i;
        };
        values_array[map_size] = {0, 0}; //sentinel

        mti = static_cast<ModelTraceInterface *>(cti);
        if (!RegisterCallbackForComponent(mti, name.c_str(), values_array,
            this, callback, &event_class, ss)) {
            Error(ss.str().c_str());
            return 0;
        }
        return event_class;
    }
    return 0;
}
};

/*
 * Class and types used to handle trace sources belonging to a
 * component.
*/
typedef map<string, TraceSourceContext*> MapTraceSourcesType;
class TraceComponentContext {
    public:
        string trace_path;
        MapTraceSourcesType trace_sources;

TraceComponentContext(string tpath) {
        trace_path = tpath;
}

void AddTraceSource(TraceSourceContext *ts) {
        trace_sources[ts->name] = ts;
}
};

/*
 * Class used to instantiate a Instruction trace source
*/
class InstructionTraceContext: public TraceSourceContext {
    public:
        using TraceSourceContext::TraceSourceContext;
        InstStatMap stats;
        uint64_t nb_insts;

    static void Callback(void* user_data,
                         const MTI::EventClass *event_class,
                         const MTI::EventRecord *record) {
        InstructionTraceContext* itc = static_cast<InstructionTraceContext*>
                                       (user_data);
        itc->nb_insts++; // Number of instructions
        // Filled by Component
        uint32_t pc = record->GetAs<uint32_t>(event_class,
                                                      itc->fields["PC"].index);
        uint32_t size = record->Get<uint32_t>(event_class,
                                                    itc->fields["SIZE"].index);
        // Save PC stats. If not already present in the map, a counter with
        // value 0 will be created before incrementing.
        InstStat& is = itc->stats[pc];
        is.cnt++;
        is.size = size;
    };
};

#endif // _COVERAGE_TOOL_COVERAGE_PLUGIN_TRACE_SOURCES_H_
