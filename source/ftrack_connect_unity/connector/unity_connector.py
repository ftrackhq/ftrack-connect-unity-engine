# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack
from ftrack_connect.connector import base as maincon
from ftrack_connect.connector import FTAssetHandlerInstance

class Connector(maincon.Connector):
    def __init__(self):
        super(Connector, self).__init__()
