# coverage-reporting User Guide

The *coverage-reporting* is collection of python and bash scripts to generate LCOV HTML-based reports for code coverage against C source code. There are two stages for this process:

1. Converting the information from the execution traces (using coverage-plugin) of the FVP and the DWARF signatures from the elf/axf files to an intermediate JSON file.

2. Converting the intermediate JSON file into an info file that can be read by LCOV utilities to produce a code coverage HTML report. There are merrge utility scipts provided to merge multiple info files to generate a combined report from multiple runs.

## Intermediate JSON file
This is a JSON file that contains the information including the source code line numbers embedded in the elf files (by virtue of DWARF signatures) paired against the execution trace log files from the coverage-plugin. Hence only the lines that are compiled and linked to form the final binaries will be referenced by the DWARF signatures. Thus the coverage information will always be against the compiled code that made into the binary. The tools needs a configuration json file as an input with the needed metadata to perform the coverage computation. This configuration file is given as below:
```json
{
    "configuration":
        {
        "remove_workspace": "<true> if workspace must be from removed from the path of the source files",
        "include_assembly": "<true> to include assembly source code in the intermediate layer"
        },
    "parameters":
        {
        "objdump": "<Path> to the objdump binary to handle DWARF signatures",
        "readelf": "<Path> to the readelf binary to handle DWARF signatures",
        "sources": [
                    {
                    "type": "git",
                    "URL":  "<URL> git repo",
                    "COMMIT": "<Commit id>",
                    "REFSPEC": "<Refspec>",
                    "LOCATION": "<Folder> within 'workspace' where this source is located"
                    },
                    {
                    "type": "http",
                    "URL":  "<URL> link to file",
                    "COMPRESSION": "xz",
                    "LOCATION": "<Folder within 'workspace' where this source is located>"
                    }
                ],
        "workspace": "<Workspace folder> where the source code was located to produce(build) the elf/axf files",
        "output_file": "<Intermediate json layer output file name and location>",
        "metadata": {"metadata_1": "metadata value"}
        },
    "elfs": [
            {
                    "name": "<Full path name to elf/axf file>",
                    "traces": [
                                "Full path name to the trace file,"
                              ]
                }
        ]
}
```

Here is an example of an actual configuration JSON file:

```json
{
    "configuration":
        {
        "remove_workspace": true,
        "include_assembly": true
        },
    "parameters":
        {
        "objdump": "gcc-arm-none-eabi-7-2018-q2-update/bin/arm-none-eabi-objdump",
        "readelf": "gcc-arm-none-eabi-7-2018-q2-update/bin/arm-none-eabi-readelf",
        "sources": [
                    {
                    "type": "git",
                    "URL":  "https://git.trustedfirmware.org/TF-M/trusted-firmware-m.git/",
                    "COMMIT": "2ffadc12fb34baf0717908336698f8f612904",
                    "REFSPEC": "",
                    "LOCATION": "trusted-firmware-m"
                    },
                    {
                    "type": "git",
                    "URL":  "https://mucboot.com/mcuboot.git",
                    "COMMIT": "507689a57516f558dac72bef634723b60c5cfb46b",
                    "REFSPEC": "",
                    "LOCATION": "mcuboot"
                    },
                    {
                    "type": "git",
                    "URL":  "https://tf.org/mbed/mbed-crypto.git",
                    "COMMIT": "1146b4589011b69a6437e6b728f2af043a06ec19",
                    "REFSPEC": "",
                    "LOCATION": "mbed-crypto"
                    }
                ],
        "workspace": "/workspace/workspace/tf-m",
        "output_file": "output_file.json"
        },
    "elfs": [
            {
                    "name": "mcuboot.axf",
                    "traces": [
                                "reg-covtrace*.log"
                              ]
                },
            {
                    "name": "tfms.axf",
                    "traces": [
                                "reg-covtrace*.log"
                              ]
                },
            {
                    "name": "tfmns.axf",
                    "traces": [
                                "reg-covtrace*.log"
                              ]
                }
        ]
}
```


As dependencies the script needs the path to the objdump and readelf binares from the *same* toolchain used to build the elf binaries tested.
Now it can be invoked as:

```bash
$ python3 intermediate_layer.py --config-json <config json file> [--local-workspace <path to local folder/workspace where the source files are located]
```
The *local-workspace* option must be indicated if the current path to the source files is different from the workspace where the build (compiling and linking) happened. The latter will be in the DWARF signature while the former will be used to produce the coverage report. It is not a requirement to have the local workspace recreated but if not present then the program will not be able to find the line numbers belonging to functions within the source files (also **ctags** must be installed i.e. **sudo apt install exuberant-ctags**)

The output is an intermediate json file with the following format:

```json
{
	"configuration": {
		"elf_map": {
			"binary name 1": 0,
			"binary name 2": 1
		},
		"metadata": {
			"property 1": "metadata value 1",
			"property 2": "metadata value 2"
		},
		"sources": [{
			"type": "<git or http>",
			"URL": "<url for the source>",
			"COMMIT": "<commit id for git source>",
			"REFSPEC": "<refspec for the git source",
			"LOCATION": "<folder to put the source>"
		}]
	},
	"source_files": {
		"<Source file name>": {
			"functions": {
				"line": "<Function line number>",
				"covered": "<true or false>"
			},
			"lines": {
				"<line number>": {
					"covered": "<true or false>",
					"elf_index": {
						"<Index from elf map>": {
							"<Address in decimal>": [
								"<Assembly opcode>",
								"<Number of times executed>"
							]
						}
					}
				}
			}
		}
	}
}
```

