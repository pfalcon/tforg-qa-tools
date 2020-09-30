/*!
##############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################
*/
// Implements the trace plugin interface for the MTI interface to trace
// source data from Arm FVP.

#include "MTI/PluginInterface.h"
#include "MTI/PluginFactory.h"
#include "MTI/PluginInstance.h"
#include "MTI/ModelTraceInterface.h"

#include "plugin_utils.h"
#include "trace_sources.h"

#include <errno.h>
#include <string>
#include <algorithm>
#include <cstdio>
#include <sstream>
#include <vector>
#include <map>
#include <typeinfo>
#include <typeindex>
#include <utility>

#ifdef SG_MODEL_BUILD
    #include "builddata.h"
    #define PLUGIN_VERSION FULL_VERSION_STRING
#else
    #define PLUGIN_VERSION "unreleased"
#endif

using namespace eslapi;
using namespace MTI;
using namespace std;

// Implements the plugin interface for trace coverage
class CoverageTrace :public PluginInstance
{
public:
    virtual CAInterface * ObtainInterface(if_name_t    ifName,
                                          if_rev_t     minRev,
                                          if_rev_t *   actualRev);

    CoverageTrace(const char *instance_name, const char *trace_file_prefix);
    ~CoverageTrace();

    /** This is to associate a plugin with a simulation instance. Exactly one
     * simulation must be registered.
     * */
    virtual eslapi::CADIReturn_t RegisterSimulation(eslapi::CAInterface
                                                    *simulation);

    // This is called before the plugin .dll/.so is unloaded and should allow
    // the plugin to do it's cleanup.
    virtual void Release();

    virtual const char *GetName() const;

private:
    std::string instance_name;

    bool Error(const char *);

    vector<TraceComponentContext*> trace_components;
    std::string trace_file_prefix;
};

CAInterface *CoverageTrace::ObtainInterface(if_name_t ifName,
                            if_rev_t     minRev,
                            if_rev_t *   actualRev)
{
  printf("CoverageTrace::ObtainInterface\n");
    // If someone is asking for the matching interface
    if((strcmp(ifName,IFNAME()) == 0) &&
    // and the revision of this interface implementation is
       (minRev <= IFREVISION()))
        // at least what is being asked for
    {
        if (actualRev) // Make sure this is not a NULL pointer
            *actualRev = IFREVISION();
        return this;
    }

    if((strcmp(ifName, CAInterface::IFNAME()) == 0) &&
       minRev <= CAInterface::IFREVISION())
    {
        if (actualRev != NULL)
            *actualRev = CAInterface::IFREVISION();
        return this;// Dynamic_cast<TracePluginInterface *>(this);
    }
    return NULL;
}


CoverageTrace::CoverageTrace(const char *instance_name_,
                             const char *trace_file_prefix_) :
    instance_name(instance_name_),
    trace_file_prefix(trace_file_prefix_)
{
  printf("CoverageTrace::CoverageTrace\n");
}

CoverageTrace::~CoverageTrace()
{
  printf("CoverageTrace::~CoverageTrace\n");
}

bool
CoverageTrace::Error(const char *msg)
{
    fprintf(stderr, "%s\n", msg);
    return false;
}

// Method that registers the simulation traces events. In this case registers
// for trace sources with the 'INST' name.
CADIReturn_t
CoverageTrace::RegisterSimulation(CAInterface *ca_interface)
{
  printf("CoverageTrace::RegisterSimulation\n");
    if (!ca_interface) {
        Error("Received CAInterface NULL pointer.");
        return CADI_STATUS_IllegalArgument;
    }
    std::stringstream ss;

    SystemTraceInterface *sys_if =
                          ca_interface->ObtainPointer<SystemTraceInterface>();
    if (sys_if == 0) {
        Error("Got a NULL SystemTraceInterface.");
        return CADI_STATUS_GeneralError;
    }

    for(SystemTraceInterface::TraceComponentIndex tci=0;
        tci < sys_if->GetNumOfTraceComponents(); ++tci) {
        const char* tpath = sys_if->GetComponentTracePath(tci);
        CAInterface *caif = sys_if->GetComponentTrace(tci);
        ComponentTraceInterface *cti =
                                 caif->ObtainPointer<ComponentTraceInterface>();
        if (cti == 0) {
            Error("Could not get TraceInterface for component.");
            continue;
        }

        if (cti->GetTraceSource("INST") != 0) {
            TraceComponentContext *trace_component = new
                                                TraceComponentContext(tpath);

            // To register a new trace source the arguments are the
            // name of the trace source followed by a vector of
            // pairs of (field name,field type).
            InstructionTraceContext *inst_cont = new InstructionTraceContext(
                                            "INST",
                                            { {"PC", u32},
                                            {"SIZE", u32}}
                                        );
            inst_cont->nb_insts = 0;
            inst_cont->CreateEvent(&cti, inst_cont->Callback);
            trace_component->AddTraceSource(inst_cont);
            trace_components.push_back(trace_component);
        }
    }

    return CADI_STATUS_OK;
}

