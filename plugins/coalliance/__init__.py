'''
Created on March 5, 2011

@author: jonathangreen
'''

from plugin_manager import IslandoraListenerPlugin
from fcrepo.connection import FedoraConnectionException
from coalliance_conversion import CoallianceConversion
from coalliance_mime import CoallianceMime

class coalliance(IslandoraListenerPlugin):

    def fedoraMessage(self, message, obj, client):
        try:
            # do actions based on DSID then on MIME
            if self.dsid == 'MODS': 
                CoallianceConversion.add_handle_to_mods(obj['MODS'])
            else: 
                CoallianceMime.dispatch(obj,message)
                
        except FedoraConnectionException:
            self.logger.warning('Object %s does not exist.' % obj.pid)

    def islandoraMessage(self, method, message, client):
        pass
        
