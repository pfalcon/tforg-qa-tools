# !/usr/bin/env python
##############################################################################
# Copyright (c) 2020, ARM Limited and Contributors. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import os
import sys
import json
import re
import argparse


def function_coverage(function_tuples, info_file):
    """
    Parses and get information from intermediate json file to info
    file for function coverage

    :param function_tuples: List of tuples with function name
                            and its data as pairs.
    :param info_file: Handler to for file writing coverage
    """
    total_func = 0
    covered_func = 0
    function_names = []
    function_cov = []
    for func_name, func_data in function_tuples:
        function_names.append(
            'FN:{},{}\n'.format(
                func_data["line_number"],
                func_name))
        total_func += 1
        if func_data["covered"]:
            covered_func += 1
            function_cov.append('FNDA:1,{}\n'.format(func_name))
        else:
            function_cov.append('FNDA:0,{}\n'.format(func_name))
    info_file.write("\n".join(function_names))
    info_file.write("\n".join(function_cov))
    info_file.write('FNF:{}\n'.format(total_func))
    info_file.write('FNH:{}\n'.format(covered_func))


def line_coverage(lines_dict, info_file):
    """
    Parses and get information from intermediate json file to info
    file for line coverage

    :param lines_dict: Dictionary of lines with line number as key
                       and its data as value
    :param info_file: Handler to for file writing coverage
    """
    total_lines = 0
    covered_lines = 0
    for line in lines_dict:
        total_lines += 1
        if lines_dict[line]['covered']:
            covered_lines += 1
            info_file.write('DA:' + line + ',1\n')
        else:
            info_file.write('DA:' + line + ',0\n')
    info_file.write('LF:' + str(total_lines) + '\n')
    info_file.write('LH:' + str(covered_lines) + '\n')


def sanity_check(branch_line, lines_dict, abs_path_file):
    """
    Check if the 'branch_line' line of the C source corresponds to actual
    branching instructions in the assembly code. Also, check if that
    line is covered. If it's not covered, this branching statement can
    be omitted from the report.
    Returns False and prints an error message if check is not successful,
    True otherwise

    :param branch_line: Source code line with the branch instruction
    :param lines_dict: Dictionary of lines with line number as key
                        and its data as value
    :param abs_path_file: File name of the source file
    """
    if str(branch_line) not in lines_dict:
        return False
    found_branching = False
    for i in lines_dict[str(branch_line)]['elf_index']:
        for j in lines_dict[str(branch_line)]['elf_index'][i]:
            string = lines_dict[str(branch_line)]['elf_index'][i][j][0]
            # these cover all the possible branching instructions
            if ('\tb' in string or
                '\tcbnz' in string or
                '\tcbz' in string or
                '\ttbnz' in string or
                    '\ttbz' in string):
                # '\tbl' in string or  # already covered by '\tb'
                # '\tblr' in string or  # already covered by '\tb'
                # '\tbr' in string or  # already covered by '\tb'
                found_branching = True
    if not found_branching:
        error_log.write(
            '\nSomething possibly wrong:\n\tFile ' +
            abs_path_file +
            ', line ' +
            str(branch_line) +
            '\n\tshould be a branching statement but couldn\'t ' +
            'find correspondence in assembly code')
    return True


