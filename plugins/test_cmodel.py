'''
Created on March 5, 2011

@author: jonathangreen
'''

from plugin_manager import IslandoraListenerPlugin

class test_cmodel(IslandoraListenerPlugin):
    name = "Jon Stomp Demo"
    content_model =  ['demo:testCModel']

    def runRules(self, obj, dsid, body):
        print 'Got here!'

    def islandoraMessage(self, method, message, client):
        print 'woot'
