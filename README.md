# webwml-utils

Simple (lazy) utilities to work with Debian webwml repository (translation work).

Includes:

## lazycopy

This script copies the file named on the command line to the translation, and
adds the translation-check header to it. It also will create the destination
directory if necessary, and create the Makefile. It also runs an editor on the
copied file, produces diff output to send to localisation team mailing list,
and a pseudo-url to register translation in Debian i18n project. The behaviour
of lazycopy can be modified via command line arguments or by editing its
configuration file, some configuration can be made through environment
variables.

## lazytodo

This script downloads website translation status webpage for the specified
language and produces a sorted (sorts on filesize) list of untranslated
webpages.
