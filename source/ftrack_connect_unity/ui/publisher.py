# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import logging
import getpass

from QtExt import QtWidgets, QtCore, QtGui

import ftrack
import ftrack_api
from ftrack_api import event
from ftrack_connect import connector as ftrack_connector
from ftrack_connect.ui.widget import header
from ftrack_connect.ui.theme import applyTheme
from ftrack_connect.ui.widget.context_selector import ContextSelector
from ftrack_connect_unity.ui.export_asset_options_widget import ExportAssetOptionsWidget
from ftrack_connect_unity.ui.export_options_widget import ExportOptionsWidget
from ftrack_connect_unity.connector.unity_connector import Connector, UnityEditor, UnityEngine


class FtrackPublishDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, connector=None):
        if not connector:
            raise ValueError(
                'Please provide a connector object for {0}'.format(
                    self.__class__.__name__
                )
            )
        self.connector = connector
        if not parent:
            self.parent = self.connector.getMainWindow()

        self.currentEntity = Connector.getCurrentEntity()

        super(FtrackPublishDialog, self).__init__(self.parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding
            )
        )
        applyTheme(self, 'integration')

        self.assetType = None
        self.assetName = None
        self.status = None

        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.mainWidget = QtWidgets.QWidget(self)
        self.scrollLayout = QtWidgets.QVBoxLayout(self.mainWidget)
        self.scrollLayout.setSpacing(6)

        self.scrollArea = QtWidgets.QScrollArea(self)
        self.mainLayout.addWidget(self.scrollArea)

        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )
        self.scrollArea.setWidget(self.mainWidget)

        self.headerWidget = header.Header(getpass.getuser(), self)
        self.scrollLayout.addWidget(self.headerWidget)

        if 'FTRACK_TASKID' in os.environ:
            self.browseMode = 'Task'
        else:
            self.browseMode = 'Shot'

        self.browseTasksWidget = ContextSelector(
            currentEntity=self.currentEntity, parent=self
        )

        self.scrollLayout.addWidget(self.browseTasksWidget)

        self.exportAssetOptionsWidget = ExportAssetOptionsWidget(
            self, browseMode=self.browseMode
        )

        self.scrollLayout.addWidget(self.exportAssetOptionsWidget)

        self.exportOptionsWidget = ExportOptionsWidget(
            self, connector=self.connector
        )

        self.scrollLayout.addWidget(self.exportOptionsWidget)

        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.scrollLayout.addItem(spacerItem)

        self.setObjectName('ftrackPublishAsset')
        self.setWindowTitle("ftrackPublishAsset")
        panelComInstance = ftrack_connector.panelcom.PanelComInstance.instance()
        panelComInstance.addSwitchedShotListener(self.reset_context_browser)
        panelComInstance.addSwitchedShotListener(self.resetOptions)

        self.exportAssetOptionsWidget.clickedAssetTypeSignal.connect(
            self.exportOptionsWidget.setStackedWidget
        )

        self.browseTasksWidget.entityChanged.connect(
            self.exportAssetOptionsWidget.updateView
        )

        self.exportOptionsWidget.ui.publishButton.clicked.connect(
            self.renderAssetForPublish
        )

        panelComInstance.publishProgressSignal.connect(
            self.exportOptionsWidget.setProgress
        )

        self.browseTasksWidget.reset()

    def reset_context_browser(self):
        '''Reset task browser to the value stored in the environments'''
        entity_id = os.getenv('FTRACK_TASKID', os.getenv('FTRACK_SHOTID'))
        entity = ftrack.Task(entity_id)
        self.browseTasksWidget.reset(entity)
        self.currentEntity = entity

    def resetOptions(self):
        '''Reset options'''
        self.exportOptionsWidget.resetOptions()
        self.exportAssetOptionsWidget.setAssetType(self.assetType)
        self.exportAssetOptionsWidget.setAssetName(self.assetName)
        self.exportOptionsWidget.setComment('')

        self.exportAssetOptionsWidget.updateTasks(self.currentEntity)
        self.exportAssetOptionsWidget.updateView(self.currentEntity)

    def setAssetType(self, assetType):
        '''Set to the provided *assetType*'''
        self.exportAssetOptionsWidget.setAssetType(assetType)
        self.assetType = assetType

    def setAssetName(self, assetName):
        '''Set to the provided *assetName*'''
        self.exportAssetOptionsWidget.setAssetName(assetName)
        self.assetName = assetName

    def setComment(self, comment):
        '''Set the provided *comment*'''
        self.exportOptionsWidget.setComment(comment)

    def renderAssetForPublish(self):
        '''Publish the asset'''
        assetName = self.exportAssetOptionsWidget.getAssetName()
        if assetName == '':
            self.showWarning('Missing assetName', 'assetName can not be blank')
            return
        assettype = self.exportAssetOptionsWidget.getAssetType()
        if not assettype:
            self.showWarning('Missing assetType', 'assetType can not be blank')
            return

        options = self.exportOptionsWidget.getOptions()
        publishReviewable = options.get('publishReviewable')
        if publishReviewable:
            UnityEditor().ftrack.MovieRecorder.Record()
        else:
            UnityEditor().ftrack.ImageSequenceRecorder.Record()
        self.exportOptionsWidget.setProgress(25)

    def publishAsset(self, published_file_path):
        task = self.exportAssetOptionsWidget.getTask()
        taskId = task.getId()
        shot = self.exportAssetOptionsWidget.getShot()

        assettype = self.exportAssetOptionsWidget.getAssetType()
        assetName = self.exportAssetOptionsWidget.getAssetName()
        status = self.exportAssetOptionsWidget.getStatus()

        comment = self.exportOptionsWidget.getComment()
        options = self.exportOptionsWidget.getOptions()

        if assetName == '':
            self.showWarning('Missing assetName', 'assetName can not be blank')
            return

        prePubObj = ftrack_connector.FTAssetObject(
            options=options, taskId=taskId
        )

        result, message = self.connector.prePublish(prePubObj)

        if not result:
            self.showWarning('Prepublish failed', message)
            return

        self.exportOptionsWidget.setProgress(50)
        asset = shot.createAsset(assetName, assettype)

        assetVersion = asset.createVersion(comment=comment, taskid=taskId)

        # Get version that is in project
        # given the name and type of asset
        # Note: Don't need to do this for image sequences
        if assettype != "img":
            oldAssetVersion = Connector.getAsset(assetName, assettype, taskId)
            if not oldAssetVersion:
                self.showError("Publish failed: Selected asset not in project")
                return

            # copy over used versions and components
            usesVersions = list(oldAssetVersion.usesVersions())
            usesVersions.append(oldAssetVersion)
            assetVersion.addUsesVersions(usesVersions)

            oldComponents = oldAssetVersion.getComponents()
            for oldComp in oldComponents:
                compName = oldComp.getName()
                if compName == 'thumbnail' or compName == 'ftrackreview-mp4':
                    continue
                filePath = oldComp.getFilesystemPath()
                assetVersion.createComponent(
                    name=compName,
                    path=(filePath if filePath else ''))

        pubObj = ftrack_connector.FTAssetObject(
            assetVersionId=assetVersion.getId(),
            options=options
        )
        try:
            logging.info('pubObj' + str(pubObj))
            publishedComponents, message = self.connector.publishAsset(
                published_file_path, pubObj)
        except:
            self.exportOptionsWidget.setProgress(100)
            self.showError('Publish failed. Please check the console.')
            raise

        if publishedComponents:
            session = ftrack_api.Session()
            for componentNumber, ftComponent in enumerate(publishedComponents):
                path = ftComponent.path  # HelpFunctions.safeString(ftComponent.path)
                location = Connector.pickLocation(copyFiles=True)
                try:
                    publishReviewable = options.get('publishReviewable')
                    if publishReviewable:
                        ftrack.Review.makeReviewable(assetVersion, path)
                    else:
                        assetVersion.createComponent(
                            name=ftComponent.componentname, path=path)
                    assetVersion.publish()
                except Exception as error:
                    logging.error(str(error))
        else:
            self.exportOptionsWidget.setProgress(100)

        # Update status of task.
        ftTask = ftrack.Task(id=taskId)
        if (
            ftTask and
            ftTask.get('object_typeid') == '11c137c0-ee7e-4f9c-91c5-8c77cec22b2c'
        ):
            for taskStatus in ftrack.getTaskStatuses():
                if (
                    taskStatus.getName() == status and
                    taskStatus.get('statusid') != ftTask.get('statusid')
                ):
                    try:
                        ftTask.setStatus(taskStatus)
                    except Exception, error:
                        print 'warning: {0}'.format(error)

                    break

        self.headerWidget.setMessage(message, 'info')
        self.exportOptionsWidget.setComment('')
        self.resetOptions()
        self.exportAssetOptionsWidget.emitAssetType(
            self.exportAssetOptionsWidget.ui.ListAssetsComboBox.currentIndex()
        )
        self.exportOptionsWidget.setProgress(100)

    def keyPressEvent(self, e):
        '''Handle Escape key press'''
        if not e.key() == QtCore.Qt.Key_Escape:
            super(FtrackPublishDialog, self).keyPressEvent(e)

    def getShotPath(self, shot):
        '''Return the full path to the shot'''
        shotparents = shot.getParents()
        shotpath = ''

        for parent in reversed(shotparents):
            shotpath += parent.getName() + '.'
        shotpath += shot.getName()
        return shotpath

    def showWarning(self, subject, message):
        '''Helper method for *showWarning*'''
        self.headerWidget.setMessage(message, 'warning')

    def showError(self, message):
        '''Helper method for *showError'''
        self.headerWidget.setMessage(message, 'error')
