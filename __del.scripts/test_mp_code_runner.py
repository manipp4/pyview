import sys
import os,os.path
import time
import traceback

sys.path.append(os.path.abspath(os.path.normpath(__file__)+"\\..\\..\\..\\"))

from pyview.helpers.coderunner import *

if __name__ == '__main__':

    mp = MultiProcessCodeRunner()

    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
    app = QApplication(sys.argv)

    def updateOutputs():
        if not mp.codeProcess().is_alive():
          print "mp's dead..."
          mp.restart()
        sys.stdout.write(mp.stdout())
        sys.stderr.write(mp.stderr())

    def restartProcess():
      print "Stopping execution..."
#      mp.stopExecution("main")
      mp.restart()

    def executeCode():
        if not mp.codeProcess().is_alive():
          mp.restart()
        if mp.executeCode(editor.toPlainText().toUtf8(),widget.environment.text(),"c:\\test122#snippet_4#rev_13") == False:
          print "Process is busy..."

    timer = QTimer(None)
    timer.setInterval(100)
    timer.start()

    timer.connect(timer,SIGNAL("timeout()"),updateOutputs)

    window = QMainWindow()
    widget = QWidget()
    layout = QGridLayout()
    editor = QTextEdit()
    layout.addWidget(editor)
    executeButton = QPushButton("execute")
    killButton = QPushButton("kill")
    widget.environment = QLineEdit()
    widget.environment.setText("main")
    executeButton.connect(executeButton,SIGNAL("clicked()"),executeCode)
    killButton.connect(killButton,SIGNAL("clicked()"),restartProcess)
    layout.addWidget(executeButton)
    layout.addWidget(killButton)
    layout.addWidget(widget.environment)
    widget.setLayout(layout)
    window.setCentralWidget(widget)
    window.show()
    
    mp.stdin("hello, world!")

    app.exec_()

    mp.terminate()
 
