# coverage-plugin User Guide

The *coverage-plugin* is a C++ project using the Model Trace Interface Plugin Development Kit (MTIPDK) in order to create a trace plugin, which is a special shared library. The trace plugins can be loaded into Arm Fast Models to produce execution trace data for doing code coverage measurement.

## Dependencies
- GCC 7.5.0 at least

## Building the coverage-plugin
```bash
$ cd coverage-plugin
$ make PVLIB_HOME=</path/to/model_library>
```

## Capturing a trace

You need to add two options to your model command-line:

```bash
   --plugin /path/to/coverage_trace.so
   -C TRACE.coverage_trace.trace-file-prefix="/path/to/TRACE-PREFIX"
```

You can then run your FVP model. The traces will be created at the end of the simulation*.

BEWARE: Traces aren't numbered and will be overwritten if you do two successive runs. Aggregating results will require moving traces to a separate place or changing the prefix between runs. This is the responsibility of the plugin user.

*NOTE: The plugin captures the traces in memory and on the termination of the simulation it writes the data to a file. If user terminates the simulation forcefully with a Ctrl+C the trace files are not generated.

## License
[BSD-3-Clause](../../license.md)
