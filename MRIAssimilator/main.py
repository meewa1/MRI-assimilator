#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys, os

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen

# disable PyQt messages in the console
def handler(msg_type, msg_log_context, msg_string):
	pass
	# from utils import logger
    # if (msg_type == 0):
    #     logger.info("Debug: %s (%s:%u, %s)\n" % (msg_string, msg_log_context.file, msg_log_context.line, msg_log_context.function))

    # elif (msg_type == 1):
    #     logger.warning("Warning: %s (%s:%u, %s)\n" % (msg_string, msg_log_context.file, msg_log_context.line, msg_log_context.function))

    # elif (msg_type == 2):
    #     logger.error("Critical: %s (%s:%u, %s)\n" % (msg_string, msg_log_context.file, msg_log_context.line, msg_log_context.function))

    # elif (msg_type == 3):
    #     logger.error("Fatal: %s (%s:%u, %s)\n" % (msg_string, msg_log_context.file, msg_log_context.line, msg_log_context.function))

    # elif (msg_type == 4):
    #     logger.info("Info: %s (%s:%u, %s)\n" % (msg_string, msg_log_context.file, msg_log_context.line, msg_log_context.function))

from PyQt5.QtCore import qInstallMessageHandler
qInstallMessageHandler(handler)

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

import io
from utils import EXIT_CODE_REBOOT

if __name__ == '__main__':

	sys.stdout = buf = io.StringIO()

	currentExitCode = EXIT_CODE_REBOOT
	while currentExitCode == EXIT_CODE_REBOOT:

		app = QApplication.instance() # checks if QApplication already exists
		if not app: # create QApplication if it doesnt exist
			app = QApplication(sys.argv)
			
		app.aboutToQuit.connect(app.deleteLater)
		
		# LoadScreen = utils.resource_path(r"pictures\MRIASplashScreen.png")
		# splashscreen = QSplashScreen(QPixmap(LoadScreen))
		
		# splashscreen.show()

		from PyQt5.QtCore import Qt, QTranslator, QSettings

		setting = QSettings("locale","language")
		cur_lang = QSettings("locale","language").value('lang', type=str)
		if not cur_lang:
			setting.setValue("lang", "ru_RU")
			cur_lang = "ru_RU"

		from utils import resource_path
		translator = QTranslator()
		switchTranslator(translator, 
						 resource_path(r"translations\MRIAssimilator_{}".format(cur_lang)))

		# splashscreen.showMessage(app.translate("SplachScreen","Version 1.0 (c) 2018"),
		# 						 Qt.AlignBottom | Qt.AlignCenter)

		switchQtTranslator(cur_lang)

		from MRIA_GUI import MRIAMainWindow
		main = MRIAMainWindow()

		#splashscreen.finish(main)
	   # app.installEventFilter(ex)
		currentExitCode = app.exec_()
		#buf.getvalue()
		app = None # delete the QApplication object
