#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os

from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem, QCursor
from PyQt5 import QtCore, QtWidgets

from pyqtgraph import ImageItem

import bruker
import utils

from BrukerGraphicsLayoutWidget import *
from ImageScrollBar import *
from FilesTreeWidget import *
from BrukerThreads import *

import numpy as np
import re
from scipy.misc import toimage

from functools import partial

# dictionaries for sliders
BRIGHTNESS = {
    "conv" : 1000,
    "singleStep" : 1,
    "pageStep" : 50,
    "min" : -600,
    "max" : 600,
    "init" : 0.
}

CONTRAST = {
    "conv" : 100,
    "singleStep" : 1,
    "pageStep" : 40,
    "min" : 20,
    "max" : 900,
    "init" : 100
}

# necessary for path in PyInstaller
def resource_path(relative_path, folder = ""):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(folder)

    return os.path.join(base_path, relative_path)

class dockTreeWidget(QtWidgets.QDockWidget):
    def __init__(self, title, parent = None):
        QtWidgets.QDockWidget.__init__(self, title, parent)
        self.parent = parent

    def closeEvent(self, event):
        self.parent.toggleDock.setText(self.tr("Show Contents"))

    def sizeHint(self):
        return QtCore.QSize(165, 140)

class BrukerSlider(QtWidgets.QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def sizeHint(self):
        return QtCore.QSize(80, 27)

class BrukerMainWindow(QtWidgets.QMainWindow):
    signalCheck = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__() #вызывает родительский объект Example с классом

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)    

        self.applySeries = False
        self.correctNegative = True

        self.hsize, self.vsize = 840, 520

        self.contrast = CONTRAST["init"]/CONTRAST["conv"]
        self.bright = BRIGHTNESS["init"]/BRIGHTNESS["conv"]

        self.initUI()

        self.curExpName = ""
        self.curExpNum = ""

    def initUI(self):

        self.curDir = os.path.normpath(QtCore.QDir.currentPath())
        self.SaveDir = os.path.normpath(QtCore.QDir.homePath() + os.sep+\
                                                "Documents")
        self.resize(self.hsize, self.vsize)
        self.center()

        self.setWindowTitle(self.tr('BrukerGUI'))
        Logo = resource_path("pictures\\LogoBruker.png")
        self.setWindowIcon(QIcon(Logo))

        self.createViewerArea()

        self.createStatusBar()

        self.window.setLayout(self.hbox)
        self.setCentralWidget(self.window)

        self.createActions()
        self.createMenus()

        self.createToolsToolbar()
        self.addToolBarBreak ()
        self.createSliderToolbar()

        QtWidgets.QApplication.restoreOverrideCursor()

        self.show()
        self.raise_()
        self.activateWindow()

    # def eventFilter(self, source, event):
    # """ Mouse tracking in main window """
    #     if event.type() == QtCore.QEvent.MouseMove:
    #         pos = event.pos()
    #         self.x_coord_label.setText("X: {}".format(pos.x()))
    #         self.y_coord_label.setText("Y: {}".format(pos.y()))
    #         self.name_label.setText(str(BrukerGraphicsLayoutWidget))
    #     return QtWidgets.QMainWindow.eventFilter(self, source, event)

    def about(self):
        QtWidgets.QMessageBox.about(self, self.tr("About BrukerGUI"),
                                    self.tr("This is a GUI for imaging bruker data"))
    def addExp(self):

        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, 
                                        self.tr("Add new experiments"),
                                        self.curDir,
                                        QtWidgets.QFileDialog.ShowDirsOnly
                                        | QtWidgets.QFileDialog.DontResolveSymlinks)

        # Try to create multiple directory selection

        # file_dialog = QtWidgets.QFileDialog(self, self.tr("Add new experiments"), self.curDir)
        # file_dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        # file_dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog,True)
        # file_view = file_dialog.findChild(QtWidgets.QListView, "listView")

        # if file_view:
        #     file_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        # f_tree_view = file_dialog.findChild(QtWidgets.QTreeView)
        # if f_tree_view:
        #     f_tree_view.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)

        # paths_list = ""
        # if file_dialog.exec():
        #     paths_list = file_dialog.selectedFiles()


        def tree_on_finished():
            QtWidgets.QApplication.restoreOverrideCursor()
            utils.logger.info("Experiment is added from {}".format(self.curDir))
            self.state_label.setText(self.tr("Ready"))

        if dirname:
            self.state_label.setText(self.tr("Loading..."))
            self.curDir = os.path.normpath(dirname)
            self.treeThread = FilesTreeThread(self, "add", dirname)
            self.treeThread.finished.connect(tree_on_finished)
            self.treeThread.started.connect(self.tree_on_started)
            self.treeThread.start()

    def center(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        try:
            self.winTag.close()
        except:
            pass
    #     reply = QtWidgets.QMessageBox.question(self, 'Message',
    #         "Are you sure to quit?", QtWidgets.QMessageBox.Yes |
    #         QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

    #     if reply == QtWidgets.QMessageBox.Yes:
    #         event.accept()
    #     else:
    #         event.ignore()

    def createActions(self):

        self.openDirAct = QtWidgets.QAction(self.tr("Open Directory"), 
                self, shortcut="Ctrl+O", triggered=self.openDir)

        self.addExpAct = QtWidgets.QAction(self.tr("Add New Experiment"),
                self, enabled=False, triggered=self.addExp)

        self.saveImageAsAct = QtWidgets.QAction(self.tr("Save Image As..."),
                self, shortcut="Ctrl+S", enabled=False, triggered=self.saveImageAs)

        self.saveExpAsTextAct = QtWidgets.QAction(self.tr("Text file"),
                self, shortcut="Ctrl+T", triggered=self.saveExpAsText)

        self.saveExpAsImgAct = QtWidgets.QAction(self.tr("Separete images"),
                self, shortcut="Ctrl+I", triggered=self.saveExpAsImage)

        self.saveExpAsXMLAct = QtWidgets.QAction(self.tr("XML file"),
                self, shortcut="Ctrl+B", triggered=self.saveExpAsXML)

        self.saveAllCheckedAsTextAct = QtWidgets.QAction(self.tr("Separate text files"),
                self, shortcut="Shift+T", triggered=self.saveAllCheckedAsText)

        self.saveAllCheckedAsImgAct = QtWidgets.QAction(self.tr("Separete images"),
                self, shortcut="Shift+I", triggered=self.saveAllCheckedAsImage)

        self.saveAllCheckedAsXMLAct = QtWidgets.QAction(self.tr("Separate XML files"),
                self, shortcut="Shift+B", triggered=self.saveAllCheckedAsXML)

        self.exitAct = QtWidgets.QAction(self.tr("Exit"),
                self, shortcut="Ctrl+Q", triggered=self.close)

        self.toggleDock = QtWidgets.QAction(self.tr("Hide Contents"),
                self, triggered=self.toggleDockWidget)

        self.zoomInAct = QtWidgets.QAction(self.tr("Zoom In (25%)"),
                self, shortcut="Ctrl++", enabled=False, triggered=self.zoomIn)

        self.zoomOutAct = QtWidgets.QAction(self.tr("Zoom Out (25%)"),
                self, shortcut="Ctrl+-", enabled=False, triggered=self.zoomOut)

        self.zoomToFitAct = QtWidgets.QAction(self.tr("Zoom to Fit"),
                self, shortcut="Ctrl+F", enabled=False, triggered=self.zoomToFit)

        self.rotateRightAct = QtWidgets.QAction(self.tr("Rotate Right 90"),
                self, shortcut="Ctrl+R", enabled=False, triggered=self.rotateRightImg)

        self.rotateLeftAct = QtWidgets.QAction(self.tr("Rotate Left 90"),
                self, shortcut="Ctrl+L", enabled=False, triggered=self.rotateLeftImg)

        self.rotateAct = QtWidgets.QAction(self.tr("Rotate 180"),
                self, enabled=False, triggered=self.rotateImg)

        self.tagInfo = QtWidgets.QAction(self.tr("Tag image"),
                self, enabled=False, triggered=self.TagInfo)

        self.ru_RUAct = QtWidgets.QAction("Русский",
                self, checkable=True,
                checked = QtCore.QSettings("locale","language").value('lang', type=str) == "ru_RU",
                triggered=self.ru_RULang)

        self.en_GBAct = QtWidgets.QAction("English",
                self, checkable=True,
                checked = QtCore.QSettings("locale","language").value('lang', type=str) == "en_GB",
                triggered=self.en_GBLang)

        self.aboutAct = QtWidgets.QAction(self.tr("&About"),
                self, triggered=self.about)

        self.aboutQtAct = QtWidgets.QAction(self.tr("About &Qt"),
                self, triggered=QtWidgets.qApp.aboutQt)

    def createTreeContextMenu(self, point):
        index = self.tree.indexAt(point)

        if not index.isValid():
            return

        item = self.tree.itemAt(point)
        if self.tree.isImageItem(item):
            return

        # show context menu 
        self.popMenu = QtWidgets.QMenu(self)

        if self.tree.isNumberItem(item):
            expNum = utils.num_pattern.findall(item.text(0))[0]
            expName = item.parent().text(0)

            deleteExpNumAct = QtWidgets.QAction(self.tr('Delete selected experiment number'), self, 
                                                triggered=partial(self.tree.deleteExpNumItem, item))

            self.popMenu.addAction(deleteExpNumAct)
            if item.checkState(0) == QtCore.Qt.Checked:
                deleteExpNumAct.setDisabled(True)

            # CorrectNegative option
            if "correction" in self.tree.ImageData[expName][expNum]:
                if self.tree.ImageData[expName][expNum]["correction"]: 
                    self.correctNegativeAct = QtWidgets.QAction(self.tr('Cancel correction'), self, 
                                                                triggered=self.setCorrection)
                    self.correctNegative = True
                else:
                    self.correctNegativeAct = QtWidgets.QAction(self.tr('Correct negative values'), self, 
                                                                triggered=self.setCorrection)
                    self.correctNegative = False

                self.popMenu.addAction(self.correctNegativeAct)

                self.popMenu.exec_(QCursor.pos())
                self.tree.ImageData[expName][expNum]["correction"] = self.correctNegative
                self.tree.removeItemsColorFront(item)
                self.scroll.valueChanged.emit(self.scroll.value())
            else:
                self.popMenu.exec_(QCursor.pos())

        elif self.tree.isNameItem(item):
            deleteExpNameAct = QtWidgets.QAction(self.tr('Delete selected experiment name'), self, 
                                                            triggered=partial(self.tree.deleteExpNameItem, item))

            self.popMenu.addAction(deleteExpNameAct)

            if item.checkState(0) in [QtCore.Qt.Checked, QtCore.Qt.PartiallyChecked]:
                deleteExpNameAct.setDisabled(True)

            self.popMenu.exec_(QCursor.pos())

    def createImageItem(self, name, first):

        self.tree.imageItem = QtWidgets.QTreeWidgetItem(self.tree.numberItem)
        self.tree.imageItem.setText(0, name)

        expName = self.tree.getExpNameItem(self.tree.numberItem).text(0)
        expNum = utils.num_pattern.findall(self.tree.numberItem.text(0))[0]
        self.tree.setNegativeItemColor(self.tree.imageItem)
        
        if first:
            self.tree.imageItem.setBackground(0, ITEMCOLORS["imageCurrent"])
            self.tree.setCurrentImageItem(self.tree.imageItem)
            self.tree.collapseItem(self.tree.nameItem)
            self.tree.collapseItem(self.tree.numberItem)

    def createMenus(self):
        self.fileMenu = QtWidgets.QMenu(self.tr("&File"), self)
        self.fileMenu.addAction(self.openDirAct)
        self.fileMenu.addAction(self.addExpAct)
        self.fileMenu.addAction(self.saveImageAsAct)

        self.saveExpAs = QtWidgets.QMenu(self.tr("Save Current Experiment Number As..."), self.fileMenu)
        self.saveExpAs.addAction(self.saveExpAsTextAct)
        self.saveExpAs.addAction(self.saveExpAsImgAct)
        self.saveExpAs.addAction(self.saveExpAsXMLAct)
        self.fileMenu.addMenu(self.saveExpAs)
        self.saveExpAs.setDisabled(True)

        self.saveAllCheckedAs = QtWidgets.QMenu(self.tr("Save All Checked Experiments As..."), self.fileMenu)
        self.saveAllCheckedAs.addAction(self.saveAllCheckedAsTextAct)
        self.saveAllCheckedAs.addAction(self.saveAllCheckedAsImgAct)
        self.saveAllCheckedAs.addAction(self.saveAllCheckedAsXMLAct)
        self.fileMenu.addMenu(self.saveAllCheckedAs)
        self.saveAllCheckedAs.setDisabled(True)

        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.viewMenu = QtWidgets.QMenu(self.tr("&View"), self)
        self.viewMenu.addAction(self.toggleDock)
        self.viewMenu.addSeparator()

        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.rotateRightAct)
        self.viewMenu.addAction(self.rotateLeftAct)        
        self.viewMenu.addAction(self.rotateAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.zoomToFitAct)

        self.toolsMenu = QtWidgets.QMenu(self.tr("&Tools"), self)
        self.toolsMenu.addAction(self.tagInfo)

        self.langMenu = QtWidgets.QMenu(self.tr("Language"), self.toolsMenu)
        self.langMenu.addAction(self.ru_RUAct)
        self.langMenu.addAction(self.en_GBAct)
        self.toolsMenu.addMenu(self.langMenu)


        self.helpMenu = QtWidgets.QMenu(self.tr("&Help"), self)
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addMenu(self.viewMenu)
        self.menuBar().addMenu(self.toolsMenu)
        self.menuBar().addMenu(self.helpMenu)

    def createNameItem(self, name, first):

        self.tree.nameItem = QtWidgets.QTreeWidgetItem(self.tree)
        self.tree.nameItem.setFlags(self.tree.nameItem.flags()
                             | QtCore.Qt.ItemIsTristate 
                             | QtCore.Qt.ItemIsUserCheckable)
        
        self.tree.nameItem.setCheckState(0, QtCore.Qt.Unchecked)
        self.tree.nameItem.setText(0, name)
        if first:
            self.tree.nameItem.setBackground(0, ITEMCOLORS["nameCurrent"])

    def createNumberItem(self, name, first):

        self.tree.numberItem = QtWidgets.QTreeWidgetItem(self.tree.nameItem)
        self.tree.numberItem.setFlags(self.tree.numberItem.flags() 
                            | QtCore.Qt.ItemIsUserCheckable)
        
        self.tree.numberItem.setCheckState(0, QtCore.Qt.Unchecked)
        self.tree.numberItem.setText(0, name)

        expName = self.tree.nameItem.text(0)
        expNum = utils.num_pattern.findall(name)[0]
        self.tree.setNegativeItemColor(self.tree.numberItem)

        if first:
            self.tree.numberItem.setCheckState(0, QtCore.Qt.Checked)
            self.tree.numberItem.setBackground(0, ITEMCOLORS["numberCurrent"])

    def createSliderToolbar(self):

        tb = QtWidgets.QToolBar(self.tr("Image Toolbar"))
        self.addToolBar(tb)

        applyButton = QtWidgets.QRadioButton(self.tr("Apply to the series"), self)
        applyButton.clicked.connect(self.setApplySeries)

        contrLabel = QtWidgets.QLabel(self.tr("Contrast: "), self)

        self.contrSlider = BrukerSlider(QtCore.Qt.Horizontal, self)
        self.contrSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)        
        self.contrSlider.setMinimum(CONTRAST["min"])
        self.contrSlider.setMaximum(CONTRAST["max"])
        self.contrSlider.setSingleStep(CONTRAST["singleStep"])
        self.contrSlider.setTickInterval(CONTRAST["pageStep"])
        self.contrSlider.setPageStep(CONTRAST["pageStep"])
        self.contrSlider.setValue(CONTRAST["init"])

        self.contrValueSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.contrValueSpinBox.setRange(CONTRAST["min"]/CONTRAST["conv"],
                                        CONTRAST["max"]/CONTRAST["conv"])
        self.contrValueSpinBox.setSingleStep(CONTRAST["singleStep"]/CONTRAST["conv"])
        self.contrValueSpinBox.setValue(CONTRAST["init"]/CONTRAST["conv"])

        self.contrValueSpinBox.valueChanged.connect(self.setContrast)
        self.contrSlider.valueChanged.connect(self.setContrast)

        spacer1 = QtWidgets.QLabel("    ")
        spacer2 = QtWidgets.QLabel("    ")

        brightLabel = QtWidgets.QLabel(self.tr("Brightness: "), self)

        self.brightSlider = BrukerSlider(QtCore.Qt.Horizontal, self)
        self.brightSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.brightSlider.setMinimum(BRIGHTNESS["min"])
        self.brightSlider.setMaximum(BRIGHTNESS["max"])
        self.brightSlider.setSingleStep(BRIGHTNESS["singleStep"])
        self.brightSlider.setTickInterval(BRIGHTNESS["pageStep"])
        self.brightSlider.setPageStep(BRIGHTNESS["pageStep"])
        self.brightSlider.setValue(BRIGHTNESS["init"])

        self.brightValueSpinBox = QtWidgets.QDoubleSpinBox(self)
        self.brightValueSpinBox.setRange(BRIGHTNESS["min"]/BRIGHTNESS["conv"],
                                         BRIGHTNESS["max"]/BRIGHTNESS["conv"])
        self.brightValueSpinBox.setSingleStep(BRIGHTNESS["singleStep"]/BRIGHTNESS["conv"])
        self.brightValueSpinBox.setValue(BRIGHTNESS["init"]/BRIGHTNESS["conv"])
        self.brightValueSpinBox.setDecimals(3)

        self.brightValueSpinBox.valueChanged.connect(self.setBrightness)
        self.brightSlider.valueChanged.connect(self.setBrightness)

        resetButton = QtWidgets.QPushButton(self.tr("Reset"))
        resetButton.clicked.connect(self.resetCnB)

        tb.addWidget(applyButton)
        tb.addSeparator()
        tb.addWidget(brightLabel)
        tb.addWidget(self.brightSlider)
        tb.addWidget(spacer2)
        tb.addWidget(self.brightValueSpinBox)

        tb.addSeparator()

        tb.addWidget(contrLabel)
        tb.addWidget(self.contrSlider)
        tb.addWidget(spacer1)
        tb.addWidget(self.contrValueSpinBox)

        tb.addSeparator()
        tb.addWidget(resetButton)

    def createStatusBar(self):

        self.status = QtWidgets.QStatusBar()

        self.name_label = QtWidgets.QLabel(self.tr("Experiment:"))
        self.name_label.setMinimumSize(QtCore.QSize(200,15))
 
        self.num_label = QtWidgets.QLabel(self.tr("Number:"))
        self.num_label.setMinimumSize(QtCore.QSize(70,15))

        self.img_label = QtWidgets.QLabel(self.tr("Image:"))
        self.img_label.setMinimumSize(QtCore.QSize(160,15))

        self.state_label = QtWidgets.QLabel(self.tr("Ready"))
        self.state_label.setMinimumSize(QtCore.QSize(160,15))
        # self.x_coord_label = QtWidgets.QLabel("X:")
        # self.x_coord_label.setMinimumSize(QtCore.QSize(60,13))

        # self.y_coord_label = QtWidgets.QLabel("Y:")
        # self.y_coord_label.setMinimumSize(QtCore.QSize(60,13))

        self.status.addPermanentWidget(self.name_label)
        self.status.addPermanentWidget(self.num_label)
        self.status.addPermanentWidget(self.img_label)
        self.status.addWidget(self.state_label)
        self.status.setStyleSheet("QStatusBar{border-top: 1px outset grey;}")
        # self.status.addPermanentWidget(self.x_coord_label)
        # self.status.addPermanentWidget(self.y_coord_label)
        self.setStatusBar(self.status)

    def createToolsToolbar(self):
        tools_tb = QtWidgets.QToolBar(self.tr("Tools Toolbar"))
        self.addToolBar(tools_tb) 

        self.openDirAct.setIcon(QIcon(resource_path("pictures\\Open_Folder.ico")))
        self.addExpAct.setIcon(QIcon(resource_path("pictures\\Add_List.ico")))
        self.saveImageAsAct.setIcon(QIcon(resource_path("pictures\\Save_Image_As.ico")))

        self.saveExpAsbutton = QtWidgets.QToolButton(self)
        self.saveExpAsbutton.setMenu(self.saveExpAs)
        self.saveExpAsbutton.setIcon(QIcon(resource_path("pictures\\Save_Exp_As.ico")))
        self.saveExpAsbutton.setToolTip(self.tr("Save Current Experiment Number As..."))
        self.saveExpAsbutton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.saveExpAsbutton.setDisabled(True)

        self.saveAllCheckedAsbutton = QtWidgets.QToolButton(self)
        self.saveAllCheckedAsbutton.setMenu(self.saveAllCheckedAs)
        self.saveAllCheckedAsbutton.setIcon(QIcon(resource_path("pictures\\Save_All_As.ico")))
        self.saveAllCheckedAsbutton.setToolTip(self.tr("Save All Checked Experiments As..."))
        self.saveAllCheckedAsbutton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.saveAllCheckedAsbutton.setDisabled(True)

        self.zoomInAct.setIcon(QIcon(resource_path("pictures\\Zoom_In.ico")))
        self.zoomOutAct.setIcon(QIcon(resource_path("pictures\\Zoom_Out.ico")))
        #self.zoomBox = QtWidgets.QComboBox(self)
        #self.zoomBox.addItems(["25%", "50%", "100%", "125%", "150%", "200%"])

        self.rotateLeftAct.setIcon(QIcon(resource_path("pictures\\rotate_left.ico")))
        self.rotateRightAct.setIcon(QIcon(resource_path("pictures\\rotate_right.ico")))
        self.zoomToFitAct.setIcon(QIcon(resource_path("pictures\\Zoom_Fit.ico")))

        self.tagInfo.setIcon(QIcon(resource_path("pictures\\Tag_Info.ico")))

        tools_tb.addAction(self.openDirAct)
        tools_tb.addAction(self.addExpAct)
        tools_tb.addSeparator()
        tools_tb.addAction(self.saveImageAsAct)
        tools_tb.addWidget(self.saveExpAsbutton)
        tools_tb.addWidget(self.saveAllCheckedAsbutton)
        tools_tb.addSeparator()
        tools_tb.addAction(self.zoomInAct)
        tools_tb.addAction(self.zoomOutAct)
        #tools_tb.addWidget(self.zoomBox)
        tools_tb.addSeparator()
        tools_tb.addAction(self.rotateLeftAct)
        tools_tb.addAction(self.rotateRightAct)
        tools_tb.addAction(self.zoomToFitAct)
        tools_tb.addSeparator()
        tools_tb.addAction(self.tagInfo)

    def createViewerArea(self):
        self.window = QtWidgets.QWidget()

        self.scroll = ImageScrollBar()
        self.scroll.setMaximum(0)

        self.scroll.valueChanged.connect(self.sliderimage)

        self.dock = dockTreeWidget(self.tr('Contents'),self)
        self.addDockWidget(QtCore.Qt.DockWidgetArea(1), self.dock)

        self.tree = FilesTreeWidget(self, self.scroll)
        self.dock.setWidget(self.tree)

        self.win = BrukerGraphicsLayoutWidget(self.scroll, self.tree)
        self.win.setGeometry(0,0,100,100)
        # #self.view.setMouseMode(ViewBox.RectMode)
        self.img = ImageItem()
        self.win.view.addItem(self.img)

        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addWidget(self.win)
        self.hbox.addWidget(self.scroll)
    
    def en_GBLang(self):
        if self.en_GBAct.isChecked():
            if not self.LangConfirmWarninig("en_GB"):
                self.en_GBAct.setChecked(False)
        else:
            self.en_GBAct.setChecked(True)

    def LangConfirmWarninig(self, lang):
        import brkRebootConst
        msgbox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning,
                                       self.tr("Language Choice Confirmation"),
                                       self.tr("The application must be restarted to display\n"
                                       "the new language! Click \"Yes\" to restart or \"No\"\n"
                                       "to cancel your language selection choice."),
                                       QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                       self)
        msgbox.setDefaultButton(QtWidgets.QMessageBox.No)

        buttonBox = msgbox.findChild(QtWidgets.QDialogButtonBox)
        yes_btn = buttonBox.button(QtWidgets.QDialogButtonBox.Yes)
        no_btn = buttonBox.button(QtWidgets.QDialogButtonBox.No)
        yes_btn.setText(self.tr('Yes'))
        no_btn.setText(self.tr('No'))
        msgbox.exec_()
        if msgbox.clickedButton() == yes_btn:
            setting = QtCore.QSettings("locale","language")
            setting.setValue("lang", lang)
            QtWidgets.qApp.exit(brkRebootConst.EXIT_CODE_REBOOT)
            return True
        elif msgbox.clickedButton() == no_btn:
            return False

    def openDir(self):

        # attempt to get own localization

        # file_diag = QtWidgets.QFileDialog(self)
        # file_diag.setWindowTitle(self.tr('Open Directory'))
        # #file_diag.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)
        # file_diag.setOptions(QtWidgets.QFileDialog.ShowDirsOnly
        #                     | QtWidgets.QFileDialog.DontResolveSymlinks)
        # file_diag.setFileMode(QtWidgets.QFileDialog.Directory)
        # file_diag.setDirectory(self.curDir)
        # file_diag.setLabelText(QtWidgets.QFileDialog.Accept, self.tr("Choose folder"))
        # file_diag.setLabelText(QtWidgets.QFileDialog.Reject, self.tr("Cancel"))
        # file_diag.setLabelText(QtWidgets.QFileDialog.FileName, self.tr("Folder:"))
        # file_diag.exec_()
        # dirname = file_diag.selectedFiles()[0]

        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, 
                                self.tr('Open Directory'),
                                self.curDir,
                                QtWidgets.QFileDialog.ShowDirsOnly
                                | QtWidgets.QFileDialog.DontResolveSymlinks)

        if dirname:
            self.tree = FilesTreeWidget(self, self.scroll)

            self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.tree.customContextMenuRequested.connect(self.createTreeContextMenu)

            self.win.setTree(self.tree)
            self.scroll.setTree(self.tree)
            self.dock.setWidget(self.tree)

            self.state_label.setText(self.tr("Loading..."))
            self.curDir = os.path.normpath(dirname)

            self.treeThread = FilesTreeThread(self, "create")
            self.treeThread.finished.connect(self.tree_on_finished)
            self.treeThread.started.connect(self.tree_on_started)

            self.tree.nameItemcreate.connect(self.createNameItem)
            self.tree.numItemcreate.connect(self.createNumberItem)
            self.tree.imgItemcreate.connect(self.createImageItem)
            
            self.treeThread.start()

    def resetCnB(self):
        self.contrast = CONTRAST["init"]/CONTRAST["conv"]
        self.contrValueSpinBox.setValue(self.contrast)
        self.bright = BRIGHTNESS["init"]/BRIGHTNESS["conv"]
        self.brightValueSpinBox.setValue(self.bright)

        if self.tree.getCurrentImageItem():
            data = self.tree.ImageData[self.curExpName][self.curExpNum][str(self.scroll.value())]
            data[0] = self.bright
            data[1] = self.contrast 
            self.scroll.valueChanged.emit(self.scroll.value())

    def rotateImg(self):
        self.win.setRotation(2)

    def rotateLeftImg(self):
        self.win.setRotation(1)

    def rotateRightImg(self):
        self.win.setRotation(-1)

    def ru_RULang(self):
        if self.ru_RUAct.isChecked():          
            self.LangConfirmWarninig("ru_RU")
            self.ru_RUAct.setChecked(False)
        else:
            self.ru_RUAct.setChecked(True)

    def saveAllCheckedAsImage(self):
        """
    Save all checked experiments to a separate folders with a number of image files
        """        
        self.saveExpWindow(self.tr("Save as Separete Images"))

        form = "png"
        self.saveWin.fileline.setVisible(False)
        self.saveWin.filelabel.setVisible(False)

        self.saveWin.tip.setText(
            self.tr("All files will be saved as in ExpName directory with " 
                    "ExpNumber folders and\nImage_i.png files or any image "
                    "type in combo box"))
        self.saveWin.tip.setWordWrap(True)

        self.saveWin.combo.addItems(["PNG", "JPG", "BMP", "TIFF"])

        @QtCore.pyqtSlot()
        def onActivated(text):
            nonlocal form
            form = text.lower()

        @QtCore.pyqtSlot()
        def save():
            self.SaveAs("Image", form = form)

        self.saveWin.saveButton.clicked.connect(save)
        self.saveWin.combo.activated[str].connect(onActivated)

    def saveAllCheckedAsText(self):
        """
    Save checked loaded experiments to a separate text files
        """
        self.saveExpWindow(self.tr("Save as separate text files"))
        self.saveWin.fileline.setVisible(False)
        self.saveWin.filelabel.setVisible(False)

        self.saveWin.tip.setText(
                    self.tr("All files will be saved as ExpName_ExpNumber.txt "
                            "or any text type in combo box"))
        self.saveWin.tip.setWordWrap(True)

        self.saveWin.combo.setVisible(True)
        self.saveWin.combo.addItems(["TXT", "DAT"])
        form = 'txt'

        @QtCore.pyqtSlot()
        def onActivated(text):
            nonlocal form
            form = text.lower()

        @QtCore.pyqtSlot()
        def save():
            self.SaveAs("Text", form = form)

        self.saveWin.combo.activated[str].connect(onActivated)
        self.saveWin.saveButton.clicked.connect(save)

    def saveAllCheckedAsXML(self):
        """
    Save checked loaded experiments to a separate XML files
        """
        self.saveExpWindow(self.tr("Save as XML File"))
        self.saveWin.fileline.setVisible(False)
        self.saveWin.filelabel.setVisible(False)
        self.saveWin.combo.setVisible(False)

        @QtCore.pyqtSlot()
        def save():
            self.SaveAs("XML")
        self.saveWin.saveButton.clicked.connect(save)

    def SaveAs(self, savetype, trigger = "all", form = ""):

        self.state_label.setText(self.tr("Saving..."))
        self.SaveDir = os.path.normpath(self.saveWin.dirline.text())
        fname = ""

        if trigger == "single":
            fname = self.saveWin.fileline.text()
            if QtCore.QDir(self.SaveDir).exists(fname):
                msg_button = QtWidgets.QMessageBox.warning(
                        self, 
                        self.tr("Confirm Save As"), 
                        self.tr("{} already exists.\nDo you want to replace it?").format(fname),
                        buttons = QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                        defaultButton = QtWidgets.QMessageBox.No)

                if msg_button == QtWidgets.QMessageBox.No:
                    return

        @QtCore.pyqtSlot()
        def save_finished():
            if not self.saveThread.cancelThread:
                utils.move_dirs(self.saveThread.tmp_folder.name, self.SaveDir)
                utils.logger.info("Experiments are saved in the {}".format(self.SaveDir))
            self.saveThread.tmp_folder.cleanup()            

            QtWidgets.QApplication.restoreOverrideCursor()
            self.state_label.setText(self.tr("Ready"))
            self.saveWin.progressLabel.setText("")
            self.saveWin.close()

        @QtCore.pyqtSlot()
        def save_canceled():
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.saveThread.cancelThread = True

        self.cancelButton.clicked.disconnect()
        self.cancelButton.clicked.connect(save_canceled)

        self.saveThread = SaveThread(self,
                                     self.SaveDir,
                                     savetype,
                                     form,
                                     filename = fname)

        self.saveThread.trigger = trigger
        self.saveThread.finished.connect(save_finished)
        self.saveThread.progressText[str].connect(self.saveWin.progressLabel.setText)
        self.saveThread.progress[int].connect(self.saveWin.progressBar.setValue)
        self.saveThread.start()
        self.saveWin.saveButton.setDisabled(True)

    def saveExpAsImage(self):
        """
    Save experiment to a number of image files
        """
        self.saveExpWindow(self.tr("Save as Separete Images"))

        self.saveWin.fileline.setText("{0}_{1}".format(self.curExpName,self.curExpNum))
        form = "png"
        self.saveWin.tip.setText(
            self.tr("The filename will be used for all image files in the series "
                    "with adding numeration\n(i.e. {0}_{1}.{2})").format(
                                                                self.curExpName,
                                                                self.curExpNum,
                                                                form))

        self.saveWin.combo.addItems(["PNG", "JPG", "BMP", "TIFF"])

        @QtCore.pyqtSlot()
        def onActivated(text):
            nonlocal form
            form = text.lower()
            self.saveWin.tip.setText(
                self.tr("The filename will be used for all image files in the series "
                        "with adding numeration\n(i.e. {0}_{1}.{2})").format(
                                                                self.curExpName,
                                                                self.curExpNum, 
                                                                form))

        @QtCore.pyqtSlot()
        def save():
            self.SaveAs("Image", "single", form)

        self.saveWin.saveButton.clicked.connect(save)
        self.saveWin.combo.activated[str].connect(onActivated)

    def saveExpAsText(self):
        """
    Save experiment to text file
        """
        self.saveExpWindow(self.tr("Save as Text File"))
        self.saveWin.combo.setVisible(False)

        self.saveWin.fileline.setText("{0}_{1}.txt".format(self.curExpName,
                                                           self.curExpNum))

        @QtCore.pyqtSlot()
        def save():
            self.SaveAs("Text", "single")

        self.saveWin.saveButton.clicked.connect(save)

    def saveExpAsXML(self):
        """
    Save experiment to XML file
        """
        self.saveExpWindow(self.tr("Save as XML File"))
        self.saveWin.combo.setVisible(False)

        self.saveWin.fileline.setText("{0}_{1}.xml".format(self.curExpName,
                                                           self.curExpNum))

        @QtCore.pyqtSlot()
        def save():
            self.SaveAs("XML", "single")

        self.saveWin.saveButton.clicked.connect(save)

    def saveExpWindow(self, winName):
        """ 
    Create a Window for saving experiments
    
    The window include:
        -A line(dirline) for input a directory name and "Browse.." button 
           to simplify a selection of the desired directory
        -A line(fileline) for input a file name and combobox for selection of
            file extension
        - Progressbar and progress tip which is showing a current fragment
            of saving process

        """
        self.saveWin = \
                QtWidgets.QWidget(self, QtCore.Qt.Dialog | 
                              QtCore.Qt.MSWindowsFixedSizeDialogHint | 
                              QtCore.Qt.WindowTitleHint | 
                              QtCore.Qt.WindowSystemMenuHint)
        self.saveWin.setWindowTitle(winName)
        self.saveWin.resize(500, 250)
        self.saveWin.setWindowModality(QtCore.Qt.WindowModal)
        self.saveWin.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.saveWin.dirbrowser = self.SaveDir

        @QtCore.pyqtSlot()
        def browse():
            self.saveWin.dirbrowser = \
                QtWidgets.QFileDialog.getExistingDirectory(
                                    self,
                                    self.tr('Choose Directory'),
                                    self.SaveDir,
                                    QtWidgets.QFileDialog.ShowDirsOnly
                                    | QtWidgets.QFileDialog.DontResolveSymlinks)

            self.saveWin.dirline.setText(self.saveWin.dirbrowser)
            self.SaveDir = self.saveWin.dirbrowser

        @QtCore.pyqtSlot()
        def closeWin():
                self.saveWin.close()

        self.cancelButton = QtWidgets.QPushButton(self.tr("&Cancel"))
        self.cancelButton.clicked.connect(closeWin)

        self.saveWin.saveButton = QtWidgets.QPushButton(self.tr("&Save"))
        self.saveWin.saveButton.setDefault(True)
        self.saveWin.saveButton.setAutoDefault(True)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.saveWin.saveButton)
        hbox.addWidget(self.cancelButton)

        dirlabel = QtWidgets.QLabel(self.tr("Directory:"))
        self.saveWin.dirline = QtWidgets.QLineEdit()
        self.saveWin.dirline.setText(self.SaveDir)

        browseButton = QtWidgets.QPushButton(self.tr("Browse.."))
        browseButton.clicked.connect(browse)

        dirbox = QtWidgets.QHBoxLayout()
        dirbox.addWidget(dirlabel)
        dirbox.addWidget(self.saveWin.dirline)
        dirbox.addWidget(browseButton)

        self.saveWin.filelabel = QtWidgets.QLabel(self.tr("File name:"))
        self.saveWin.fileline = QtWidgets.QLineEdit(self.saveWin)
        filebox = QtWidgets.QHBoxLayout()
        self.saveWin.combo = QtWidgets.QComboBox(self.saveWin)
        filebox.addWidget(self.saveWin.filelabel)
        filebox.addWidget(self.saveWin.fileline)
        filebox.addStretch(1)
        filebox.addWidget(self.saveWin.combo)
        self.saveWin.tip = QtWidgets.QLabel()

        self.saveWin.progressBar = QtWidgets.QProgressBar(self.saveWin)
        self.saveWin.progressLabel = QtWidgets.QLabel("")
        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(dirbox)
        vbox.addLayout(filebox)
        vbox.addWidget(self.saveWin.tip)
        vbox.addStretch(1)
        vbox.addWidget(self.saveWin.progressBar)
        vbox.addWidget(self.saveWin.progressLabel)
        vbox.addLayout(hbox)

        self.saveWin.setLayout(vbox)
        self.saveWin.show()         

    def saveImageAs(self):

        idx = self.scroll.value()

        file_formats = ["Text files (*.txt)", "XML(*.xml *.xsd *.xslt *.tld *.dtml *.opml *.svg)",
                         "Images (*.png *.jpg *.tif *.bmp)", "AllFiles(*)"]

        default_fname = self.SaveDir + os.sep + '{0}_{1}_{2}.txt'.format(self.curExpName,
                                                                         self.curExpNum,
                                                                         idx+1)

        fname = QtWidgets.QFileDialog.getSaveFileName(self, 
                                            self.tr('Save File'),
                                            default_fname,
                                            "{0};;{1};;{2};;{3}".format(file_formats[0],
                                                                        file_formats[1],
                                                                        file_formats[2],
                                                                        file_formats[3]))
        if fname[0]:
            self.state_label.setText(self.tr("Saving..."))
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

            # Get only the directory name
            self.SaveDir = os.path.normpath(os.path.dirname(fname[0]))

            try:
                # Derive the file extension from the file name.
                name, ext = os.path.splitext(fname[0])
            except:
                if fname[1] != "AllFiles(*)":

                    # Add the first extension from the file_formats according to the chosen format (fname[1])
                    ext = re.search(r"\.\w+", fname[1]).group()
                else:
                    ext = ".txt"

            img_data = self.tree.ImageData[self.curExpName][self.curExpNum]["data"]
            # Text format
            if ext in re.findall(r"\.\w+", file_formats[0]):
                bruker.SingleWriteToTextFile(fname = fname[0], 
                                             data = img_data, 
                                             index = idx, 
                                             create = True)
            # XML format
            elif ext in re.findall(r"\.\w+", file_formats[1]):
                bruker.SingleWriteToXMLFile(fname = fname[0], 
                                            data = img_data, 
                                            index = idx, 
                                            create = True)

            # Image format
            elif ext in re.findall(r"\.\w+", file_formats[2]):
                # Save image
                toimage(img_data.IntenseData[idx,:,:], 
                        cmin=img_data.min_val, cmax=img_data.max_val).save(fname[0])

            utils.logger.info("Image is saved in the {}".format(fname[0]))

            self.state_label.setText(self.tr("Ready"))
            QtWidgets.QApplication.restoreOverrideCursor()

    def set_Tag_and_Val(self, TagName, xVal, yVal="#", zVal="#"):
        """
    Set values for TagName in the table(TagInfo)
        """
        Nrow = 1 + bool(yVal!="#") + bool(zVal!="#")
        Ncolumn = 2
        Val = [xVal, yVal, zVal]

        tag = QStandardItem(TagName)
        tag.setEditable(False)
        self.tagModel.appendRow(tag)

        if Nrow == 1:
            tag.setSelectable(False)
            Val_itm = QStandardItem(xVal)
            Val_itm.setEditable(False)
            self.tagModel.setItem(tag.row(),1,Val_itm)
        else:
            idx_itm = self.tagModel.indexFromItem(tag)
            self.tagModel.insertRows(0, Nrow, parent = idx_itm)
            self.tagModel.insertColumns(0, 2, parent = idx_itm)

            for row in range(Nrow):
                Tag_idx = self.tagModel.index(row, 0, parent = idx_itm)
                if TagName != "SliceOrientation":
                    self.tagModel.setData(Tag_idx,
                                          "{}Value".format(chr(ord('x')+row)))
                else:
                    self.tagModel.setData(Tag_idx,"Vector{}".format(row+1))
                Tag_itm = self.tagModel.itemFromIndex(Tag_idx)
                Tag_itm.setSelectable(False)
                Tag_itm.setEditable(False)

                Val_idx = self.tagModel.index(row, 1, parent = idx_itm)
                self.tagModel.setData(Val_idx, Val[row])
                Val_itm = self.tagModel.itemFromIndex(Val_idx)
                Val_itm.setEditable(False)

    def setApplySeries(self, bool):
        self.applySeries = bool

    def setBrightness(self, value):
        # if func is called by slider moving
        if (type(value) == int):
            self.bright = value/BRIGHTNESS["conv"]
            self.brightValueSpinBox.setValue(self.bright)
        # if func is called by spinbox value
        else:
            self.bright = value
            self.brightSlider.setValue(self.bright*BRIGHTNESS["conv"])            

        if self.tree.getCurrentImageItem():
            data = self.tree.ImageData[self.curExpName][self.curExpNum][str(self.scroll.value())]
            data[0] = self.bright
            self.scroll.valueChanged.emit(self.scroll.value())

    def setContrast(self, value):
        # if func is called by slider moving
        if (type(value) == int):
            self.contrast = value/CONTRAST["conv"]
            self.contrValueSpinBox.setValue(self.contrast)            
        # if func is called by spinbox value
        else:
            self.contrast = value
            self.contrSlider.setValue(self.contrast*CONTRAST["conv"])

        if self.tree.getCurrentImageItem():
            data = self.tree.ImageData[self.curExpName][self.curExpNum][str(self.scroll.value())]
            data[1] = self.contrast
            self.scroll.valueChanged.emit(self.scroll.value())

    def setCorrection(self):        
        self.correctNegative = not self.correctNegative

    def setEnabledActions(self, state):
        self.zoomToFitAct.setEnabled(state)
        self.zoomInAct.setEnabled(state)
        self.zoomOutAct.setEnabled(state)

        self.rotateAct.setEnabled(state)
        self.rotateRightAct.setEnabled(state)
        self.rotateLeftAct.setEnabled(state)

        self.saveImageAsAct.setEnabled(state)
        self.saveExpAs.setEnabled(state)
        self.tagInfo.setEnabled(state)

        self.saveExpAsbutton.setEnabled(state)

    def sliderimage(self, value):

        if self.tree.getCurrentImageItem():
            self.curExpName = self.tree.getCurrentNameItem().text(0)
            self.curExpNum = utils.num_pattern.findall(self.tree.getCurrentNumberItem().text(0))[0]

            img_data = self.tree.ImageData[self.curExpName][self.curExpNum]

            if self.applySeries and self.tree.sameNumberItem():
                bright = self.bright
                contrast = self.contrast
                if img_data[str(value)] != [bright, contrast]:
                    for num in list(img_data.keys()):
                        if num not in ("data", "correction"):
                            img_data[num] = [bright, contrast]
            else:
                bright = img_data[str(value)][0]
                contrast = img_data[str(value)][1]
                self.contrValueSpinBox.setValue(contrast)
                self.brightValueSpinBox.setValue(bright)

            self.img.setLevels([0, 1])

            if img_data["data"].min_val < 0 and img_data["correction"]:
                correctdata = bruker.CorrectBrukerData(img_data["data"]).astype(float)
                min_val = np.amin(correctdata)
                max_val = np.amax(correctdata)
                rawdata = (np.rot90(correctdata[value,:,:], self.win.getRotation()) - min_val) / (max_val - min_val)
            else:
                rawdata = (np.rot90(img_data["data"].IntenseData[value,:,:], self.win.getRotation()).astype(float) - img_data["data"].min_val)\
                        / (img_data["data"].max_val - img_data["data"].min_val.astype(float))

            data = rawdata * contrast + bright
            self.img.setImage(data, autoLevels=False)

            self.tree.setCurrentImageItem(self.tree.getCurrentNumberItem().child(value))
            self.tree.changeItemsColor()

            self.name_label.setText(self.tr("Experiment: {}").format(self.curExpName))
            self.num_label.setText(self.tr("Number: {}").format(self.curExpNum))
            self.img_label.setText(self.tr("Image: {0:>3}/{1:>3}").format(value+1,
                                                                          self.scroll.maximum()+1))
            
            self.setEnabledActions(True)
            self.addExpAct.setEnabled(True)
        else:
            self.scroll.setMaximum(0)
            self.img.clear()

            self.name_label.setText(self.tr("Experiment:"))
            self.num_label.setText(self.tr("Number:"))
            self.img_label.setText(self.tr("Image:"))

            self.setEnabledActions(False)

    def TagInfo(self):
        """
    Create a table with valuable information about current experiment

    Table include such parameters as:
        -Experiment Name
        -Experiment Number
        -Study Date
        -Study Time
        -Acqusition Date
        -Acqusition Time
        -Dimension
        -Resolution
        -Slice Distance
        -Left top coordiantes
        -Image type
        Slice orientation

        """
        self.tagModel = QStandardItemModel()
        self.winTag = QtWidgets.QWidget(parent = self)
        self.winTag.setWindowFlags(QtCore.Qt.Window | 
                                   QtCore.Qt.WindowMaximizeButtonHint | 
                                   QtCore.Qt.WindowCloseButtonHint)
        self.winTag.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.winTag.setWindowTitle(self.tr("Image Info"))
        self.winTag.resize(305,400)
        self.viewTag = QtWidgets.QTreeView()

        self.tagModel.setColumnCount(2)
        self.tagModel.setHorizontalHeaderLabels({self.tr("Value"), 
                                                 self.tr("Name")})

        data = self.tree.ImageData[self.curExpName][self.curExpNum]["data"]

        #Experiment Name tag
        self.set_Tag_and_Val("ExperimentName", self.curExpName)

        #Experiment Number tag
        self.set_Tag_and_Val("ExperimentNumber", self.curExpNum)

        from time import strptime
        
        if data.visu:
            #Study Date tag
            month_num = strptime(re.search(r"\w{3}", 
                                           data.visu["VisuStudyDate"]).group(),'%b').tm_mon
            new_date = re.sub(r"(\s\w{3}\s)",
                              ".{}.".format(month_num),
                              data.visu["VisuStudyDate"])
            self.set_Tag_and_Val("Study Date",
                            re.search(r"\d+\.\d+\.\d{4}",new_date).group())
            #Study Time tag
            self.set_Tag_and_Val("Study Time",
                            re.search(r"\d{2}:\d{2}:\d{2}", data.visu["VisuStudyDate"]).group())

        #Acqusition Date tag
        try:
            month_num = strptime(re.search(r"\w{3}", 
                                           data.acqp["ACQ_time"]).group(),'%b').tm_mon
            new_date = re.sub(r"(\s\w{3}\s)",
                              ".{}.".format(month_num), 
                              data.acqp["ACQ_time"])
        except Exception as err:
            utils.logger.error("Error: uncorrect read {0} in {1}\{2}".format(err, self.curExpName,self.curExpNum))

        self.set_Tag_and_Val("Acqusition Date",
                        re.search(r"\d+\.\d+\.\d{4}", new_date).group())

        #Acqusition Time tag
        try:
            self.set_Tag_and_Val("Acqusition Time",
                            re.search(r"\d{2}:\d{2}:\d{2}", data.acqp["ACQ_time"]).group())
        except Exception as err:
            utils.logger.error("Error: uncorrect read {0} in {1}\{2}".format(err, self.curExpName,self.curExpNum))

        #dimension tag
        self.set_Tag_and_Val("Dimension", 
                        str(data.Dimension[1]),
                        str(data.Dimension[2]),
                        str(data.Dimension[0]))

        # resolution tag
        if data.Resolution().any():
            self.set_Tag_and_Val("Resolution",
                            "{:.5}".format(data.Resolution()[0]),
                            "{:.5}".format(data.Resolution()[1]))

        # sliceDistance tag
        if data.SliceDistance():
            self.set_Tag_and_Val("SliceDistance",
                            "{:.5}".format(data.SliceDistance()))

        # LeftTopCoordinates tag
        if data.LeftTopCoordinates().any():
            dim = len(data.LeftTopCoordinates())
            self.set_Tag_and_Val("LeftTopCoordinates",
                            str(data.LeftTopCoordinates()[0 : int(dim/3)][0]),
                            str(data.LeftTopCoordinates()[int(dim/3) : int(2*dim/3)][0]),
                            str(data.LeftTopCoordinates()[int(2*dim/3) :][0]))

        # ImageWordType tag
        self.set_Tag_and_Val("ImageWordType",
                        str(data.ImageWordType()))

        # sliceOrientation tag
        if data.SliceOrientation().any():
            dim = len(data.SliceOrientation())
            self.set_Tag_and_Val("SliceOrientation",
                            str(data.SliceOrientation()[0 : int(dim/3)][0]),
                            str(data.SliceOrientation()[int(dim/3) : int(2*dim/3)][0]),
                            str(data.SliceOrientation()[int(2*dim/3) :][0]))

        self.viewTag.setModel(self.tagModel)
        self.viewTag.setColumnWidth(0,150)
        self.viewTag.setAlternatingRowColors(True)
        self.viewTag.expandAll()

        OKbutton = QtWidgets.QPushButton(self.tr("OK"),self.winTag)
        OKbutton.setDefault(True)
        OKbutton.clicked.connect(self.winTag.close)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(OKbutton, 1, QtCore.Qt.AlignLeft)

        box = QtWidgets.QVBoxLayout()
        box.addWidget(self.viewTag)
        box.addLayout(hbox)
        self.winTag.setLayout(box)

        self.winTag.show()

    def toggleDockWidget(self):
        if self.dock.isHidden():
            self.dock.show()
            self.toggleDock.setText(self.tr("Hide Contents"))
        else:
            self.dock.hide()
            self.toggleDock.setText(self.tr("Show Contents"))

    def tree_on_finished(self):
        QtWidgets.QApplication.restoreOverrideCursor()
        try:
            maxval = int(utils.num_pattern.findall(self.tree.getCurrentNumberItem().text(0))[-1])
            self.scroll.setMaximum(maxval-1)

            self.scroll.setValue(0)
            self.scroll.valueChanged.emit(0)
            self.saveAllCheckedAs.setEnabled(True)
            self.saveAllCheckedAsbutton.setEnabled(True)
            utils.logger.info("Bruker data are loaded")
        except :
            utils.logger.warning("No Bruker data in that directory name!!!")
            QtWidgets.QMessageBox.warning(
                        self, 
                        self.tr("Directory Warning"),
                        self.tr("No Bruker data in that directory name!!!"))

        self.state_label.setText(self.tr("Ready"))

    def tree_on_started(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        utils.logger.info("\n\nLoading are started!!!")

    def zoomIn(self):
        self.win.view.scaleBy(0.8)

    def zoomOut(self):
        self.win.view.scaleBy(1.25)

    def zoomToFit(self):
        self.win.view.autoRange()
        self.win.rotation = 0
        self.scroll.valueChanged.emit(self.scroll.value())
