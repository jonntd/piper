#  Copyright (c) 2021 Christian Corsica. All Rights Reserved.

import os
import sys
import maya.cmds as mc
import maya.standalone
maya.standalone.initialize()


# global variables to define your own environment
MODULE_NAME = 'PIPER'
ENVIRONMENT_KEY = 'PIPER_DIR'
ENVIRONMENT = ['MAYA_ENABLE_LEGACY_VIEWPORT=1']

# directory to add to environment should be passed to this script as an argument
if len(sys.argv) < 2:
    raise IndexError('No directory specified. Please pass a directory to add to module to environment.')

# using maya's environment to figure out where to save modules to
environment_directory = sys.argv[1]
modules_directory = os.path.join(os.environ['MAYA_APP_DIR'], mc.about(version=True), 'modules')

if not os.path.exists(modules_directory):
    os.makedirs(modules_directory)

# formatting lines for modules file.
lines = ['+ {0} 1.0 {1}'.format(MODULE_NAME, environment_directory),
         '{0}={1}'.format(ENVIRONMENT_KEY, environment_directory)]

lines += ENVIRONMENT
lines = [line + '\n' for line in lines]
modules_path = os.path.join(modules_directory, MODULE_NAME.lower() + '.mod')
print('Writing environment to: {}'.format(modules_path))

with open(modules_path, 'w') as module_file:
    module_file.writelines(lines)