def manage_if_branching(branch_line, lines_dict, info_file, abs_path_file):
    """
    Takes care of branch coverage, branch_line is the source code
    line in which the 'if' statement is located the function produces
    branch coverage info based on C source code and json file content

    :param branch_line: Source code line with the 'if' instruction
    :param lines_dict: Dictionary of lines with line number as key
                        and its data as value
    :param info_file: Handler to for file writing coverage
    :param abs_path_file: File name of the source file
    """
    total_branch_local = 0
    covered_branch_local = 0

    if not sanity_check(branch_line, lines_dict, abs_path_file):
        return(total_branch_local, covered_branch_local)
    total_branch_local += 2
    current_line = branch_line  # used to read lines one by one
    # check for multiline if-condition and update current_line accordingly
    parenthesis_count = 0
    while True:
        end_of_condition = False
        for char in lines[current_line]:
            if char == ')':
                parenthesis_count -= 1
                if parenthesis_count == 0:
                    end_of_condition = True
            elif char == '(':
                parenthesis_count += 1
        if end_of_condition:
            break
        current_line += 1
    # first branch
    # simple case: 'if' statements with no braces
    if '{' not in lines[current_line] and '{' not in lines[current_line + 1]:

        if (str(current_line + 1) in lines_dict and
                lines_dict[str(current_line + 1)]['covered']):
            info_file.write('BRDA:' + str(branch_line) + ',0,' + '0,' + '1\n')
            covered_branch_local += 1
        else:
            info_file.write('BRDA:' + str(branch_line) + ',0,' + '0,' + '0\n')
        current_line += 1

    # more complex case: '{' after the 'if' statement
    else:
        if '{' in lines[current_line]:
            current_line += 1
        else:
            current_line += 2

        # we need to check whether at least one line in the block is covered
        found_covered_line = False

        # this is a simpler version of a stack used to check when a code block
        # ends at the moment, it just checks for '{' and '}', doesn't take into
        # account the presence of commented braces
        brace_counter = 1
        while True:
            end_of_block = False
            for char in lines[current_line]:
                if char == '}':
                    brace_counter -= 1
                    if brace_counter == 0:
                        end_of_block = True
                elif char == '{':
                    brace_counter += 1
            if end_of_block:
                break
            if (str(current_line) in lines_dict and
                    lines_dict[str(current_line)]['covered']):
                found_covered_line = True

            current_line += 1

        if found_covered_line:
            info_file.write('BRDA:' + str(branch_line) + ',0,' + '0,' + '1\n')
            covered_branch_local += 1
        else:
            info_file.write('BRDA:' + str(branch_line) + ',0,' + '0,' + '0\n')

    # second branch (if present). If not present, second branch is covered by
    # default
    current_line -= 1
    candidate_else_line = current_line
    while 'else' not in lines[current_line] and candidate_else_line + \
            2 >= current_line:
        current_line += 1
        if current_line == len(lines):
            break

    # no 'else': branch covered by default
    if current_line == candidate_else_line + 3:
        info_file.write('BRDA:' + str(branch_line) + ',0,' + '1,' + '1\n')
        covered_branch_local += 1
        return(total_branch_local, covered_branch_local)

    # 'else' found: check if opening braces are present
    if '{' not in lines[current_line - 1] and '{' not in lines[current_line]:
        if str(current_line + 1) in lines_dict:
            if lines_dict[str(current_line + 1)]['covered']:
                info_file.write(
                    'BRDA:' +
                    str(branch_line) +
                    ',0,' +
                    '1,' +
                    '1\n')
                covered_branch_local += 1
            else:
                info_file.write(
                    'BRDA:' +
                    str(branch_line) +
                    ',0,' +
                    '1,' +
                    '0\n')
        else:
            info_file.write('BRDA:' + str(branch_line) + ',0,' + '1,' + '0\n')

    else:
        if '{' in lines[current_line]:
            current_line += 1
        else:
            current_line += 2
        found_covered_line = False
        while '}' not in lines[current_line]:
            if (str(current_line) in lines_dict and
                    lines_dict[str(current_line)]['covered']):
                found_covered_line = True
                break
            current_line += 1
        if found_covered_line:
            info_file.write('BRDA:' + str(branch_line) + ',0,' + '1,' + '1\n')
            covered_branch_local += 1
        else:
            info_file.write('BRDA:' + str(branch_line) + ',0,' + '1,' + '0\n')

    return(total_branch_local, covered_branch_local)


