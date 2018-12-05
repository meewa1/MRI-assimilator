from PyQt5.QtWidgets import QToolButton
from PyQt5.QtCore import Qt

class SaveToolButton(QToolButton):
	def __init__(self, parent=None):
		super().__init__()
		self.setArrowType(Qt.NoArrow)

	def mousePressEvent(self, event):
		self.showMenu()