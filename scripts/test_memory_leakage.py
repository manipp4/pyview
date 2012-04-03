from pyview.lib.datacube import *
from pyview.helpers.datamanager import DataManager


if __name__ == '__main__':
  dataManager = DataManager()
  datas = []
  while True:
    for i in range(0,1000):
      data = Datacube("test")
      child = Datacube("child")
      data.addChild(child,name = "test")
      datas.append(data)
      dataManager.addDatacube(data)
      for j in range(0,1000):
        data.set(x = j,y = j*j,z = j*j*j)
        data.commit()
    print "clearing..."
    datas = []
    dataManager.clear()
      