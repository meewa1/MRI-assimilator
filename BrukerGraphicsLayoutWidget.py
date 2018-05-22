from pyqtgraph import GraphicsLayoutWidget
from PyQt5 import QtCore
import utils

__all__ = ['BrukerGraphicsLayoutWidget']

class BrukerGraphicsLayoutWidget(GraphicsLayoutWidget):
    def __init__(self, scroll, tree, parent=None, **kargs):
        super().__init__()
        self.scroll = scroll

        self.view = self.addViewBox(enableMenu=False, lockAspect = True)

        self.tree = tree
        self.rotation = 0

    def setTree(self, tree):
        self.tree = tree

    def setRotation(self, value):
        self.rotation = (self.rotation + value) % 4
        self.scroll.valueChanged.emit(self.scroll.value())

    def getRotation(self):
        return self.rotation

    def wheelEvent(self, event):
        if self.scroll.maximum() > 0:
            if(event.modifiers() == QtCore.Qt.NoModifier):
                try:
                    curitm = self.tree.getCurrentImageItem()
                    # scroll down
                    if event.angleDelta().y() < 0:
                        nextitem = self.tree.getFrontItem(curitm)
                    # scroll up
                    if event.angleDelta().y() > 0:
                        nextitem = self.tree.getBackItem(curitm)

                    if curitm.parent() != nextitem.parent():
                        new_scroll_val = int(utils.num_pattern.findall(nextitem.parent().text(0))[-1])
                        self.scroll.setMaximum(new_scroll_val-1)

                    self.tree.setCurrentImageItem(nextitem)
                    idx = int(nextitem.text(0))-1
                    self.scroll.setValue(idx)
                    self.scroll.valueChanged.emit(idx)

                except Exception as err:
                    utils.logger.exception(err)

            # allows to scale image with scrolling
            elif(event.modifiers() == QtCore.Qt.ControlModifier):
                if event.angleDelta().y() > 0:
                    self.view.scaleBy(1/1.1)
                    #self.view.rotate(1)
                elif event.angleDelta().y() < 0:
                    self.view.scaleBy(1.1)

    # def mouseMoveEvent(self, ev):
    #     if ev.buttons() == QtCore.Qt.MidButton:
    #         pass
    #     else:
    #         GraphicsLayoutWidget.mouseMoveEvent(self, ev)