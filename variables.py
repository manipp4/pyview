##Start the instruments panel and the data manager
import matplotlib

import sys
from pyview.gui.coderunner import *
from pyview.gui.variablepanel import *
reload(sys.modules["pyview.gui.variablepanel"])
from pyview.gui.variablepanel import *
	

def startVariablePanel():
		
	panel = VariablePanel(globals = gv)
	panel.show()
	
execInGui(startVariablePanel)

