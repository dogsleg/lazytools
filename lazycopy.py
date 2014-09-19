#!/usr/bin/python
########################################################################
#
# lazycopy -- lazy copy tool for Debian webwml repository
#
# Copyright (C) 2013-2014  Lev Lamberov <l.lamberov@gmail.com>
#
# This program is licensed under the GNU General Public License (GPL).
# you can redistribute it and/or modify it under the terms of the GNU
# General Public License as published by the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA; either
# version 3 of the License, or (at your option) any later version.
# The GPL is available online at http://www.gnu.org/copyleft/gpl.html
# or in /usr/share/common-licenses/GPL-3
#
########################################################################
#
# Configuration
#
########################################################################
#
# Configuration file should have a section [lazycopy] and may contain the
# following options: language, maintainer, editor, temp_dir, diff_args.
# Some of these options can be empty (as editor and temp_dir options in
# the following example).
#
# Command-line arguments override options in the configuration file. If
# editor is not specified, lazycopy will use symlink /usr/bin/editor. You
# can change it with update-alternatives command. If temp_dir is not
# specified, then /tmp will be used to store patches. If diff_args is not
# specified, then lazycopy will produce unified diff (with diff -u
# command). If maintainer is not specified, then information about
# maintainer will not be added to translation file. But you have to
# specify target language either in configuration file, or by argument.
#
# Example of configuration file:
#
# [lazycopy]
# language = russian
# maintainer = Lev Lamberov
# editor =
# temp_dir =
# diff_args = -yw --minimal
#
########################################################################

_VERSION_ = '0.2.2'

import argparse
import sys
import os
import subprocess

if sys.version_info < (3, 0):
    import ConfigParser as configparser
else:
    import configparser

# Command-line arguments PARSER

PARSER = argparse.ArgumentParser(description="Copies the specified page to the corresponding directory of the specified language and adds the translation-check header with the current revision, optionally adds also the MAINTAINER name. If the directory does not exist, it will be created, and the Makefile created. If the translation of the file already exists in the target language directory either because it was removed (and is in the Attic) or has been removed locally the program will abort and warn the user (unless '-nu' is used)")

PARSER.add_argument('path', metavar='path', type=str,
                    help='Sets file for the translation')
PARSER.add_argument('-l', '--language', metavar='language', type=str,
                    help='''Sets language for the translation.''')
PARSER.add_argument('-m', '--maintainer', metavar='maintainer', type=str,
                    help='Sets maintainer for the translation.')
PARSER.add_argument('-e', '--editor', metavar='editor', type=str,
                    help='Sets editor')
PARSER.add_argument('-t', '--temp_dir', metavar='temp_dir', type=str,
                    help='Sets temporary directory')
PARSER.add_argument('-d', '--diff_args', metavar='diff_args', type=str,
                    help='Sets diff arguments')
PARSER.add_argument('-f', '--list-file', metavar='list_file', type=str,
                    help='Sets list file')
PARSER.add_argument('-nc', '--not-check', action='store_const', const=True,
                    default=False,
                    help='Does not check status of target files in CVS')
PARSER.add_argument('-nu', '--not-update', action='store_const', const=True,
                    default=False,
                    help='Does not update specified')
PARSER.add_argument('-ne', '--not-edit', action='store_const', const=True,
                    default=False,
                    help='Does not run editor and produce patch')
PARSER.add_argument('-nd', '--not-diff', action='store_const', const=True,
                    default=False,
                    help='Does not produce patch')

ARGS = PARSER.parse_args()

# Check specified file to be a valid (wml, src) page

PATH_LIST = ARGS.path.split('/')
if 'wml' not in PATH_LIST[-1] and 'src' not in PATH_LIST[-1]:
    print("ERROR: specified file doesn't seem to be a valid page.")
    sys.exit(1)

# Configuration

if os.path.exists('lazycopy.conf'):
    CONFIG = configparser.RawConfigParser()
    CONFIG.read('lazycopy.conf')
