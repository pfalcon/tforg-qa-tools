# qa-tools

qa-tools repo consists of a set of tools that helps in improving the quality assurance within project teams.

Currently qa-tools repo hosts the following tools:
- Trace-based code coverage tool.
- Quality metrics measurement and tracking setup.

## Trace-based code coverage tool

This is a code coverage tool specifically for firmware components that run on memory constraint platforms, where traditional approach to measuring coverage with code instrumentation does not work well. This tool allows coverage measurement to be done based on execution trace from fastmodel platforms used along with the information gathered from DWARF signatures embedded in the firmware binaries.

See [Coverage Tool - README](./coverage-tool/readme.md) for more details.


## Quality metrics measurement and tracking setup

This is a collection of data generator scripts that can be integrated as part of any CI setup to generate some quality metrics and publish that to a database backend to be visualised and tracked over time. The aim is to equip the projects with the capability to measure and track useful metrics to improve quality of the software delivery over time.


See [Quality Metrics - README](./quality-metrics/readme.md) for more details.


## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update the in-source documentation as appropriate.

## Style Guide

At the moment the qa-tools comprises of various component developed in multiple languages. We follow the below coding guidelines and would request the same for any incoming contributions.

Shell scripting guidelines - Follow Google's guidelines [Google Shell Scripting Guideline](https://google.github.io/styleguide/shellguide.html)
C++ coding guidelines - Follow Google's guidelines [Google C++ Guideline](https://google.github.io/styleguide/cppguide.html)
Python coding guidelines - Follow PEP 8 style guide [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/). We highly recommend the user of [Autopep8 tool](https://pypi.org/project/autopep8/) for the automatic formating of python code to be compliant with PEP 8 guidelines.

## License
[BSD-3-Clause](./license.md)

