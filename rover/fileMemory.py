#Benjamin Hoeller 0925688 TUWIEN 2013-2014
#fileMemory provides the permanent storage of a boolean value in the filesystem
#the value is true if the file exist, false otherwise
import os

class fileMemory:
    path=""

    # path: String - the path where to save the file
    def __init__(self,path):
        self.path=path
#        print ("fileMemory path: "+self.path)

    #sets the path to the __file__ standartvariable
    def __init__(self):
        self.path=os.path.dirname(os.path.abspath(__file__))
#        print ("fileMemory path: "+self.path)

    #returns a valid path for a .save file
    #name: String - the name of the .save file
    def getPath(self,name):
        return self.path+os.sep+name+'.save'

    #returns true if the .save file exists
    #name: String - the name of the .save file
    def check(self,name):
        return os.path.exists(self.getPath(name))

    #saves a name.save file
    #name: String - the name of the .save file
    def save(self,name):
        if not self.check(name):
        	f=open(self.getPath(name),'w')
        	f.close()

    #deletes a .save file
    #name: String - the name of the .save file
    def delete(self,name):
        if self.check(name):
            os.remove(self.getPath(name))