else:
    print('Configuration file lazycopy.conf not found. You can specify lazycopy your default option in it, instead of using arguments all the time.')

TARGET_LANGUAGE = ARGS.language or CONFIG.get('lazycopy', 'language')

if not TARGET_LANGUAGE:
    print('ERROR: specify target language in configuration file or by argument.')
    sys.exit(1)

MAINTAINER = ARGS.maintainer or CONFIG.get('lazycopy', 'maintainer')

if not MAINTAINER:
    print('You can specify maintainer in configuration file or by argument.')

EDITOR = ARGS.editor or CONFIG.get('lazycopy', 'editor')

if not EDITOR:
    if os.path.exists('/usr/bin/editor'):
        EDITOR = '/usr/bin/editor'
    else:
        print("Editor is not specified, symlink /usr/bin/editor doesn't exits, not running editor. Use update-alternatives or specify editor in configuration file of by argument.")

TEMP_DIR = ARGS.temp_dir or CONFIG.get('lazycopy', 'temp_dir')

if not TEMP_DIR:
    print('Using /tmp as temporary directory. You can specify temporary directory in configuration file or by argument.')
    TEMP_DIR = '/tmp'

DIFF_ARGS = ARGS.diff_args or CONFIG.get('lazycopy', 'diff_args')

if not DIFF_ARGS:
    print('Will prepare unified diff. You can specify diff arguments in configuration file or by argument.')
    DIFF_ARGS = '-u'

LIST_FILE = ARGS.list_file or CONFIG.get('lazycopy', 'list_file')

if not LIST_FILE:
    print('Using /tmp/webwml_list.tmp as a list file. You can specify list file in configuration file or by argument.')
    LIST_FILE = '/tmp/webwml_list.tmp'

TARGET_PATH = TARGET_LANGUAGE + '/' + '/'.join(PATH_LIST[1:-1])
TARGET_FILE = TARGET_PATH + '/' + PATH_LIST[-1]
PATH_FILE = '/tmp/' + "_".join(PATH_LIST[1:]) + '.' + ARGS.path[:2] + '_' + TARGET_LANGUAGE[:2] + '.patch'
LIST_FILE_ENTRY = '/'.join(PATH_LIST[1:])
SOURCE_MAKEFILE = '/'.join(PATH_LIST[:-1]) + '/Makefile'
TARGET_MAKEFILE = TARGET_LANGUAGE + '/' + '/'.join(PATH_LIST[1:-1]) + '/Makefile'

def get_revision_number():
    cvs_entries_file = open('/'.join(PATH_LIST[:-1]) + '/CVS/Entries', 'r')
    for line in cvs_entries_file:
        if PATH_LIST[-1] in line:
            return line.split('/')[2]

def make_title():
    title = '#use wml::debian::translation-check translation="' + get_revision_number() + '"'
    if MAINTAINER:
        title += ' maintainer="' + MAINTAINER + '"'
    return title

def check_status():
    print(('Checking status of ' + TARGET_FILE))
    cvs = subprocess.Popen(['cvs', 'status', TARGET_FILE],
                           stdout=subprocess.PIPE)
    out, err = cvs.communicate()
    if cvs.returncode:
        return
    cvs_status = out.split('\n')
    for entry in cvs_status:
        if 'Status' in entry:
            if 'Unknown' in entry.split()[-1]:
                return
        if 'Repository revision' in entry:
            if 'Attic' in entry.split()[-1]:
                print('ERROR: An old translation exists in the Attic, you should restore it using:')
                print(('cvs update -j DELETED -j PREVIOUS' + TARGET_FILE))
                print('[Edit and update the file]')
                print(('cvs ci ' + TARGET_FILE))
                return
    print("ERROR: A translation already exists in CVS for this file.")
    print("Please update your CVS copy using 'cvs update'.")
    sys.exit(1)

print(('Copying ' + ARGS.path))
if not os.path.exists(ARGS.path):
    print('ERROR: specified file does not exist.')
    sys.exit(1)
