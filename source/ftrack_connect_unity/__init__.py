# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

from ._version import __version__
import ftrack_connect
# Install the ftrack logging handlers
ftrack_connect.config.configure_logging(__name__)