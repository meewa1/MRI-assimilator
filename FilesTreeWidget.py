from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QBrush,QColor

import utils, inspect, os
import bruker
from itertools import compress

ITEMCOLORS = {
    "imageInit": QBrush(QColor("white")),
    "imageNegative" : QBrush(QColor("yellow"), QtCore.Qt.DiagCrossPattern),
    "imageCurrent" : QBrush(QColor(0,255,0,128)),
    "numberInit" : QBrush(QColor("white")),
    "numberNegative" : QBrush(QColor("yellow"), QtCore.Qt.DiagCrossPattern),
    "numberCurrent" : QBrush(QColor(255,150,0, 128)),
    "nameInit" : QBrush(QColor("white")),
    "nameCurrent" : QBrush(QColor("lightGray"))
}

class FilesTreeWidget(QtWidgets.QTreeWidget):
    nameItemcreate = QtCore.pyqtSignal(str, int)
    numItemcreate = QtCore.pyqtSignal(str, int)
    imgItemcreate = QtCore.pyqtSignal(str, int)
    def __init__(self, parent, scroll):
        super().__init__()
        self.parent = parent
        self.headerItem().setHidden(True)
        self.scroll = scroll
        self.nocheckeditem = 0

        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,\
                                       QtWidgets.QSizePolicy.Ignored)
        self.setSizePolicy(policy)
        self.itemDoubleClicked.connect(self.selectionitem)
        self.itemChanged.connect(self.changeditem)

        self.CurrentItem = None
        self.imageItem = None
        self.numberItem = None
        self.nameItem = None
        self.ImageData = {}
    
    def changeditem(self, item, column):
        
        try: 
            # exclude image items otherwise infinite loop is happened
            # when you unchecked all items
            # also exclude nameItem
            item.child(0).text(0)
            item.parent().text(0)

            checkedItemList = []
            self.findCheckedItems(self.invisibleRootItem(), checkedItemList)
            
            curitem = self.getCurrentImageItem()
            try:
                if not checkedItemList:
                    self.removeItemsColorBack(curitem)
                    self.setCurrentImageItem(None)
                    self.scroll.valueChanged.emit(0)
     
                elif not curitem or self.getExpNumberItem(curitem) not in checkedItemList:

                    if curitem and item == self.getExpNumberItem(curitem):
                        item = self.nearestItem

                    maxval = int(utils.num_pattern.findall(self.getExpNumberItem(item).text(0))[-1])
                    self.setCurrentImageItem(self.getImageItem(item, 0))
                    self.scroll.setMaximum(maxval-1)
                    self.scroll.setValue(0)
                    self.scroll.valueChanged.emit(0)
                else:
                    self.nearestItem = self.findFrontNearestCheckedItem(curitem)
            except Exception as err:
                utils.logger.exception(err)
        except Exception as err:
            pass

    def changeItemsColor(self):
        curitem = self.getCurrentImageItem()
        cur_nameItem = self.getCurrentNameItem()
        cur_numberItem = self.getCurrentNumberItem()

        self.removeItemsColorBack(self.prev_imageItem)

        # change color of the nameItem item corresponding to experiment name
        cur_nameItem.setBackground(0, ITEMCOLORS["nameCurrent"])

        # change color of the numberItem item corresponding to experiment number
        cur_numberItem.setBackground(0,ITEMCOLORS["numberCurrent"])
    
        # change color of the imageItem item corresponding to experiment image
        curitem.setBackground(0, ITEMCOLORS["imageCurrent"])
        self.prev_imageItem = curitem

    def deleteExpNameItem(self, item):
        exp_name = item.text(0)

        self.ImageData.pop(exp_name, None)
        self.invisibleRootItem().removeChild(item)
        if self.invisibleRootItem().childCount() == 0:
            self.setCurrentImageItem(None)
            self.scroll.valueChanged.emit(0)
        
    def deleteExpNumItem(self, item):
        exp_name = item.parent().text(0)
        exp_num = utils.num_pattern.findall(item.text(0))[0]
        
        if item == self.getCurrentNumberItem():
            newNumItem = self.findFrontNearestCheckedItem(item)
            if newNumItem != self.getCurrentNumberItem():
                self.setCurrentImageItem(newNumItem.child(0))
            else:
                self.setCurrentImageItem(None)

            self.scroll.valueChanged.emit(0)

        self.ImageData[exp_name].pop(exp_num, None)
        item.parent().removeChild(item)
        # necessary for the excluding the item color change error
        self.prev_imageItem = self.invisibleRootItem().child(0).child(0).child(0)

    def findBackNearestCheckedItem(self, curitem):
        """
    Return numItem which is a nearest to curitem in the descending order.
        """
        checkedItemList = []
        self.findCheckedItems(self.invisibleRootItem(), checkedItemList)

        if self.isImageItem(curitem):
            curitem = self.getExpNumberItem(curitem)

        if len(checkedItemList) > 1:
            nearestItem = None
            for item in checkedItemList:                
                if item == curitem:
                    break
                nearestItem = item
            if not nearestItem:
                nearestItem = checkedItemList[-1]
        else:
            nearestItem = curitem

        return nearestItem

    def findCheckedItems(self, item, itemList):
        """
    Return list of numberItems which are checked
        """
        if item.checkState(0) == QtCore.Qt.Checked and item.parent():
            itemList.append(item)

        for i in range(item.childCount()):
            self.findCheckedItems(item.child(i), itemList)

    def findFrontNearestCheckedItem(self, curitem):
        """
    Return numItem which is a nearest to curitem in the ascending order.
        """
        checkedItemList = []
        self.findCheckedItems(self.invisibleRootItem(), checkedItemList)

        if self.isImageItem(curitem):
            curitem = self.getExpNumberItem(curitem)

        if len(checkedItemList) > 1:
            nearestItem = None
            for item in reversed(checkedItemList):
                if item == curitem:
                    break
                nearestItem = item
            if not nearestItem:
                nearestItem = checkedItemList[0]
        else:
            nearestItem = curitem

        return nearestItem

    def getBackItem(self, curitem):
        """
    Return a tree item following the curitem in descending order.

    If function is called from "BrukerGraphicsLayoutWidget" 
        then items are chosen from all checked experiments.
    If function is called from "ImageScrollBar" 
        then items are chosen from the same experiment as the curitem.

    IMPORTANT: only image item items are returned
        """
        callingclass = utils.getCallingClassName(inspect.currentframe())
        if callingclass == "BrukerGraphicsLayoutWidget":
            exp_name = self.getExpNameItem(curitem)
            exp_num = self.getExpNumberItem(curitem)
            curIndex =  exp_num.indexOfChild(curitem)
            if curIndex > 0:
                backIndex = curIndex - 1
                return exp_num.child(backIndex)
            else:
                nearestItem = self.findBackNearestCheckedItem(curitem)
                maxval = int(utils.num_pattern.findall(nearestItem.text(0))[-1])
                return nearestItem.child(maxval - 1)

        elif callingclass == "ImageScrollBar":
            exp_num = self.getExpNumberItem(curitem)
            maxval = int(utils.num_pattern.findall(exp_num.text(0))[-1])
            curIndex =  exp_num.indexOfChild(curitem)
            backIndex = curIndex - 1 if curIndex > 0 else maxval-1
            return exp_num.child(backIndex)

    def getCurrentImageItem(self):
        return self.CurrentItem

    def getCurrentNameItem(self):
        return self.CurrentItem.parent().parent()

    def getCurrentNumberItem(self):
        return self.CurrentItem.parent()

    def getExpNameItem(self, item):
        """
    Return expName item as a QTreeWidgetItem object
        """

        # item from nameItem
        if not item.parent():
            return item
        # item from numberItem
        elif not item.parent().parent():
            return item.parent()
        # item from imageItem
        else:
            return item.parent().parent()

    def getExpNumberItem(self, item):
        """
    Return expNum item as a QTreeWidgetItem object
        """

        # item from nameItem
        if not item.parent():
            return None
        # item from numberItem
        elif not item.parent().parent():
            return item
        # item from imageItem
        else:
            return item.parent()

    def getFrontItem(self, curitem):
        """
    Return a tree item following the curitem in ascending order.

    If function is called from "BrukerGraphicsLayoutWidget" 
        then items are chosen from all checked experiments.
    If function is called from "ImageScrollBar" 
        then items are chosen from the same experiment as the curitem.

    IMPORTANT: only image item items are returned
        """
        callingclass = utils.getCallingClassName(inspect.currentframe())

        if callingclass == "BrukerGraphicsLayoutWidget":
            exp_num = self.getExpNumberItem(curitem)
            maxval = int(utils.num_pattern.findall(exp_num.text(0))[-1])
            curIndex =  exp_num.indexOfChild(curitem)
            if curIndex < maxval-1:
                frontIndex = curIndex + 1
                return exp_num.child(frontIndex)
            else:
                nearestItem = self.findFrontNearestCheckedItem(curitem)
                return nearestItem.child(0)

        elif callingclass == "ImageScrollBar":
            exp_num = self.getExpNumberItem(curitem)
            maxval = int(utils.num_pattern.findall(exp_num.text(0))[-1])
            curIndex =  exp_num.indexOfChild(curitem)
            frontIndex = curIndex + 1 if curIndex < maxval-1 else 0
            return exp_num.child(frontIndex)

    def getImageItem(self, item, index):
        """
    Return image item as a QTreeWidgetItem object
        """

        # item from nameItem
        if not item.parent():
            return None
        # item from numberItem
        elif not item.parent().parent():
            return item.child(index)
        # item from imageItem
        else:
            return item

    def isImageItem(self, item):
        return bool(not item.child(0))

    def isNameItem(self, item):
        return bool(not item.parent())

    def isNumberItem(self, item):
        return bool(item.parent() and item.child(0))

    def manageTree(self, dirname, mode = "create"):
        """ 
    Create tree in the dockwidget with the following hierarchy:
        -nameItem (corresponding to experiment name)
            -numberItem (corresponding to experiment number)
                -imageItem (corresponding to image from experiment number)
        """
        first_image = mode == "create"

        dirname = os.path.normpath(dirname)
        files_dir = bruker.ReadDirectory(dirname)
        for exp_name in files_dir.keys():

            items = self.findItems(exp_name,
                                    QtCore.Qt.MatchExactly 
                                    | QtCore.Qt.MatchRecursive,
                                    0)

            if not items:
                self.ImageData[exp_name] = {}
                self.nameItemcreate.emit(exp_name, first_image)
                self.parent.treeThread.usleep(1)
            else:
                self.nameItem = items[0]

            for exp_num in files_dir[exp_name].keys():
                items = self.findItems('{} ('.format(exp_num),
                                    QtCore.Qt.MatchContains 
                                    | QtCore.Qt.MatchRecursive,
                                    0)

                # looking for presence of exp_num item
                boolItems = [self.getExpNameItem(itm).text(0) == exp_name for itm in items]
                addingItems = list(compress(range(len(boolItems)), boolItems))

                if not addingItems:
                    self.ImageData[exp_name][exp_num] = {}
                    self.ImageData[exp_name][exp_num]["data"] = \
                          bruker.ReadExperiment(files_dir, exp_num, exp_name)

                    img_data = self.ImageData[exp_name][exp_num]["data"]

                    if img_data:
                        try:
                            # create a "correction" key if there is a negative number
                            if img_data.min_val < 0:
                                self.ImageData[exp_name][exp_num]["correction"] = True

                            self.numItemcreate.emit("{0} ({1})".format(exp_num, img_data.Dimension[0]),
                                                first_image)
                            self.parent.treeThread.usleep(1)

                            for i in range(img_data.Dimension[0]):
                                self.imgItemcreate.emit(str(i+1), first_image)
                                self.parent.treeThread.usleep(1)
                                # write values of brightness and contrast in img data as list [brightness, contrast]
                                self.ImageData[exp_name][exp_num][str(i)] = [0, 1]
                                if first_image:
                                    self.ImageData["numberOfImages"] = 0
                                    self.prev_imageItem = self.imageItem

                                    first_image = 0

                            self.ImageData["numberOfImages"] += img_data.Dimension[0]
                        except AttributeError as err:
                            utils.logger.error(err)

    def removeItemsColorBack(self, item):
        # redraw items in initial color
        if item and item.parent():
            self.setInitItemColor(item)
            if not self.isNameItem(item):
                self.setNegativeItemColor(item)

            self.removeItemsColorBack(item.parent())

    def removeItemsColorFront(self, item):
        if item and item.parent():
            self.setInitItemColor(item)
            if not self.isNameItem(item):
                self.setNegativeItemColor(item)

            if item.child(0):
                for idx in range(item.childCount()):
                    if item.child(idx):
                        self.removeItemsColorFront(item.child(idx))

    def sameNumberItem(self):
        return self.getExpNumberItem(self.prev_imageItem) == self.getCurrentNumberItem()

    def selectionitem(self, item):
        try:
            exp_num = self.getExpNumberItem(item)
            exp_name = self.getExpNameItem(item)

            checkedItemList = []
            self.findCheckedItems(self.invisibleRootItem(), checkedItemList)

            if exp_num in checkedItemList:

                if exp_num != self.getCurrentNumberItem():
                    maxval = int(utils.num_pattern.findall(exp_num.text(0))[-1])
                    self.scroll.setMaximum(maxval - 1)

                if self.isNumberItem(item):
                    item = item.child(0)

                value = int(item.text(0))-1
                self.setCurrentImageItem(item)
                self.scroll.setValue(value)
                self.scroll.valueChanged.emit(value)

                self.prev_imageItem = item

        except Exception as err:
            utils.logger.exception(err)

    def setCurrentImageItem(self, item):
        self.CurrentItem = item

    def setInitItemColor(self, item):
        if item.parent():
            if self.isNameItem(item):
                item.setBackground(0, ITEMCOLORS["nameInit"])

            elif self.isNumberItem(item):
                item.setBackground(0, ITEMCOLORS["numberInit"])

            elif self.isImageItem(item):
                item.setBackground(0, ITEMCOLORS["imageInit"])

    def setNegativeItemColor(self, item):
        if item.parent():
            expName = self.getExpNameItem(item).text(0)
            expNum = utils.num_pattern.findall(self.getExpNumberItem(item).text(0))[0]
            if "correction" in self.ImageData[expName][expNum]:
                if self.ImageData[expName][expNum]["correction"]:
                    if self.isNumberItem(item):
                        item.setBackground(0, ITEMCOLORS["numberNegative"])
                    elif self.isImageItem(item):
                        item.setBackground(0, ITEMCOLORS["imageNegative"])

    def sizeHint(self):
        return QtCore.QSize(165, 140)