An example snippet of an intermediate JSON file is here:

```json
{
    "configuration": {
        "elf_map": {
            "bl1": 0,
            "bl2": 1,
            "bl31": 2
        },
        "metadata": {
            "BUILD_CONFIG": "tf1",
            "RUN_CONFIG": "tf2"
        },
        "sources": [
                    {
                    "type": "git",
                    "URL":  "https://git.trustedfirmware.org/TF-M/trusted-firmware-m.git/",
                    "COMMIT": "2ffadc12fb34baf0717908336698f8f612904",
                    "REFSPEC": "",
                    "LOCATION": "trusted-firmware-m"
                    },
                    {
                    "type": "git",
                    "URL":  "https://mucboot.com/mcuboot.git",
                    "COMMIT": "507689a57516f558dac72bef634723b60c5cfb46b",
                    "REFSPEC": "",
                    "LOCATION": "mcuboot"
                    },
                    {
                    "type": "git",
                    "URL":  "https://tf.org/mbed/mbed-crypto.git",
                    "COMMIT": "1146b4589011b69a6437e6b728f2af043a06ec19",
                    "REFSPEC": "",
                    "LOCATION": "mbed-crypto"
                    }
        ]
    },
    "source_files": {
        "mcuboot/boot1.c": {
            "functions": {
                "arch_setup": true
            },
            "lines": {
                "12": {
                    "covered": true,
                    "elf_index": {
                        "0": {
                            "6948": [
                                "b2760000 \torr\tx0, x0, #0x400",
                                1
                            ]
                        }
                    }
                },
                "19": {
                    "covered": true,
                    "elf_index": {
                        "0": {
                            "6956": [
                                "d65f03c0 \tret",
                                1
                            ]
                        }
                    }
                }
            }
        },
... more lines
```



## Report
LCOV uses **info** files to produce a HTML report; hence to convert the intermediate json file to **info** file:
```bash
$ python3 generate_info_file.py --workspace <Workspace where the C source folder structure resides> --json <Intermediate json file> [--info <patht and filename for the info file>]
```
As was mentioned, the *workspace* option tells the program where to look for the source files thus is a requirement that the local workspace is populated.

This will generate an info file *coverage.info* that can be input into LCOV to generate the final coverage report as below:

```bash
$ genhtml --branch-coverage coverage.info --output-directory <HTML report folder>
```

Here is a example snippet of a info file:

```bash
TN:
SF:/home/projects/initial_attestation/attestation_key.c
FN:213,attest_get_instance_id

FN:171,attest_calc_instance_id

FN:61,attest_register_initial_attestation_key

FN:137,attest_get_signing_key_handle

FN:149,attest_get_initial_attestation_public_key

FN:118,attest_unregister_initial_attestation_key
FNDA:1,attest_get_instance_id

FNDA:1,attest_calc_instance_id

FNDA:1,attest_register_initial_attestation_key

FNDA:1,attest_get_signing_key_handle

FNDA:1,attest_get_initial_attestation_public_key

FNDA:1,attest_unregister_initial_attestation_key
FNF:6
FNH:6
BRDA:71,0,0,0
BRDA:71,0,1,1
...<more lines>
```

Refer to [](http://ltp.sourceforge.net/coverage/lcov/geninfo.1.php) for meaning of the flags.

## Wrapper
There is a wrapper bash script that can generate the intermediate json file, create the info file and the LCOV report:
```bash
$ ./branch_coverage.sh --config config_file.json --workspace Local workspace --outdir html_report
```

## Merge files
There is an utility wrapper that can merge jso and info files to produce a merge of the code coverage:
```bash
$ ./merge.sh -j <input json file> [-l <filename for report>] [-w <local workspace>] [-c to indicate to recreate workspace from sources]
```
This utility needs a input json file with the list of json/info files to be merged:
```json
{ "files" : [
                {
                    "id": "<unique project id (string) that belongs the json and info files>",
                    "config":
                        {
                            "type": "<'http' or 'file'>",
                            "origin": "<URL or folder where the json files reside>"
                        },
                    "info":
                        {
                            "type": "<'http' or 'file'>",
                            "origin": "<URL or folder where the info files reside>"
                        }
                },
....More of these json objects
        ]
}
```
This utility will merge the files, create the C source folder structure and produce the LCOV reports for the merged files. The utility can do a translation from the workspaces for each info file to the local workspace in case the info files come from different workspaces. The only requirement is that all the info files come from the **same** sources, i.e. repositories.

Example snippet of input json file:

```bash
{ "files" : [
                {
                    "id": "Tests_Release_BL2",
                    "config":
                        {
                            "type": "file",
                            "origin": "/home/workspace/150133/output_file.json"
                        },
                    "info":
                        {
                            "type": "file",
                            "origin": "/home/workspace/150133/coverage.info"
                        }
                },
                {
                    "id": "Tests_Regression_BL2",
                    "config":
                        {
                            "type": "file",
                            "origin": "/home//workspace/150143/output_file.json"
                        },
                    "info":
                            "type": "file",
                            "origin": "/home/workspace/150143/coverage.info"
                        }
                }
        ]
}
```

## License
[BSD-3-Clause](../../license.md)
