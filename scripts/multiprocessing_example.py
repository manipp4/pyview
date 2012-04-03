from pyview.helpers.coderunner import *
import time

if __name__ == '__main__':
  codeRunner = MultiProcessCodeRunner()
  codeRunner.restart()
  codeRunner.executeCode("from pyview.gui.datamanager import *;print 'Starting data manager...';startDataManagerThread();print 'Done'",1,filename = "test")
