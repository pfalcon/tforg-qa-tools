# Trace-based Coverage Tool User Guide

The *coverage-tool* is developed to provide code coverage measurement based on execution trace and without the need for code instrumentation. This tool is specifically meant for firmware components which are run on memory constraint platforms. The non-reliance on code instrumentation in this approach circumvents the frequent issue of instrumented code affecting the target memory model, where the firmware is expected to run. Thus here we test the firmware in the actual memory model it is intended to be eventually released. The coverage tool comprises of 2 main components. A *trace plugin component* and a set of *post processing scripts* to generate the coverage report.

## Design Overview
Refer to [design overview](./design_overview.md) for an outline of the design of this trace-based coverage tool.

## Plugin user guide
Refer to [plugin user guide](./plugin_user_guide.md) to learn more on how the plugin component is to be used as part of trace-based coverage tool.

## Reporting user guide
Refer to [reporting user guide](./reporting_user_guide.md) to learn more on how to use the post-processing scripts, that are part of the trace-based coverage tool, in order to generate the coverage report for analysis.

## License
[BSD-3-Clause](../../license.md)
