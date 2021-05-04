#!/usr/bin/python3 -u

#libs
import signal
import sys
import time

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QFontDatabase
from PyQt5.QtCore import QLocale, QTranslator, QTimer, QLibraryInfo

#local imports
from gui_tools import ArgParser, CommandLineArgs, init_gui_tools, get_code_root
from gui_server_thread import GuiServerThread
from gui_session import SignaledSession
import ray


def signalHandler(sig, frame):
    if sig in (signal.SIGINT, signal.SIGTERM):
        if session.daemon_manager.launched_before:
            if (CommandLineArgs.under_nsm
                    and session.server_status != ray.ServerStatus.OFF):
                session.main_win.terminate_request = True

                l_server = GuiServerThread.instance()
                if l_server:
                    l_server.abort_session()
            else:
                session.daemon_manager.stop()
            return

        session.main_win.terminate_request = True
        session.daemon_manager.stop()

if __name__ == '__main__':
    # set Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName(ray.APP_TITLE)
    app.setApplicationVersion(ray.VERSION)
    app.setOrganizationName(ray.APP_TITLE)
    app.setWindowIcon(QIcon(':/scalable/%s.svg' % ray.APP_TITLE.lower()))
    #app.setWindowIcon(QIcon(':/scalable/test_icon.svg'))
    app.setQuitOnLastWindowClosed(False)
    app.setDesktopFileName(ray.APP_TITLE.lower())

    ### Translation process
    locale = QLocale.system().name()

    appTranslator = QTranslator()
    if appTranslator.load(QLocale(), ray.APP_TITLE.lower(),
                          '_', "%s/locale" % get_code_root()):
        app.installTranslator(appTranslator)

    sysTranslator = QTranslator()
    pathSysTranslations = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if sysTranslator.load(QLocale(), 'qt', '_', pathSysTranslations):
        app.installTranslator(sysTranslator)

    QFontDatabase.addApplicationFont(":/fonts/Ubuntu-R.ttf")
    QFontDatabase.addApplicationFont(":fonts/Ubuntu-C.ttf")

    # get arguments
    parser = ArgParser()

    init_gui_tools()

    # Add raysession/src/bin to $PATH
    # to can use raysession after make, whitout install
    ray.addSelfBinToPath()

    #connect signals
    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)

    #needed for signals SIGINT, SIGTERM
    timer = QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: None)

    #build session
    server = GuiServerThread()
    session = SignaledSession()

    app.exec()

    # TODO find something better, sometimes program never ends without.
    #time.sleep(0.002)

    server.stop()
    session.quit()
    del session
    del app
