# coverage-tool

The *coverage-tool* is a coverage measurement tool based on a custom plugin (implementing Model Trace Interface (MTI)) to generate execution traces and a report generator based on LCOV. Current implementation of this tool reports statement/line coverage, function coverage and branch coverage information.

## Installation

Please clone the repository.

```bash
git clone https://gitlab.arm.com/qa-tools.git
```

## Dependencies
For the plugin
- Python 3

For the report generator:
- LCOV (https://github.com/linux-test-project/lcov)
```bash
sudo apt-get update -y
sudo apt-get install -y lcov
sudo apt-get install exuberant-ctags
```
## Usage

Please see the individual [user guide](./docs/user_guide.md) for more details.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please follow the recommended [coding style](../readme.md#Style Guide) specified for each component. Also do  make sure to update the in-source documentation as appropriate.


## License
[BSD-3-Clause](../../license.md)
