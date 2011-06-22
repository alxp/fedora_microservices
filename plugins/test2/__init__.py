'''
Created on March 5, 2011

@author: jonathangreen
'''

from plugin_manager import IslandoraListenerPlugin

class test2(IslandoraListenerPlugin):
    
    def islandoraMessage(self, method, message, client):
        print method
        print message

    def fedoraMessage(self, method, pid, obj, client, message):
        print pid
        print obj
        print message
