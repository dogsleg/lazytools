#!/usr/bin/python3
###############################################################################
#
# lazycopy -- lazy copy tool for Debian webwml repository
#
# Copyright (C) 2013-2016  Lev Lamberov <dogsleg@debian.org>
#
# This program is licensed under the GNU General Public License (GPL). you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, Inc., 59 Temple Place,
# Suite 330, Boston, MA 02111-1307 USA; either version 3 of the License, or (at
# your option) any later version.
# The GPL is available online at http://www.gnu.org/copyleft/gpl.html
# or in /usr/share/common-licenses/GPL-3
#
###############################################################################
#
# Configuration
#
###############################################################################
#
# Configuration file should have a section [lazycopy] and may contain the
# following options: language, maintainer, editor, temp_dir, diff_args. Some of
# these options can be empty (as editor and temp_dir options in the following
# example).
#
# Command-line arguments override options in the configuration file. If editor
# is not specified, lazycopy will use symlink /usr/bin/editor. You can change
# it with update-alternatives command. If temp_dir is not specified, then /tmp
# will be used to store patches. If diff_args is not specified, then lazycopy
# will produce unified diff (with diff -u command). If maintainer is not
# specified, then information about maintainer will not be added to translation
# file. But you have to specify target language either in configuration file,
# or by argument.
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
###############################################################################

_VERSION_ = '0.3.1'

import argparse
import configparser
import os
import subprocess
import sys


class colors(object):
    error = '\033[41m[ERROR]\033[0m '
    warning = '\e[43m[WARNING]\033[0m '
    success = '\033[42m[DONE]\033[0m '
    info = '\033[44m[INFO]\033[0m '


class Configuration(object):
    def __init__(self, args):
        self.path = args.path
        self.check_target_file()
        self.no_check = args.no_check
        self.no_update = args.no_update
        self.no_edit = args.no_edit
        self.no_diff = args.no_diff

        if os.path.exists('lazycopy.conf'):
            cfg_file = configparser.RawConfigParser()
            cfg_file.read('lazycopy.conf')
        else:
            print(colors.info + "Configuration file lazycopy.conf not found.")

        self.target_lang = args.language or cfg_file.get(
            'lazycopy', 'language')
        if not self.target_lang:
            print(colors.error + "Specify target language in configuration "
                  "file or with argument.")
            sys.exit(1)

        self.maintainer = args.maintainer or cfg_file.get(
            'lazycopy', 'maintainer')
        if not self.maintainer:
            print(colors.info + "You can specify maintainer in configuration "
                  "file or with argument.")

        self.editor = args.editor or cfg_file.get('lazycopy', 'editor')
        if not self.editor:
            if os.path.exists('/usr/bin/editor'):
                self.editor = '/usr/bin/editor'
            else:
                print(colors.warning + "Editor is not specified, symlink "
                      "/usr/bin/editor doesn't exits, not running editor.")

        self.temp_dir = args.temp_dir or cfg_file.get('lazycopy', 'temp_dir')
        if not self.temp_dir:
            print(colors.info + "Using /tmp as temporary directory.")
            self.temp_dir = '/tmp'

        self.diff_args = args.diff_args or cfg_file.get(
            'lazycopy', 'diff_args')
        if not self.diff_args:
            print(colors.info + "Will prepare unified diff.")
            self.diff_args = '-u'

        self.list_file = args.list_file or cfg_file.get(
            'lazycopy', 'list_file')
        if not self.list_file:
            print(colors.info + "Using /tmp/webwml_list.tmp as a list file.")
            self.list_file = '/tmp/webwml_list.tmp'

        self.lang_code = self.target_lang[:2]
        self.path_lst = self.path.split('/')
        self.path_lst2 = self.path_lst[1:]
        self.target_path = self.target_lang + \
            '/' + '/'.join(self.path_lst[1:-1])
        self.target_file = self.target_path + '/' + self.path_lst[-1]
        self.patch_file = '/tmp/' + '_'.join(self.path_lst2) + '.' + \
                          self.path[:2] + '_' + self.lang_code + '.patch'
        self.lst_file_entry = '/'.join(self.path_lst2)
        self.source_makefile = '/'.join(self.path_lst[:-1]) + '/Makefile'
        self.target_makefile = self.target_lang + '/' + \
            '/'.join(self.path_lst[1:-1]) + '/Makefile'

    def check_target_file(self):
        # Check specified file to be a valid (wml, src) page
        self.path_lst = self.path.split('/')
        if 'wml' not in self.path_lst[-1] and 'src' not in self.path_lst[-1]:
            print(colors.error + "Specified file doesn't seem to be a valid "
                  "page.")
            sys.exit(1)

    def revision_number(self):
        cvs_entries_file = '/'.join(self.path_lst[:-1]) + '/CVS/Entries'
        cvs_entries = open(cvs_entries_file, 'r')
        for line in cvs_entries:
            if self.path_lst[-1] in line:
                return line.split('/')[2]

    def make_title(self):
        title = '#use wml::debian::translation-check translation="' + \
                self.revision_number() + '"'
        if self.maintainer:
            title += ' maintainer="' + self.maintainer + '"'
        return title

    def make_Makefile(self):
        return 'include $(subst webwml/' + self.target_lang + \
            ',webwml/english,$(CURDIR))/Makefile\n'

    def make_diff(self):
        return 'diff ' + self.diff_args + ' ' + self.path + ' ' + \
            self.target_file + ' > ' + self.patch_file