def manage_switch_branching(switch_line, lines_dict, info_file, abs_path_file):
    """
    Takes care of branch coverage, branch_line is the source code
    line in which the 'switch' statement is located the function produces
    branch coverage info based on C source code and json file content

    :param switch_line: Source code line with the 'switch' instruction
    :param lines_dict: Dictionary of lines with line number as key
                        and its data as value
    :param info_file: Handler to for file writing coverage
    :param abs_path_file: File name of the source file
    """

    total_branch_local = 0
    covered_branch_local = 0

    if not sanity_check(switch_line, lines_dict, abs_path_file):
        return(total_branch_local, covered_branch_local)

    current_line = switch_line  # used to read lines one by one
    branch_counter = 0          # used to count the number of switch branches
    brace_counter = 0

    # parse the switch-case line by line, checking if every 'case' is covered
    # the switch-case ends with a '}'
    while True:
        if '{' in lines[current_line]:
            brace_counter += 1
        if '}' in lines[current_line]:
            brace_counter -= 1
        if brace_counter == 0:
            return(total_branch_local, covered_branch_local)
        if 'case' in lines[current_line] or 'default' in lines[current_line]:
            covered = False
            total_branch_local += 1
            inner_brace = 0
            current_line += 1
            while (('case' not in lines[current_line]
                   and 'default' not in lines[current_line]) or
                   inner_brace > 0):
                if (str(current_line) in lines_dict and
                        lines_dict[str(current_line)]['covered']):
                    covered = True
                if '{' in lines[current_line]:
                    inner_brace += 1
                    brace_counter += 1
                if '}' in lines[current_line]:
                    inner_brace -= 1
                    brace_counter -= 1
                if brace_counter == 0:
                    break
                current_line += 1
            if covered:
                info_file.write(
                    'BRDA:' +
                    str(switch_line) +
                    ',0,' +
                    str(branch_counter) +
                    ',1\n')
                covered_branch_local += 1
            else:
                info_file.write(
                    'BRDA:' +
                    str(switch_line) +
                    ',0,' +
                    str(branch_counter) +
                    ',0\n')
            if brace_counter == 0:
                return(total_branch_local, covered_branch_local)
            branch_counter += 1
        else:
            current_line += 1

    return(total_branch_local, covered_branch_local)


def branch_coverage(abs_path_file, info_file, lines_dict):
    """
    Produces branch coverage information, using the functions
    'manage_if_branching' and 'manage_switch_branching'

    :param abs_path_file: File name of the source file
    :param info_file: Handler to for file writing coverage
    :param lines_dict: Dictionary of lines with line number as key
                       and its data as value
    """
    total_branch = 0
    covered_branch = 0

    # branch coverage: if statements
    branching_lines = []

    # regex: find all the lines starting with 'if' or 'else if'
    # (possibly preceded by whitespaces/tabs)
    pattern = re.compile(r"^\s+if|^\s+} else if|^\s+else if")
    for i, line in enumerate(open(abs_path_file)):
        for match in re.finditer(pattern, line):
            branching_lines.append(i + 1)
    while branching_lines:
        t = manage_if_branching(branching_lines.pop(0), lines_dict,
                                info_file, abs_path_file)
        total_branch += t[0]
        covered_branch += t[1]

    # branch coverage: switch statements
    switch_lines = []

    # regex: find all the lines starting with 'switch'
    # (possibly preceded by whitespaces/tabs)
    pattern = re.compile(r"^\s+switch")
    for i, line in enumerate(open(abs_path_file)):
        for match in re.finditer(pattern, line):
            switch_lines.append(i + 1)
    while switch_lines:
        t = manage_switch_branching(switch_lines.pop(0), lines_dict,
                                    info_file, abs_path_file)
        total_branch += t[0]
        covered_branch += t[1]

    info_file.write('BRF:' + str(total_branch) + '\n')
    info_file.write('BRH:' + str(covered_branch) + '\n')


parser = argparse.ArgumentParser(
    description="Script to convert intermediate json file to LCOV info file")
parser.add_argument('--workspace', metavar='PATH',
                    help='Folder with source files structure',
                    required=True)
parser.add_argument('--json', metavar='PATH',
                    help='Intermediate json file name',
                    required=True)
parser.add_argument('--info', metavar='PATH',
                    help='Output info file name',
                    default="coverage.info")
args = parser.parse_args()
with open(args.json) as json_file:
    json_data = json.load(json_file)
info_file = open(args.info, "w+")
error_log = open("error_log.txt", "w+")
file_list = json_data['source_files'].keys()

for relative_path in file_list:
    abs_path_file = os.path.join(args.workspace, relative_path)
    if not os.path.exists(abs_path_file):
        continue
    source = open(abs_path_file)
    lines = source.readlines()
    info_file.write('TN:\n')
    info_file.write('SF:' + os.path.abspath(abs_path_file) + '\n')
    lines = [-1] + lines  # shifting the lines indexes to the right
    function_coverage(
        json_data['source_files'][relative_path]['functions'].items(),
        info_file)
    branch_coverage(abs_path_file, info_file,
                    json_data['source_files'][relative_path]['lines'])
    line_coverage(json_data['source_files'][relative_path]['lines'],
                  info_file)
    info_file.write('end_of_record\n\n')
    source.close()

json_file.close()
info_file.close()
error_log.close()
