#!/usr/bin/python
########################################################################
#
# lazycopy -- lazy copy tool for Debian webwml repository
#
# Copyright (C) 2013  Lev Lamberov <l.lamberov@gmail.com>
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

_version_ = '0.1.1'

import argparse
import sys
import os
import subprocess

if sys.version_info < (3, 0):
    import ConfigParser as configparser
else:
    import configparser

# Command-line arguments parser

parser = argparse.ArgumentParser(description="Copies the specified page to the corresponding directory of the specified language and adds the translation-check header with the current revision, optionally adds also the maintainer name. If the directory does not exist, it will be created, and the Makefile created. If the translation of the file already exists in the target language directory either because it was removed (and is in the Attic) or has been removed locally the program will abort and warn the user (unless '-nu' is used)")

parser.add_argument('path', metavar='path', type=str,
                    help='Sets file for the translation')
parser.add_argument('-l', '--language',  metavar='LANGUAGE', type=str,
                    help='''Sets language for the translation. Overrides configuration file.''')
parser.add_argument('-m', '--maintainer', metavar='MAINTAINER', type=str,
                    help='Sets maintainer for the translation. Overrides configuration file.')
parser.add_argument('-e', '--editor', metavar='EDITOR', type=str,
                    help='Sets editor')
parser.add_argument('-t', '--temp_dir', metavar='TEMP_DIR', type=str,
                    help='Sets temporary directory')
parser.add_argument('-d', '--diff_args', metavar='DIFF_ARGS', type=str,
                    help='Sets diff arguments')
parser.add_argument('-nc', '--not-check', action='store_const', const=True,
                    default=False, help='Does not check status of target files in CVS')
parser.add_argument('-nu', '--not-update', action='store_const', const=True,
                    default=False, help='Does not update specified')
parser.add_argument('-ne', '--not-edit', action='store_const', const=True,
                    default=False, help='Does not run editor and produce patch, just copy the file')
parser.add_argument('-nd', '--not-diff', action='store_const', const=True,
                    default=False, help='Does not produce patch, just copy the file and edit it')

args = parser.parse_args()

# Check specified file to be a valid (wml, src) page

path_list = args.path.split('/')
if 'wml' not in path_list[-1] and 'src' not in path_list[-1]:
    print("ERROR: specified file doesn't seem to be a valid page.")
    sys.exit(1)

# Configuration

if os.path.exists('lazycopy.conf'):
    config = configparser.RawConfigParser()
    config.read('lazycopy.conf')
else:
    print('Configuration file lazycopy.conf not found. You can specify lazycopy your default option in it, instead of using arguments all the time.')

target_language = args.language or config.get('lazycopy', 'language')

if not target_language:
    print('ERROR: specify target language in configuration file or by argument.')
    sys.exit(1)

maintainer = args.maintainer or config.get('lazycopy', 'maintainer')

if not maintainer:
    print('You can specify maintainer in configuration file or by argument.')

editor = args.editor or config.get('lazycopy', 'editor')

if not editor:
    if os.path.exists('/usr/bin/editor'):
        editor = '/usr/bin/editor'
    else:
        print("Editor is not specified, symlink /usr/bin/editor doesn't exits, not running editor. Use update-alternatives or specify editor in configuration file of by argument.")

temp_dir = args.temp_dir or config.get('lazycopy', 'temp_dir')

if not temp_dir:
    print('Using /tmp as temporary directory. You can specify temporary directory in configuration file or by argument.')
    temp_dir = '/tmp'

diff_args = args.diff_args or config.get('lazycopy', 'diff_args')

if not diff_args:
    print('Will prepare unified diff. You can specify diff arguments in configuration file or by argument.')
    diff_args = '-u'

target_path = target_language + '/' + '/'.join(path_list[1:-1])
target_file = target_path + '/' + path_list[-1]
patch_file = '/tmp/' + "_".join(path_list[1:]) + '.' + args.path[:2] + '_' + target_language[:2] + '.patch'
source_makefile = '/'.join(path_list[:-1]) + '/Makefile'
target_makefile = target_language + '/' + '/'.join(path_list[1:-1]) + '/Makefile'

def get_revision_number():
    cvs_entries_file = open('/'.join(path_list[:-1]) + '/CVS/Entries', 'r')
    for line in cvs_entries_file:
        if path_list[-1] in line:
            return line.split('/')[2]

def make_title():
    title = '#use wml::debian::translation-check translation="' + get_revision_number() + '"'
    if maintainer:
        title += ' maintainer="' + maintainer + '"'
    return title

def check_status():
    print(('Checking status of ' + target_file))
    cvs = subprocess.Popen(['cvs', 'status', target_file], stdout=subprocess.PIPE)
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
                print(('cvs update -j DELETED -j PREVIOUS' + target_file))
                print('[Edit and update the file]')
                print(('cvs ci ' + target_file))
                return
    print("ERROR: A translation already exists in CVS for this file.")
    print("Please update your CVS copy using 'cvs update'.")
    sys.exit(1)
    
print(('Copying ' + args.path))
if not os.path.exists(args.path):
    print('ERROR: specified file does not exist.')
    sys.exit(1)
if not args.not_check:
    check_status()
if not os.path.exists(target_path):
    os.makedirs(target_path)
if not os.path.exists(target_makefile):
    makefile = open(target_path + '/Makefile', 'w')
    makefile.write('include $(subst webwml/' + target_language + ',webwml/english,$(CURDIR))/Makefile\n')
    makefile.close()
if not args.not_update:
    print('Updating specified file.')
    subprocess.call(['cvs', 'update', args.path])
src_file = open(args.path, 'r')
dest_file = open(target_file, 'w')
src_file_contents = src_file.read().split('\n')
inserted_title = False
for line in src_file_contents:
    line += '\n'
    if line[0] != '#' and not inserted_title:
        dest_file.write(make_title() + '\n')
        dest_file.write(line)
        inserted_title = True
    else:
        dest_file.write(line)
dest_file.close()

if not args.not_edit:
    print(('Running editor to edit ' + target_file))
    subprocess.call([editor, target_file])

if not args.not_diff:
    diff_string = 'diff ' + diff_args + ' ' + args.path + ' ' + target_file + ' > ' +  patch_file
    print(('Running ' + diff_string))
    subprocess.call(diff_string, shell=True)
