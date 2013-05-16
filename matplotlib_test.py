from pyview.gui.coderunner import *
from PyQt4.QtSvg import *
##
import os
os._exit(0)
##
import matplotlib
matplotlib.use('module://pyview.gui.mpl.backend')

from numpy import *
from matplotlib.pyplot import *	

figure(4)
cla()
plot(arange(0,100,0.1),cos(arange(0,100,0.1)*0.4))
plot(arange(0,100,0.1),cos(arange(0,100,0.1)*0.1))
plot(arange(0,100,0.1),cos(arange(0,100,0.1)*0.2))
xlabel("test")
ylabel("another sqdsdftest")
show()
##

print gcf().canvas.print_svg(gv.fig)
##Plot forever...
ioff()
import time
cnt = 0
while True:
	figure(3)
	cla()
	cnt+=0.1
	plot(arange(0,100,0.1),cos(arange(0,100,0.1)*0.1+cnt))
	time.sleep(0.1)	
##Plot a figure...
ioff()
figure(5)
cla()
clf()
m = zeros((101,101))
for i in range(0,100):
	for j in range(0,100):
		m[i,j] = i*0.3+cos(j*0.4)

imshow(m)
title("test")
xlabel("label")
ylabel("label")
show()
##Start the instruments panel...
import sys
from pyview.gui.coderunner import *
from pyview.gui.instrumentspanel import *
from pyview.gui.datamanager import *
reload(sys.modules["pyview.gui.datamanager"])
from pyview.gui.datamanager import *

def startInstrumentsPanel():
	
	global panel
	global manager
	
	panel = InstrumentsPanel()
	manager = DataManager(globals = gv)
	manager.show()
	panel.show()


execInGui(startInstrumentsPanel)
##
from pyview.lib.datacube import Datacube
from pyview.helpers.datamanager import DataManager
dataManager = DataManager()
cube = Datacube()
dataManager.addDatacube(cube)
for i in range(0,100):
	cube.set(x=i,y=i*i)
	cube.commit()