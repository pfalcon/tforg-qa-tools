# !/usr/bin/env python
###############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
###############################################################################

###############################################################################
# FILE: intermediate_layer.py
#
# DESCRIPTION: Creates an intermediate json file with information provided
#              by the configuration json file, dwarf signatures and trace
#              files.
#
###############################################################################

import os
import re
import glob
import argparse
import subprocess
import json
from argparse import RawTextHelpFormatter
import logging
import time

__version__ = "6.0"

# Static map that defines the elf file source type in the intermediate json
ELF_MAP = {
    "bl1": 0,
    "bl2": 1,
    "bl31": 2,
    "bl32": 3,
    "scp_ram": 10,
    "scp_rom": 11,
    "mcp_rom": 12,
    "mcp_ram": 13,
    "custom_offset": 100
}


def os_command(command, show_command=False):
    """
    Function that execute an os command, on fail exit the program

    :param command: OS command as string
    :param show_command: Optional argument to print the command in stdout
    :return: The string output of the os command
    """
    out = ""
    try:
        if show_command:
            print("OS command: {}".format(command))
        out = subprocess.check_output(
            command, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as ex:
        raise Exception(
            "Exception running command '{}': {}({})".format(
                command, ex.output, ex.returncode))
    return out.decode("utf8")


def load_stats_from_traces(trace_globs):
    """
    Function to process and consolidate statistics from trace files

    :param trace_globs: List of trace file patterns
    :return: Dictionary with stats from trace files i.e.
        {mem address in decimal}=(times executed, inst size)
    """
    stats = {}
    stat_size = {}

    # Make a list of unique trace files
    trace_files = []
    for tg in trace_globs:
        trace_files.extend(glob.glob(tg))
    trace_files = set(trace_files)

    if not trace_files:
        raise Exception("No trace files found for '{}'".format(trace_globs))
    # Load stats from the trace files
    for trace_file in trace_files:
        try:
            with open(trace_file, 'r') as f:
                for line in f:
                    data = line.split()
                    address = int(data[0], 16)
                    stat = int(data[1])
                    size = int(data[2])
                    stat_size[address] = size
                    if address in stats:
                        stats[address] += stat
                    else:
                        stats[address] = stat
        except Exception as ex:
            logger.error("@Loading stats from trace files:{}".format(ex))
    # Merge the two dicts
    for address in stats:
        stats[address] = (stats[address], stat_size[address])
    return stats


def get_code_sections_for_binary(elf_name):
    """
    Function to return the ranges of memory address for sections of code
    in the elf file

    :param elf_name: Elf binary file name
    :return: List of code sections tuples, i.e. (section type, initial
            address, end address)
    """
    command = """%s -h %s | grep -B 1 CODE | grep -v CODE \
                | awk '{print $2" "$4" "$3}'""" % (OBJDUMP, elf_name)
    text_out = os_command(command)
    sections = text_out.split('\n')
    sections.pop()
    secs = []
    for sec in sections:
        try:
            d = sec.split()
            secs.append((d[0], int(d[1], 16), int(d[2], 16)))
        except Exception as ex:
            logger.error(
                "@Returning memory address code sections:".format(ex))
    return secs


def get_executable_ranges_for_binary(elf_name):
    """
    Get function ranges from an elf file

    :param elf_name: Elf binary file name
    :return: List of tuples for ranges i.e. (range start, range end)
    """
    # Parse all $x / $d symbols
    symbol_table = []
    command = r"""%s -s %s | awk '/\$[xatd]/ {print $2" "$8}'""" % (
        READELF, elf_name)
    text_out = os_command(command)
    lines = text_out.split('\n')
    lines.pop()
    for line in lines:
        try:
            data = line.split()
            address = int(data[0], 16)
            _type = 'X' if data[1] in ['$x', '$t', '$a'] else 'D'
        except Exception as ex:
            logger.error("@Getting executable ranges:".format(ex))
        symbol_table.append((address, _type))

    # Add markers for end of code sections
    sections = get_code_sections_for_binary(elf_name)
    for sec in sections:
        symbol_table.append((sec[1] + sec[2], 'S'))

    # Sort by address
    symbol_table = sorted(symbol_table, key=lambda tup: tup[0])

    # Create ranges (list of START/END tuples)
    ranges = []
    range_start = symbol_table[0][0]
    rtype = symbol_table[0][1]
    for sym in symbol_table:
        if sym[1] != rtype:
            if rtype == 'X':
                # Substract one because the first address of the
                # next range belongs to the next range.
                ranges.append((range_start, sym[0] - 1))
            range_start = sym[0]
            rtype = sym[1]
    return ranges


def list_of_functions_for_binary(elf_name):
    """
    Get an array of the functions in the elf file

    :param elf_name: Elf binary file name
    :return: An array of function address start, function address end,
            function dwarf signature (sources) addressed by function name
    """
    _functions = {}
    command = "%s -t %s | awk 'NR>4' | sed /^$/d" % (OBJDUMP, elf_name)
    symbols_output = os_command(command)
    rex = r'([0-9a-fA-F]+) (.{7}) ([^ ]+)[ \t]([0-9a-fA-F]+) (.*)'
    symbols = symbols_output.split('\n')[:-1]
    for sym in symbols:
        try:
            symbol_details = re.findall(rex, sym)
            symbol_details = symbol_details[0]
            if 'F' not in symbol_details[1]:
                continue
            function_name = symbol_details[4]
            # We don't want the .hidden for hidden functions
            if function_name.startswith('.hidden '):
                function_name = function_name[len('.hidden '):]
            if function_name not in _functions:
                _functions[function_name] = {'start': symbol_details[0],
                                             'end': symbol_details[3],
                                             'sources': False}
            else:
                logger.warning("'{}' duplicated in '{}'".format(
                    function_name,
                    elf_name))
        except Exception as ex:
            logger.error("@Listing functions at file {}: {}".format(
                elf_name,
                ex))
    return _functions


def apply_functions_exclude(elf_config, functions):
    """
    Remove excluded functions from the list of functions

    :param elf_config: Config for elf binary file
    :param functions: Array of functions in the binary elf file
    :return: Tuple with included and excluded functions
    """
    if 'exclude_functions' not in elf_config:
        return functions, []
    incl = {}
    excl = {}
    for fname in functions:
        exclude = False
        for rex in elf_config['exclude_functions']:
            if re.match(rex, fname):
                exclude = True
                excl[fname] = functions[fname]
                break
        if not exclude:
            incl[fname] = functions[fname]
    return incl, excl


def remove_workspace(path, workspace):
    """
    Get the relative path to a given workspace

    :param path: Path relative to the workspace to be returned
    :param workspace: Path.
    """
    ret = path if workspace is None else os.path.relpath(path, workspace)
    # print("{} => {}".format(path, ret))
    return ret


def get_function_line_numbers(source_file):
    """
    Using ctags get all the function names with their line numbers
    within the source_file

    :return: Dictionary with function name as key and line number as value
    """
    command = "ctags -x --c-kinds=f {}".format(source_file)
    fln = {}
    try:
        function_lines = os_command(command).split("\n")
        for line in function_lines:
            cols = line.split()
            if len(cols) < 3:
                continue
            if cols[1] == "function":
                fln[cols[0]] = int(cols[2])
            elif cols[1] == "label" and cols[0] == "func":
                fln[cols[-1]] = int(cols[2])
    except BaseException:
        logger.warning("Warning: Can't get all function line numbers from %s" %
                       source_file)
    except Exception as ex:
        logger.warning(f"Warning: Unknown error '{ex}' when executing command '{command}'")
        return {}

    return fln


class FunctionLineNumbers(object):

    def __init__(self, workspace):
        self.filenames = {}
        self.workspace = workspace

    def get_line_number(self, filename, function_name):
        if not FUNCTION_LINES_ENABLED:
            return 0
        if filename not in self.filenames:
            newp = os.path.join(self.workspace, filename)
            self.filenames[filename] = get_function_line_numbers(newp)
        return 0 if function_name not in self.filenames[filename] else \
            self.filenames[filename][function_name]


class PostProcessCC(object):
    """Class used to process the trace data along with the dwarf
    signature files to produce an intermediate layer in json with
    code coverage in assembly and c source code.
    """

    def __init__(self, _config, local_workspace):
        self._data = {}
        self.config = _config
        self.local_workspace = local_workspace
        self.elfs = self.config['elfs']
        # Dictionary with stats from trace files {address}=(times executed,
        # inst size)
        self.traces_stats = {}
        # Dictionary of unique assembly line memory address against source
        # file location
        # {assembly address} = (opcode, source file location, line number in
        # the source file, times executed)
        self.asm_lines = {}
        # Dictionary of {source file location}=>{'lines': {'covered':Boolean,
        # 'elf_index'; {elf index}=>{assembly address}=>(opcode,
        # times executed),
        # 'functions': {function name}=>is covered(boolean)}
        self.source_files_coverage = {}
        self.functions = []
        # Unique set of elf list of files
        self.elf_map = {}
        # For elf custom mappings
        self.elf_custom = None

    def process(self):
        """
        Public method to process the trace files and dwarf signatures
        using the information contained in the json configuration file.
        This method writes the intermediate json file output linking
        the trace data and c source and assembly code.
        """
        self.source_files_coverage = {}
        self.asm_lines = {}
        # Initialize for unknown elf files
        self.elf_custom = ELF_MAP["custom_offset"]
        sources_config = {}
        print("Generating intermediate json layer '{}'...".format(
            self.config['parameters']['output_file']))
        for elf in self.elfs:
            # Gather information
            elf_name = elf['name']
            os_command("ls {}".format(elf_name))
            # Trace data
            self.traces_stats = load_stats_from_traces(elf['traces'])
            prefix = self.config['parameters']['workspace'] \
                if self.config['configuration']['remove_workspace'] else \
                None
            functions_list = list_of_functions_for_binary(elf_name)
            (functions_list, excluded_functions) = apply_functions_exclude(
                elf, functions_list)
            # Produce code coverage
            self.dump_sources(elf_name, functions_list, prefix)
            sources_config = self.config['parameters']['sources']
            # Now check code coverage in the functions with no dwarf signature
            # (sources)
            nf = {f: functions_list[f] for f in
                  functions_list if not
                  functions_list[f]["sources"]}
            self.process_fn_no_sources(nf)
            # Write to the intermediate json file
        data = {"source_files": self.source_files_coverage,
                "configuration": {
                    "sources": sources_config,
                    "metadata": "" if 'metadata' not in
                                      self.config['parameters'] else
                    self.config['parameters']['metadata'],
                    "elf_map": self.elf_map
                }
                }
        json_data = json.dumps(data, indent=4, sort_keys=True)
        with open(self.config['parameters']['output_file'], "w") as f:
            f.write(json_data)

    def dump_sources(self, elf_filename, function_list, prefix=None):
        """
        Process an elf file i.e. match the source and asm lines against trace
            files (coverage).

        :param elf_filename: Elf binary file name
        :param function_list: List of functions in the elf file i.e.
                                [(address start, address end, function name)]
        :param prefix: Optional path name to be removed at the start of source
                        file locations
        """
        command = "%s -Sl %s" % (OBJDUMP, elf_filename)
        dump = os_command(command)
        dump += "\n"  # For pattern matching the last \n
        elf_name = os.path.splitext(os.path.basename(elf_filename))[0]
        # Object that handles the function line numbers in
        # their filename
        function_line_numbers = FunctionLineNumbers(self.local_workspace)
        # To map the elf filename against an index
        if elf_name not in self.elf_map:
            if elf_name in ELF_MAP:
                self.elf_map[elf_name] = ELF_MAP[elf_name]
            else:
                self.elf_map[elf_name] = self.elf_custom
                self.elf_custom += 1
        elf_index = self.elf_map[elf_name]
        # The function groups have 2 elements:
        # Function's block name, Function's block code
        function_groups = re.findall(
            r"(?s)[0-9a-fA-F]+ <([a-zA-Z0-9_]+)>:\n(.+?)(?:\r*\n\n|\n$)",
            dump, re.DOTALL | re.MULTILINE)
        # Pointer to files dictionary
        source_files = self.source_files_coverage
        for function_group in function_groups:
            if len(function_group) != 2:
                continue
            block_function_name, block_code = function_group
            block_code += "\n"
            # Find if the function has C source code filename
            function_signature_group = re.findall(
                r"(?s){}\(\):\n(/.+?):[0-9]+.*(?:\r*\n\n|\n$)".format(
                    block_function_name), block_code, re.DOTALL | re.MULTILINE)
            if not function_signature_group:
                continue  # Function does not have dwarf signature (sources)
            if not block_function_name in function_list:
                print("Warning:Function '{}' not found in function list!!!".format(block_function_name))
                continue # Function not found in function list
            function_list[block_function_name]["sources"] = True
            block_function_source_file = remove_workspace(
                function_signature_group[0], prefix)
            fn_line_number = function_line_numbers.get_line_number(
                block_function_source_file, block_function_name)
            if block_function_source_file not in source_files:
                source_files[block_function_source_file] = {"functions": {},
                                                            "lines": {}}
            source_files[block_function_source_file]["functions"][
                block_function_name] = {"covered": False,
                                        "line_number": fn_line_number}
            # Now lets check the block code
            # The source code groups have 5 elements:
            # Function for the statements (optional), Source file for the asm
            # statements,
            # line number for the asm statements, asm statements, lookahead
            # (ignored)
            source_code_groups = re.findall(SOURCE_PATTERN, block_code,
                                            re.DOTALL | re.MULTILINE)
            is_function_block_covered = False
            # When not present the last function name applies
            statements_function_name = block_function_name
            for source_code_group in source_code_groups:
                if len(source_code_group) != 5:
                    continue
                fn_name, source_file, ln, asm_code, _ = source_code_group
                if not fn_name:
                    # The statement belongs to the most recent function
                    fn_name = statements_function_name
                else:
                    # Usually in the first iteration fn_name is not empty and
                    # is the function's name block
                    statements_function_name = fn_name
                if statements_function_name in function_list:
                    # Some of the functions within a block are not defined in
                    # the function list dump
                    function_list[statements_function_name]["sources"] = True
                statements_source_file = remove_workspace(source_file, prefix)
                if statements_source_file not in source_files:
                    source_files[statements_source_file] = {"functions": {},
                                                            "lines": {}}
                if statements_function_name not in \
                        source_files[statements_source_file]["functions"]:
                    fn_line_number = function_line_numbers.get_line_number(
                        statements_source_file,
                        statements_function_name)
                    source_files[statements_source_file]["functions"][
                        statements_function_name] = \
                        {"covered": False, "line_number": fn_line_number}
                if ln not in source_files[statements_source_file]["lines"]:
                    source_files[statements_source_file]["lines"][ln] = \
                        {"covered": False, "elf_index": {}}
                source_file_ln = source_files[statements_source_file]["lines"][
                    ln]
                asm_line_groups = re.findall(
                    r"(?s)([a-fA-F0-9]+):\t(.+?)(?:\n|$)",
                    asm_code, re.DOTALL | re.MULTILINE)
                for asm_line in asm_line_groups:
                    if len(asm_line) != 2:
                        continue
                    hex_line_number, opcode = asm_line
                    dec_address = int(hex_line_number, 16)
                    times_executed = 0 if dec_address not in self.traces_stats \
                        else self.traces_stats[dec_address][0]
                    if times_executed > 0:
                        is_function_block_covered = True
                        source_file_ln["covered"] = True
                        source_files[statements_source_file]["functions"][
                            statements_function_name]["covered"] = True
                    if elf_index not in source_file_ln["elf_index"]:
                        source_file_ln["elf_index"][elf_index] = {}
                    if dec_address not in \
                            source_file_ln["elf_index"][elf_index]:
                        source_file_ln["elf_index"][elf_index][dec_address] = (
                            opcode, times_executed)
            source_files[block_function_source_file]["functions"][
                block_function_name]["covered"] |= is_function_block_covered

    def process_fn_no_sources(self, function_list):
        """
        Checks function coverage for functions with no dwarf signature i.e
         sources.

        :param function_list: Dictionary of functions to be checked
        """
        if not FUNCTION_LINES_ENABLED:
            return  # No source code at the workspace
        address_seq = sorted(self.traces_stats.keys())
        for function_name in function_list:
            # Just check if the start address is in the trace logs
            covered = function_list[function_name]["start"] in address_seq
            # Find the source file
            files = os_command(("grep --include *.c --include *.s -nrw '{}' {}"
                                "| cut -d: -f1").format(function_name,
                                                        self.local_workspace))
            unique_files = set(files.split())
            sources = []
            line_number = 0
            for source_file in unique_files:
                d = get_function_line_numbers(source_file)
                if function_name in d:
                    line_number = d[function_name]
                    sources.append(source_file)
            if len(sources) > 1:
                logger.warning("'{}' declared in {} files:{}".format(
                    function_name, len(sources),
                    ", ".join(sources)))
            elif len(sources) == 1:
                source_file = remove_workspace(sources[0],
                                               self.local_workspace)
                if source_file not in self.source_files_coverage:
                    self.source_files_coverage[source_file] = {"functions": {},
                                                               "lines": {}}
                if function_name not in \
                        self.source_files_coverage[source_file]["functions"] or \
                        covered:
                    self.source_files_coverage[source_file]["functions"][
                        function_name] = {"covered": covered,
                                          "line_number": line_number}
            else:
                logger.warning("Function '{}' not found in sources.".format(
                    function_name))


json_conf_help = """
Produces an intermediate json layer for code coverage reporting
using an input json configuration file.

Input json configuration file format:
{
    "configuration":
        {
        "remove_workspace": <true if 'workspace' must be from removed from the
                                path of the source files>,
        "include_assembly": <true to include assembly source code in the
                            intermediate layer>
        },
    "parameters":
        {
        "objdump": "<Path to the objdump binary to handle dwarf signatures>",
        "readelf: "<Path to the readelf binary to handle dwarf signatures>",
        "sources": [ <List of source code origins, one or more of the next
                        options>
                    {
                    "type": "git",
                    "URL":  "<URL git repo>",
                    "COMMIT": "<Commit id>",
                    "REFSPEC": "<Refspec>",
                    "LOCATION": "<Folder within 'workspace' where this source
                                is located>"
                    },
                    {
                    "type": "http",
                    "URL":  <URL link to file>",
                    "COMPRESSION": "xz",
                    "LOCATION": "<Folder within 'workspace' where this source
                                is located>"
                    }
                ],
        "workspace": "<Workspace folder where the source code was located to
                        produce the elf/axf files>",
        "output_file": "<Intermediate layer output file name and location>",
        "metadata": {<Metadata objects to be passed to the intermediate json
                    files>}
        },
    "elfs": [ <List of elf files to be traced/parsed>
            {
                    "name": "<Full path name to elf/axf file>",
                    "traces": [ <List of trace files to be parsed for this
                                elf/axf file>
                                "Full path name to the trace file,"
                              ]
                }
        ]
}
"""
OBJDUMP = None
READELF = None
FUNCTION_LINES_ENABLED = None
SOURCE_PATTERN = (r'(?s)([a-zA-Z0-9_]+)?(?:\(\):\n)?(^/.+?):([0-9]+)'
                  r'(?: \(.+?\))?\n(.+?)(?=\n/|\n$|([a-zA-Z0-9_]+\(\):))')


def main():
    global OBJDUMP
    global READELF
    global FUNCTION_LINES_ENABLED

    parser = argparse.ArgumentParser(epilog=json_conf_help,
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('--config-json', metavar='PATH',
                        dest="config_json", default='config_file.json',
                        help='JSON configuration file', required=True)
    parser.add_argument('--local-workspace', default="",
                        help=('Local workspace folder where source code files'
                              ' and folders resides'))
    args = parser.parse_args()
    try:
        with open(args.config_json, 'r') as f:
            config = json.load(f)
    except Exception as ex:
        print("Error at opening and processing JSON: {}".format(ex))
        return
    # Setting toolchain binary tools variables
    OBJDUMP = config['parameters']['objdump']
    READELF = config['parameters']['readelf']
    # Checking if are installed
    os_command("{} --version".format(OBJDUMP))
    os_command("{} --version".format(READELF))

    if args.local_workspace != "":
        # Checking ctags installed
        try:
            os_command("ctags --version")
        except BaseException:
            print("Warning!: ctags not installed/working function line numbers\
                    will be set to 0. [{}]".format(
                "sudo apt install exuberant-ctags"))
        else:
            FUNCTION_LINES_ENABLED = True

    pp = PostProcessCC(config, args.local_workspace)
    pp.process()


if __name__ == '__main__':
    logging.basicConfig(filename='intermediate_layer.log', level=logging.DEBUG,
                        format=('%(asctime)s %(levelname)s %(name)s '
                                '%(message)s'))
    logger = logging.getLogger(__name__)
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print("Elapsed time: {}s".format(elapsed_time))
