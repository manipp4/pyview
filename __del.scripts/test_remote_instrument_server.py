from pyview.helpers.instrumentsmanager import Manager

if __name__ == '__main__':
  manager = Manager()
  instrument = manager.initInstrument("rip://127.0.0.1:8000/test","instruments.test",forceReload = False)
  for i in range(0,10):
    print i
    print instrument.measureSomething([1,2,3])["y"]