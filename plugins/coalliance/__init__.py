'''
Created on March 5, 2011

@author: jonathangreen
'''

from islandoraUtils.metadata.fedora_relationships import rels_int, rels_namespace
from plugin_manager import IslandoraListenerPlugin
from fcrepo.connection import FedoraConnectionException
from coalliance_mime import CoallianceMime
import coalliance_metadata
import coalliance_policy

class coalliance(IslandoraListenerPlugin):

    def processMessage(self, dsid, obj, comime):
        try:
            # do actions based on DSID then on MIME
            if dsid == 'MODS': 
                coalliance_metadata.add_handle_to_mods(obj)
            elif dsid == 'TN':
                pass
            #elif dsid == 'POLICY':
            #    coalliance_policy.process(obj)
            else:
                comime.dispatch(dsid)
                
        except FedoraConnectionException:
            self.logger.warning('Object %s does not exist.' % obj.pid)

    def fedoraMessage(self, message, obj, client):
        # if this is a ingest method, then we want to do actions for each datastream
        comime = CoallianceMime(obj, message)
        if message['method'] == 'ingest':
            for dsid in obj:
                self.processMessage(dsid, obj, comime)
        # clean up the rels if this was a purge
        elif message['method'] == 'purgeDatastream':
            relsint = rels_int(obj, rels_namespace('coal', 'http://www.coalliance.org/ontologies/relsint'), 'coal')
            relsint.purgeRelationships(subject=message['dsid'])
            relsint.purgeRelationships(object=message['dsid'])
            relsint.update()
        # else we just mess with the one that was changed
        elif message['dsid']:
            self.processMessage(message['dsid'], obj, comime)
         
    def islandoraMessage(self, method, message, client):
        pass
        
