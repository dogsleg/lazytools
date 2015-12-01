#!/usr/bin/python3

########################################################################
#
# todo -- process todo for Debian website translators
#
# Copyright (C) 2015  Lev Lamberov <l.lamberov@gmail.com>
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

_VERSION_ = '0.0.4'

import argparse
from urllib.request import urlopen
from html.parser import HTMLParser


class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.content = []
        self.pick_data = False
        self.to_get = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            if ('name', 'untranslated') in attrs and not ARGS.no_general:
                self.to_get = True
            if ('name', 'untranslated-news') in attrs and not ARGS.no_news:
                self.to_get = True
            if ('name', 'untranslated-user') in attrs and not ARGS.no_users:
                self.to_get = True
            if ('name', 'untranslated-l10n') in attrs and not ARGS.no_l10n:
                self.to_get = True
        if self.to_get:
            self.get_link(tag, attrs)

    def handle_endtag(self, tag):
        if tag == 'table':
            self.to_get = False

    def handle_data(self, data):
        if self.pick_data:
            self.content.append((self.current_link, int(data)))
            self.pick_data = False

    def get_link(self, tag, attrs):
        if tag == 'a':
            self.current_link = attrs[1][1][1:]
            self.passed_a = True
        if tag == 'td' and ('align', 'right') in attrs:
            self.pick_data = True

    def get_contents(self):
        return self.content


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
                                     untranslated pages for specified language")
    PARSER.add_argument('language', metavar='language', type=str,
                        help='''Set language''')
    PARSER.add_argument('-ng', '--no-general', action='store_const', const=True,
                        default=False,
                        help='Do not include general pages')
    PARSER.add_argument('-nn', '--no-news', action='store_const', const=True,
                        default=False,
                        help='Do not include news items')
    PARSER.add_argument('-nu', '--no-users', action='store_const', const=True,
                        default=False,
                        help='Do not include consultant/user pages')
    PARSER.add_argument('-nl', '--no-l10n', action='store_const', const=True,
                        default=False,
                        help='Do not include international pages')
    PARSER.add_argument('-r', '--reverse', action='store_const', const=True,
                        default=False,
                        help='Return reverse list of untranslated pages')

    ARGS = PARSER.parse_args()

    BASE_HTML = 'https://www.debian.org/devel/website/stats/'
    HTML = urlopen(BASE_HTML + ARGS.language).read().decode('utf-8')

    HTML_PARSER = MyHTMLParser()
    HTML_PARSER.feed(HTML)

    if ARGS.reverse:
        for entity in reversed(quicksort(HTML_PARSER.get_contents())):
            print(entity)
    else:
        for entity in quicksort(HTML_PARSER.get_contents()):
            print(entity)
