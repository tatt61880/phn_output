#!/usr/bin/env python
# vim: fileencoding=utf-8

"""
Copyright (C) 2011 Tatt61880 (tatt61880@gmail.com, @tatt61880)
Last Modified: 2012/04/19 08:51:33.
"""

import sys
import re
import zipfile
import time
import codecs

now = time.localtime(time.time())[:5]
time_stamp = "".join(["_%02d" % x for x in now])

#now = time.localtime(time.time())
#time_stamp = "%4d_%02d%02d_%02d%02d" % (now.tm_year, now.tm_month, now.tm_day, now.tm_hour, now.tm_minute)

version = ''

try:
    f = codecs.open('phn_output.py', 'r', 'utf-8')
    for line in f:
        m = re.search(r"__version__ = ['\"](.*)['\"]", line)
        if m:
            version = m.group(1)
            break
finally:
    f.close()

if version == "":
    sys.stderr.write("### Warning: __version__ info couldn't be found.\n")

# output file
zip_filename = "phn_output_v" + version + time_stamp + ".zip"

zip = zipfile.ZipFile('./'+zip_filename, 'w', zipfile.ZIP_DEFLATED)

files = (
        'MAKEFILE',
        'phn_output.py',
        'phn_output.inx',
        'phn_output.test.py',
        'README.txt',
        'example.phn',
        'example.svg',
        sys.argv[0],
        )
for file in files:
    try:
        zip.write('./'+file)
    except:
        sys.stderr.write("### Warning: %s is not exist in this folder\n" % file)

zip.close()

# vim: expandtab shiftwidth=4 tabstop=8 softtabstop=4 encoding=utf-8 textwidth=99
