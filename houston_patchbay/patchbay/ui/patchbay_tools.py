# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'resources/ui/patchbay/patchbay_tools.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(885, 34)
        Form.setStyleSheet("QProgressBar{\n"
"border-radius: 0px;\n"
"text-align:center;\n"
"background-color:  rgba(50%, 50%, 50%, 25%);\n"
"}")
        self.horizontalLayout = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout.setContentsMargins(-1, 1, 0, 1)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.sliderZoom = ZoomSlider(Form)
        self.sliderZoom.setMaximumSize(QtCore.QSize(90, 16777215))
        self.sliderZoom.setMouseTracking(True)
        self.sliderZoom.setToolTip("")
        self.sliderZoom.setStyleSheet("QSlider:focus{\n"
"    border: none;\n"
"}\n"
"\n"
"\n"
"QSlider::handle:horizontal{\n"
"\n"
"     image: url(:scalable/breeze/zoom-centered.svg);\n"
"}")
        self.sliderZoom.setMinimum(0)
        self.sliderZoom.setMaximum(1000)
        self.sliderZoom.setSingleStep(10)
        self.sliderZoom.setPageStep(10)
        self.sliderZoom.setProperty("value", 500)
        self.sliderZoom.setTracking(True)
        self.sliderZoom.setOrientation(QtCore.Qt.Horizontal)
        self.sliderZoom.setInvertedAppearance(False)
        self.sliderZoom.setInvertedControls(False)
        self.sliderZoom.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.sliderZoom.setTickInterval(500)
        self.sliderZoom.setObjectName("sliderZoom")
        self.horizontalLayout.addWidget(self.sliderZoom)
        spacerItem1 = QtWidgets.QSpacerItem(6, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.lineSep1 = QtWidgets.QFrame(Form)
        self.lineSep1.setFrameShape(QtWidgets.QFrame.VLine)
        self.lineSep1.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.lineSep1.setObjectName("lineSep1")
        self.horizontalLayout.addWidget(self.lineSep1)
        spacerItem2 = QtWidgets.QSpacerItem(6, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem2)
        self.labelSamplerate = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.labelSamplerate.setFont(font)
        self.labelSamplerate.setObjectName("labelSamplerate")
        self.horizontalLayout.addWidget(self.labelSamplerate)
        self.labelSamplerateUnits = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.labelSamplerateUnits.setFont(font)
        self.labelSamplerateUnits.setObjectName("labelSamplerateUnits")
        self.horizontalLayout.addWidget(self.labelSamplerateUnits)
        spacerItem3 = QtWidgets.QSpacerItem(6, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem3)
        self.lineSep2 = QtWidgets.QFrame(Form)
        self.lineSep2.setFrameShape(QtWidgets.QFrame.VLine)
        self.lineSep2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.lineSep2.setObjectName("lineSep2")
        self.horizontalLayout.addWidget(self.lineSep2)
        spacerItem4 = QtWidgets.QSpacerItem(6, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.labelBuffer = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.labelBuffer.setFont(font)
        self.labelBuffer.setObjectName("labelBuffer")
        self.horizontalLayout.addWidget(self.labelBuffer)
        spacerItem5 = QtWidgets.QSpacerItem(2, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem5)
        self.comboBoxBuffer = QtWidgets.QComboBox(Form)
        self.comboBoxBuffer.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.comboBoxBuffer.setFont(font)
        self.comboBoxBuffer.setStyleSheet("QCombobox{align:right}")
        self.comboBoxBuffer.setObjectName("comboBoxBuffer")
        self.horizontalLayout.addWidget(self.comboBoxBuffer)
        spacerItem6 = QtWidgets.QSpacerItem(6, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem6)
        self.lineSep3 = QtWidgets.QFrame(Form)
        self.lineSep3.setFrameShape(QtWidgets.QFrame.VLine)
        self.lineSep3.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.lineSep3.setObjectName("lineSep3")
        self.horizontalLayout.addWidget(self.lineSep3)
        self.pushButtonXruns = QtWidgets.QPushButton(Form)
        self.pushButtonXruns.setMinimumSize(QtCore.QSize(70, 0))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.pushButtonXruns.setFont(font)
        self.pushButtonXruns.setStyleSheet("QPushButton{border:none; text-align:right}\n"
"QPushButton::hover{border: 1 px solid grey;text-align:right}")
        self.pushButtonXruns.setObjectName("pushButtonXruns")
        self.horizontalLayout.addWidget(self.pushButtonXruns)
        spacerItem7 = QtWidgets.QSpacerItem(6, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem7)
        self.progressBarDsp = ProgressBarDsp(Form)
        self.progressBarDsp.setMaximumSize(QtCore.QSize(80, 16777215))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progressBarDsp.setFont(font)
        self.progressBarDsp.setStyleSheet("")
        self.progressBarDsp.setProperty("value", 0)
        self.progressBarDsp.setObjectName("progressBarDsp")
        self.horizontalLayout.addWidget(self.progressBarDsp)
        self.labelJackNotStarted = QtWidgets.QLabel(Form)
        self.labelJackNotStarted.setObjectName("labelJackNotStarted")
        self.horizontalLayout.addWidget(self.labelJackNotStarted)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.labelSamplerate.setToolTip(_translate("Form", "JACK Samplerate"))
        self.labelSamplerate.setText(_translate("Form", "48.000"))
        self.labelSamplerateUnits.setText(_translate("Form", "Hz"))
        self.labelBuffer.setText(_translate("Form", "Buffer :"))
        self.pushButtonXruns.setToolTip(_translate("Form", "Number of audio Xruns. Click on it to reset them."))
        self.pushButtonXruns.setText(_translate("Form", "0 Xruns"))
        self.progressBarDsp.setFormat(_translate("Form", "DSP: %p%"))
        self.labelJackNotStarted.setText(_translate("Form", "<p style=\"color:red\">JACK is not started !</p>"))
from ..surclassed_widgets import ProgressBarDsp, ZoomSlider
import resources_rc