if not ARGS.not_check:
    check_status()
if not os.path.exists(TARGET_PATH):
    os.makedirs(TARGET_PATH)
if not os.path.exists(TARGET_MAKEFILE):
    MAKEFILE = open(TARGET_PATH + '/Makefile', 'w')
    MAKEFILE.write('include $(subst webwml/' + TARGET_LANGUAGE + ',webwml/english,$(CURDIR))/Makefile\n')
    MAKEFILE.close()
if not ARGS.not_update:
    print('Updating specified file.')
    subprocess.call(['cvs', 'update', ARGS.path])
SRC_FILE = open(ARGS.path, 'r')
DEST_FILE = open(TARGET_FILE, 'w')
SRC_FILE_CONTENTS = SRC_FILE.read().split('\n')
INSERTED_TITLE = False
for line in SRC_FILE_CONTENTS:
    line += '\n'
    if line[0] != '#' and not INSERTED_TITLE:
        DEST_FILE.write(make_title() + '\n')
        DEST_FILE.write(line)
        INSERTED_TITLE = True
    else:
        DEST_FILE.write(line)
DEST_FILE.close()

if not ARGS.not_edit:
    print(('Running editor to edit ' + TARGET_FILE))
    subprocess.call([EDITOR, TARGET_FILE])

if not ARGS.not_diff:
    DIFF_STRING = 'diff ' + DIFF_ARGS + ' ' + ARGS.path + ' ' + TARGET_FILE + ' > ' +  PATH_FILE
    print(('Running ' + DIFF_STRING))
    subprocess.call(DIFF_STRING, shell=True)

def simplify(data):
    matched = ''
    nonmatched = []
    nonmatch_num = -1
    for num in range(len(data[1]) - 1):
        simplification = False
        for item in data[0:]:
            if len(item) - 1 >= num:
                if  data[1][num] == item[num]:
                    simplification = True
                elif data[1][num] != item[num]:
                    simplification = False
                    nonmatch_num = num
                    break
        if simplification:
            matched = matched + data[1][num]
        else:
            break
    for item in data:
        nonmatched.append(item[nonmatch_num:])
    return matched, nonmatched

def reverse(list_str):
    pre_output = []
    for entry in list_str[1]:
        pre_output.append(entry[::-1])
    reverse_simplified = simplify(pre_output)
    output_str = ''
    for entry in reverse_simplified:
        if isinstance(entry, str):
            output_str = output_str + entry[::-1]
        elif isinstance(entry, list):
            output_lst = []
            for item in entry:
                output_lst.append(item[::-1])
    return output_lst, output_str

if os.path.exists(LIST_FILE):
    print(('Adding new entry to list file.'))
    TMP_LIST_FILE = open(LIST_FILE, 'r')
    RAW_DATA = TMP_LIST_FILE.read()[6:].split('{')

    RAW_DATA[1] = RAW_DATA[1][:-1]
    RAW_DATA[1] = RAW_DATA[1].split('}')
    RAW_DATA.append(RAW_DATA[1].pop(1))

    EXPANDED_DATA = []

    for entry in RAW_DATA[1][0].split(','):
        EXPANDED_DATA.append(RAW_DATA[0] + entry + RAW_DATA[2])

    EXPANDED_DATA.append(LIST_FILE_ENTRY)

    RESULT = 'wml://' + simplify(EXPANDED_DATA)[0] + '{' + ','.join(reverse(simplify(EXPANDED_DATA))[0]) + '}' + reverse(simplify(EXPANDED_DATA))[1] + '\n'

    TMP_LIST_FILE.close()
else:
    print(('Creating a new list file.'))
    TMP_LIST_FILE = open(LIST_FILE, 'w')
    RESULT = 'wml://{' + LIST_FILE_ENTRY + '}\n'

print(('Resulting list file string is as follows.'))
print(RESULT)
TMP_LIST_FILE = open(LIST_FILE, 'w')
TMP_LIST_FILE.write(RESULT)
TMP_LIST_FILE.close()
