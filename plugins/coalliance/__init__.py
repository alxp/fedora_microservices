'''
Created on March 5, 2011

@author: jonathangreen
'''

from plugin_manager import IslandoraListenerPlugin
from fcrepo.connection import FedoraConnectionException
from coalliance_mime import CoallianceMime as CM
from coalliance_conversion import CoallianceConversion

class coalliance(IslandoraListenerPlugin):

    def fedoraMessage(self, message, obj, client):
        if message['dsid']:
            CC = CoallianceConversion(obj, message['dsid'], logger)
            try:
                # do actions based on DSID then on MIME
                if message['dsid'] == 'MODS': 
                    pass
                #    CC.add_handle_to_mods(obj['MODS'])
                else: 
                    CM.dispatch(obj, message['dsid'], CC)
                
            except FedoraConnectionException:
                self.logger.warning('Object %s does not exist.' % obj.pid)

    def islandoraMessage(self, method, message, client):
        pass
        
