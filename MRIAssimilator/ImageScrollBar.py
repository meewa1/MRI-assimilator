from PyQt5.QtWidgets import QScrollBar

class ImageScrollBar(QScrollBar):
    def __init__(self, tree=None):
        super().__init__()
        self.tree = tree

    def setTree(self, tree):
        self.tree = tree

    def wheelEvent(self, event):
        if self.maximum() > 0:
            # scroll down
            curitm = self.tree.getCurrentImageItem()
            if event.angleDelta().y() < 0:
                nextitem = self.tree.getFrontItem(curitm)

            # scroll up
            elif event.angleDelta().y() > 0:
                nextitem = self.tree.getBackItem(curitm)

            self.tree.setCurrentImageItem(nextitem)
            idx = int(nextitem.text(0))-1
            self.setValue(idx)
            self.valueChanged.emit(idx)