// This is called before the plugin .dll/.so is unloaded and should allow the
// plugin to do it's cleanup.
void
CoverageTrace::Release()
{
  printf("CoverageTrace::Release\n");
    // We can dump our data now
    int error = 0;
    char* fname;
    int ret;
    std::vector<TraceComponentContext*>::iterator tcc;
    for (tcc = trace_components.begin(); tcc < trace_components.end(); ++tcc) {
        TraceComponentContext *tcont = *tcc;
        // Print some overall stats
        InstructionTraceContext* rtc = (InstructionTraceContext*)
                                    tcont->trace_sources["INST"];
        printf("Trace path: %s\n", tcont->trace_path.c_str());

        // Construct a trace file name
        int status = asprintf(&fname, "%s-%s.log",
                              this->trace_file_prefix.c_str(),
                              tcont->trace_path.c_str());
        if ( status != 0)
        {
            printf("Error in asprintf: %d\n", status);
            printf("Error description is : %s\n", strerror(errno));
          }

        // Open it
        FILE* fp = fopen(fname, "w");
        if (fp == NULL) {
            fprintf(stderr, "Can't open file %s for writing.\n", fname);
            error = 1;
            break;
        }

        InstStatMap::iterator map_it;
        // Dump the detailed stats
        for (map_it = rtc->stats.begin(); map_it != rtc->stats.end();
            ++map_it) {
            fprintf(fp, "%08x %lu %lu\n", map_it->first, map_it->second.cnt,
                    map_it->second.size);
        }

        // Close the file
        ret = fclose(fp);
        if (ret != 0) {
            fprintf(stderr, "Failed to close %s: %s.", fname, strerror(errno));
            error = 1;
            break;
        }

        free(fname);
    }
if (error != 0)
    delete this;
}

const char *
CoverageTrace::GetName() const
{
  printf("CoverageTrace::GetName\n");
    return instance_name.c_str();
}

// Class used to return a static object CAInterface. CAInterface provides a
// basis for a software model built around ’components’ and ’interfaces’.
// A component provides concrete implementations of one or more interfaces.
// Interfaces are identified by a string name (of type if_name_t), and an
// integer revision (type if_rev_t). A higher revision number indicates a newer
// revision of the same interface.
class ThePluginFactory :public PluginFactory
{
public:
    virtual CAInterface *ObtainInterface(if_name_t    ifName,
                                          if_rev_t     minRev,
                                          if_rev_t *   actualRev);

    virtual uint32_t GetNumberOfParameters();

    virtual eslapi::CADIReturn_t
        GetParameterInfos(eslapi::CADIParameterInfo_t *parameter_info_list);

    virtual CAInterface *Instantiate(const char *instance_name,
                                     uint32_t number_of_parameters,
                                     eslapi::CADIParameterValue_t *parameter_values);

    virtual void Release();

    virtual const char *GetType() const { return "CoverageTrace"; }
    virtual const char *GetVersion() const { return PLUGIN_VERSION; }
};

// Allows a client to obtain a reference to any of the interfaces that the
// component implements. The client specifies the id and revision of the
// interface that it wants to request. The component can return NULL if it
// doesn’t implement that interface, or only implements a lower revision.
// The client in this case is the Arm FVP model.
CAInterface *ThePluginFactory::ObtainInterface(if_name_t ifName,
                                  if_rev_t     minRev,
                                  if_rev_t *   actualRev)
{
  printf("ThePluginFactory::ObtainInterface\n");
    // If someone is asking for the matching interface
    if((strcmp(ifName,IFNAME()) == 0) &&
        // and the revision of this interface implementation is
       (minRev <= IFREVISION()))
        // at least what is being asked for
    {
        if (actualRev) // Make sure this is not a NULL pointer
            *actualRev = IFREVISION();
        return static_cast<ThePluginFactory *>(this);
    }

    if((strcmp(ifName, CAInterface::IFNAME()) == 0) &&
       minRev <= CAInterface::IFREVISION())
    {
        if (actualRev) // Make sure this is not a NULL pointer
            *actualRev = CAInterface::IFREVISION();
        return static_cast<CAInterface *>(this);
    }
    return NULL;
}

uint32_t ThePluginFactory::GetNumberOfParameters()
{
  printf("ThePluginFactory::GetNumberOfParameters\n");
  return 1;
}

eslapi::CADIReturn_t
ThePluginFactory::GetParameterInfos(
eslapi::CADIParameterInfo_t *parameter_info_list)
{
    printf("ThePluginFactory::GetParameterInfos\n");
    *parameter_info_list = CADIParameterInfo_t(
        0, "trace-file-prefix", CADI_PARAM_STRING,
        "Prefix of the trace files.", 0, 0, 0, 0, "covtrace"
    );
    return CADI_STATUS_OK;
}

// Method that creates a new instance of the trace plugin
CAInterface *ThePluginFactory::Instantiate(const char *instance_name,
                              uint32_t param_nb,
                              eslapi::CADIParameterValue_t *values)
{
    printf("ThePluginFactory::Instantiate\n");
    const char *trace_file_prefix = 0;
    printf("CoverageTrace: number of params: %d\n", param_nb);
    for (uint32_t i = 0; i < param_nb; ++i) {
        if (values[i].parameterID == 0) {
            trace_file_prefix = values[i].stringValue;
        } else {
            printf("\tCoverageTrace: got unexpected param %d\n",
                   values[i].parameterID);
        }
    }
    return new CoverageTrace(instance_name, trace_file_prefix);
}

void ThePluginFactory::Release()
{
  printf("ThePluginFactory::Release\n");
}

static ThePluginFactory factory_instance;

// Entry point for the instantiation of the plugin.
// Returns a pointer to an static object to create the interface for the
// plugin.
CAInterface *GetCAInterface()
{
    printf("********->GetCAInterface\n");
    return &factory_instance;
}

// End of file CoverageTrace.cpp
