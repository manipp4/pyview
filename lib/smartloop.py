class SmartLoop():
	def __init__(self,name='unamed loop'):
		self.name=name
		
	def __del__(self):
		return True
		
	def setList(self,l):
		self.i=0
		self.list=l
		
	def loop(self):
		try:
			self.value=self.list[self.i]
		except IndexError:
			return False
		except:
			raise
		else:
			return True			
    finally:
   		self.i+=1
	