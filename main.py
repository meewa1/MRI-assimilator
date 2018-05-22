#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys, os

# necessary for path in PyInstaller
def resource_path(relative_path, folder = ""):
	""" Get absolute path to resource, works for dev and for PyInstaller """
	try:
		# PyInstaller creates a temp folder and stores path in _MEIPASS
		base_path = sys._MEIPASS
	except Exception:
		base_path = os.path.abspath(folder)

	return os.path.join(base_path, relative_path)

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen

def switchTranslator(translator, filename, path = ""):
	QApplication.removeTranslator(translator)

	if(translator.load(filename, path)):
		QApplication.installTranslator(translator)

def switchQtTranslator(cur_lang):
	from PyQt5.QtCore import QTranslator, QLibraryInfo

	translatorQt = QTranslator()
	translatorQt_help = QTranslator()
	translatorQt_base = QTranslator()
	translatorQt_connectivity = QTranslator()
	translatorQt_declarative = QTranslator()
	translatorQt_location = QTranslator()
	translatorQt_multimedia = QTranslator()

	try:
		# PyInstaller creates a temp folder and stores path in _MEIPASS
		base_path = sys._MEIPASS
		pathToTransaltionsQT = os.path.join(base_path, "translations")
	except Exception:
		pathToTransaltionsQT = QLibraryInfo.location(QLibraryInfo.TranslationsPath)

	switchTranslator(translatorQt, 
					 "qt_" + cur_lang, pathToTransaltionsQT)
	switchTranslator(translatorQt_help,
					 "qt_help_" + cur_lang, pathToTransaltionsQT)
	switchTranslator(translatorQt_base, 
					 "qtbase_" + cur_lang, pathToTransaltionsQT)
	switchTranslator(translatorQt_connectivity,
					 "qtconnectivity_" + cur_lang, pathToTransaltionsQT)
	switchTranslator(translatorQt_declarative,
					 "qtdeclarative_" + cur_lang, pathToTransaltionsQT)
	switchTranslator(translatorQt_location,
					 "qtlocation_" + cur_lang, pathToTransaltionsQT)
	switchTranslator(translatorQt_multimedia,
					 "qtmultimedia_" + cur_lang, pathToTransaltionsQT)

import brkRebootConst
import io

if __name__ == '__main__':
	sys.stdout = buf = io.StringIO()
	currentExitCode = brkRebootConst.EXIT_CODE_REBOOT
	while currentExitCode == brkRebootConst.EXIT_CODE_REBOOT:

		app = QApplication.instance() # checks if QApplication already exists
		if not app: # create QApplication if it doesnt exist
			app = QApplication(sys.argv)
		app.aboutToQuit.connect(app.deleteLater)
		
		LoadScreen = resource_path(r"pictures\BrukerSplashScreen.png")
		splashscreen = QSplashScreen(QPixmap(LoadScreen))
		
		splashscreen.show()	

		from PyQt5.QtCore import Qt, QTranslator, QSettings

		setting = QSettings("locale","language")
		cur_lang = QSettings("locale","language").value('lang', type=str)
		if not cur_lang:
			setting.setValue("lang", "ru_RU")
			cur_lang = "ru_RU"
			
		translator = QTranslator()
		switchTranslator(translator, 
						 resource_path(r"translations\BrukerGUI_{}".format(cur_lang)))

		splashscreen.showMessage(app.translate("SplachScreen","Version 1.0 (c) 2018"),
								 Qt.AlignBottom | Qt.AlignCenter)

		switchQtTranslator(cur_lang)

		from brukerGUI import BrukerMainWindow
		main = BrukerMainWindow()

		splashscreen.finish(main)
	   # app.installEventFilter(ex)
		currentExitCode = app.exec_()
		buf.getvalue()
		app = None # delete the QApplication object
	#sys.exit(app.exec_())