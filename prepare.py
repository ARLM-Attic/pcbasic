#!/usr/bin/env python2
import subprocess
import os
cwd = os.getcwd()
os.chdir('docsrc')
print os.getcwd()
subprocess.call(['./makeusage.sh'])
subprocess.call(['./makedoc.sh'])
os.chdir(cwd)
