##
from pyview.gui.editor.codeeditor import *

import sys

app = QApplication(sys.argv)
##

editor = CodeEditor()
editor.show()
editor.setPlainText("""
test
sdfsfsdf
    sfsdfsdf
    
sdfsdfsdf
sdfsdf
  sdfsdf  
""")
import threading
print threading.current_thread().ident
print app
print app.thread()
app.exec_()