#!/usr/bin/python3

########################################################################
#
# up -- process todo for Debian website translators
#
# Copyright (C) 2024  Lev Lamberov <dogsleg@debian.org>
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

_VERSION_ = '0.0.1'

import argparse
import subprocess
from urllib.request import urlopen

from bs4 import BeautifulSoup


def quicksort(lst):
    """Quicksort using list comprehensions"""
    if lst == []:
        return []
    else:
        pivot = lst[0]
        lesser = quicksort([x for x in lst[1:] if x[1] < pivot[1]])
        greater = quicksort([x for x in lst[1:] if x[1] >= pivot[1]])
        return lesser + [pivot] + greater


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(description="Show sorted list of\
                                     outdated pages for specified language")
    PARSER.add_argument('language', metavar='language', type=str,
                        help='''Set language''')
    PARSER.add_argument('-r', '--reverse', action='store_const', const=True,
                        default=False,
                        help='Return reverse list of outdated pages')

    ARGS = PARSER.parse_args()

    BASE_HTML = 'https://www.debian.org/devel/website/stats/'
    HTML = urlopen(BASE_HTML + ARGS.language).read().decode('utf-8')

    soup = BeautifulSoup(HTML, features='lxml')
    TABLE = ''

    for i in  soup.find_all('table'):
        if i['summary'] == 'Outdated translations':
            TABLE = i.find_all('tr')

    ENTRIES = []

    for tr in TABLE[1:]:
        tds = tr.find_all('td')
        if tds[2].find('a')['title'] == 'The original is newer than this translation':
            result = subprocess.run(tds[1].string.split(), stdout=subprocess.PIPE)
            out_chars = len(result.stdout.decode('utf-8'))
            out_len = len(result.stdout.decode('utf-8').split('\n')) - 1
            ENTRIES.append([tds[0].string, out_len, out_chars])

    if ARGS.reverse:
        for e in reversed(quicksort(ENTRIES)):
            print(e)
    else:
        for e in quicksort(ENTRIES):
            print(e)