def check_status(target_file):
    print(colors.info + "Checking status of " + target_file)
    cvs = subprocess.Popen(['cvs', 'status', target_file],
                           stdout=subprocess.PIPE)
    #out, err = cvs.communicate()
    out = cvs.communicate()
    if cvs.returncode:
        return
    out = out[0].decode('utf-8')
    cvs_status = out.split('\n')
    for entry in cvs_status:
        if 'Status' in entry:
            if 'Unknown' in entry.split()[-1]:
                return
        if 'Repository revision' in entry:
            if 'Attic' in entry.split()[-1]:
                print(colors.error + "An old translation exists in the "
                      "Attic, you should restore it using:")
                print(colors.info + "cvs update -j DELETED -j PREVIOUS" +
                      target_file)
                print(colors.info + "Edit and update the file")
                print(colors.info + "cvs ci " + target_file)
                return
    print(colors.error + "A translation already exists in CVS for this file.")
    print(colors.error + "Please update your CVS copy using 'cvs update'.")
    sys.exit(1)


def copy_original(config):
    print(colors.info + "Copying " + config.path)
    if not os.path.exists(config.path):
        print(colors.error + "Specified file does not exist.")
        sys.exit(1)
    if not config.no_check:
        check_status(config.target_file)
    if not os.path.exists(config.target_path):
        os.makedirs(config.target_path)
    if not os.path.exists(config.target_makefile):
        makefile = open(config.target_path + '/Makefile', 'w')
        makefile.write(config.make_Makefile())
        makefile.close()
    if not config.no_update:
        print(colors.info + "Updating specified file.")
        subprocess.call(['cvs', 'update', config.path])
    src_file = open(config.path, 'r')
    dest_file = open(config.target_file, 'w')
    src_file_contents = src_file.read().split('\n')
    inserted_title = False
    for line in src_file_contents:
        line += '\n'
        if line[0] != '#' and not inserted_title:
            dest_file.write(config.make_title() + '\n')
            dest_file.write(line)
            inserted_title = True
        else:
            dest_file.write(line)
    dest_file.close()


def run_editor(editor, target_file):
    print(colors.info + "Running editor to edit " + target_file)
    subprocess.call([editor, target_file])


def run_diff(diff_string):
    print(colors.info + "Running " + diff_string)
    subprocess.call(diff_string, shell=True)


def simplify(data):
    matched = ''
    nonmatched = []
    nonmatch_num = -1
    for num in range(len(data[1]) - 1):
        simplification = False
        for item in data[0:]:
            if len(item) - 1 >= num:
                if data[1][num] == item[num]:
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


def make_pseudolink(list_file, lst_file_entry):
    if os.path.exists(list_file):
        print(colors.info + "Adding new entry to list file.")
        tmp_list_file = open(list_file, 'r')
        raw_data = tmp_list_file.read()[6:].split('{')
        tmp_list_file.close()
        raw_data[1] = raw_data[1][:-1]
        raw_data[1] = raw_data[1].split('}')
        raw_data.append(raw_data[1].pop(1))
        expanded_data = []
        for entry in raw_data[1][0].split(','):
            expanded_data.append(raw_data[0] + entry + raw_data[2])
        expanded_data.append(lst_file_entry)
        result = 'wml://' + simplify(expanded_data)[0] + '{' + \
                 ','.join(reverse(simplify(expanded_data))[0]) + '}' + \
                 reverse(simplify(expanded_data))[1] + '\n'
    else:
        print(colors.info + "Creating a new list file.")
        result = 'wml://{' + lst_file_entry + '}\n'
    tmp_list_file = open(list_file, 'w')
    tmp_list_file.write(result)
    tmp_list_file.close()
    print(colors.success + result)


if __name__ == '__main__':
    # Command-line arguments parser
    parser = argparse.ArgumentParser(description="Copies the specified page "
                                     "to the corresponding directory of the "
                                     "specified language and adds the "
                                     "translation-check header with the "
                                     "current revision, optionally adds also "
                                     "the MAINTAINER name. If the directory "
                                     "does not exist, it will be created, "
                                     "and the Makefile created. If the "
                                     "translation of the file already exists "
                                     "in the target language directory "
                                     "either because it was removed (and is "
                                     "in the Attic) or has been removed "
                                     "locally the program will abort and "
                                     "warn the user (unless '-nu' is used)")

    parser.add_argument('path', metavar='path', type=str,
                        help="Sets file for the translation")
    parser.add_argument('-l', '--language', metavar='language', type=str,
                        help="Sets language for the translation.")
    parser.add_argument('-m', '--maintainer', metavar='maintainer', type=str,
                        help="Sets maintainer for the translation.")
    parser.add_argument('-e', '--editor', metavar='editor', type=str,
                        help="Sets editor")
    parser.add_argument('-t', '--temp_dir', metavar='temp_dir', type=str,
                        help="Sets temporary directory")
    parser.add_argument('-d', '--diff_args', metavar='diff_args', type=str,
                        help="Sets diff arguments")
    parser.add_argument('-f', '--list-file', metavar='list_file', type=str,
                        help="Sets list file")
    parser.add_argument('-nc', '--no-check', action='store_const', const=True,
                        default=False,
                        help="Does not check status of target files in CVS")
    parser.add_argument('-nu', '--no-update', action='store_const', const=True,
                        default=False,
                        help="Does not update specified")
    parser.add_argument('-ne', '--no-edit', action='store_const', const=True,
                        default=False,
                        help="Does not run editor and produce patch")
    parser.add_argument('-nd', '--no-diff', action='store_const', const=True,
                        default=False,
                        help="Does not produce patch")

    config = Configuration(parser.parse_args())

    copy_original(config)

    if not config.no_edit:
        run_editor(config.editor, config.target_file)
    if not config.no_diff:
        run_diff(config.make_diff())

    make_pseudolink(config.list_file, config.lst_file_entry)
