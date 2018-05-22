from PyQt5 import QtCore

import os, tempfile
from scipy.misc import toimage
import bruker

import utils

from FilesTreeWidget import *

__all__ = ["FilesTreeThread", "SaveThread"]


class FilesTreeThread(QtCore.QThread):
    def __init__(self, parent = None, mode = "create", dirnames = ""):
        super().__init__()
        self.parent = parent
        self.fail = 0
        self.mode = mode
        self.dirnames = dirnames

    def run(self):
        if not self.dirnames:
            self.parent.tree.manageTree(self.parent.curDir, self.mode)
        else:
            #for dirname in self.dirnames:
            self.parent.tree.manageTree(self.dirnames, self.mode)

class CANCELThread(Exception):
    pass

class SaveThread(QtCore.QThread):
    """ 
Create thread for saving experiment in the text format
if self.trigger == "all" then each experiment will be saved as 
    a single text file in the folder corresponding to the experiment name
else self.trigger == "single" then only one experiment will be saved without creating folder

    """
    progressText = QtCore.pyqtSignal(str)
    progress = QtCore.pyqtSignal(int)
    suggestedTypes = ["Image", "XML", "Text"]
    def __init__(self, parent, savepath, saveType, form = "", filename = ""):
        super().__init__()

        self.saveType = saveType
        if self.saveType not in self.suggestedTypes:
            raise CANCELThread("Uncorrect function type")

        self.parent = parent
        self.SaveDir = savepath
        self.form = "xml" if self.saveType=="XML" else form
        self.trigger = "all"
        self.cancelThread = False
        self.filename = filename

    def _SaveAllChecked(self):

        completed = 0
        data = self.parent.tree.ImageData

        checkedItemList = []
        self.parent.tree.findCheckedItems(self.parent.tree.invisibleRootItem(), checkedItemList)

        allDim = 0
        self.progressText.emit(self.tr("Data size counting"))
        for expNumItem in checkedItemList:
            allDim += int(utils.num_pattern.findall(expNumItem.text(0))[1])

        for expNumItem in checkedItemList:
            exp_name = self.parent.tree.getExpNameItem(expNumItem).text(0)
            exp_num = utils.num_pattern.findall(expNumItem.text(0))[0]

            saveDir = os.path.join(self.tmp_folder.name, exp_name)
            utils.checkdir(saveDir)

            if self.saveType == "Image":
                saveDir = os.path.join(saveDir, exp_num)
                utils.checkdir(saveDir)

            if self.saveType != "Image":
                fname = '{0}{1}Experiment_{2}.{3}'.format(saveDir,
                                                          os.sep,
                                                          exp_num,
                                                          self.form)

            img_data = data[exp_name][exp_num]["data"]
            for i in range(img_data.Dimension[0]):
                if self.cancelThread:
                    raise CANCELThread()

                if self.saveType == "Image":
                    fname = '{0}{1}Image_{2}.{3}'.format(saveDir, 
                                                         os.sep, 
                                                         i+1, 
                                                         self.form)
                    self.progressText.emit(
                        self.tr("Writting Image_{0}.{1} to the folder /{2}/{3}").format(
                                                                                i+1,
                                                                                self.form,
                                                                                exp_name,
                                                                                exp_num))
                    toimage(img_data.IntenseData[i,:,:], 
                            cmin=img_data.min_val, cmax=img_data.max_val).save(fname)

                else:    
                    self.progressText.emit(
                        self.tr("Writting Image {0}\{1} to the Experiment_{2}.{3}").format(
                                                                            i+1,
                                                                            img_data.Dimension[0],
                                                                            exp_num,
                                                                            self.form))

                    eval("bruker.SingleWriteTo{}File".format(self.saveType))(fname,
                                                                             img_data,
                                                                             i,
                                                                             i==0)

                completed += 100/allDim
                self.progress.emit(completed)

    def _SaveSingle(self):
        """
    Saving current experiment number
        """
        completed = 0
        allDim = self.parent.scroll.maximum()
        saveDir = self.tmp_folder.name
        img_data = self.parent.tree.ImageData[self.parent.curExpName][self.parent.curExpNum]["data"]

        # add ".xml" postfix if it's not presented for XML files
        if self.saveType == "XML":
            try:
                self.filename = re.search(r".+\.xml$", self.filename).group()
            except AttributeError:
                self.filename += ".xml"

        fname = '{0}{1}{2}'.format(saveDir, 
                                   os.sep, 
                                   self.filename)

        for i in range(allDim):
            if self.cancelThread:
                raise CANCELThread()

            if self.saveType == "Image":
                fname = '{0}{1}{2}_{3}.{4}'.format(saveDir,
                                                   os.sep,
                                                   self.filename,
                                                   i+1,
                                                   self.form)
                self.progressText.emit(
                        self.tr("Writting {0}_{1}.{2}").format(self.filename, 
                                                               i+1,
                                                               self.form))

                toimage(img_data.IntenseData[i,:,:], 
                    cmin=img_data.min_val, cmax=img_data.max_val).save(fname)

            else:
                self.progressText.emit(
                        self.tr("Writting Image {0}\{1} to the {2}").format(i+1,
                                                                        allDim + 1, 
                                                                        self.filename))

                eval("bruker.SingleWriteTo{}File".format(self.saveType))(fname, 
                                                                         img_data,
                                                                         i,
                                                                         i==0)
            completed += 100/allDim
            self.progress.emit(completed)

    def run(self):

        try:
            utils.checkdir(self.SaveDir)

            # create a temporary folder
            self.tmp_folder = tempfile.TemporaryDirectory(suffix = ".TMP",
                                                          prefix="_BrukerGUI_",
                                                          dir = self.SaveDir)
            if self.trigger == "all":
                self._SaveAllChecked()

            elif self.trigger == "single":
                self._SaveSingle()

        except CANCELThread: 
            self.quit()
