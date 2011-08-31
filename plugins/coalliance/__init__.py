'''
Created on March 5, 2011

@author: jonathangreen
'''

from plugin_manager import IslandoraListenerPlugin
from fcrepo.connection import FedoraConnectionException
import coalliance_conversion as CC
from coalliance_mime import CoallianceMime as CM

class coalliance(IslandoraListenerPlugin):

    def fedoraMessage(self, message, obj, client):
        if message['dsid']:
            try:
                # do actions based on DSID then on MIME
                if message['dsid'] == 'MODS': 
                    CC.add_handle_to_mods(obj['MODS'])
                else: 
                    CM.dispatch(obj,message['dsid'])
                
            except FedoraConnectionException:
                self.logger.warning('Object %s does not exist.' % obj.pid)

    def islandoraMessage(self, method, message, client):
        pass
        
