
from islandoraUtils import DSConverter as DSC
from plugin_manager import IslandoraListenerPlugin
import pprint

BINARY_THUMB_LOCATION = u'http://icons.iconarchive.com/icons/mayosoft/aero-vista/128/System-Binary-icon.png'
AUDIO_THUMB_LOCATION = u'http://dg.jwa.org/sites/jwa.org/modules/islandora/islandora_JWA_module/images/TN.png'

class jwa_plugin(IslandoraListenerPlugin):

    def initialize(self, config_parser):
        # call the parent function (this just prints an init message to the logs
        # this is a good practice
        IslandoraListenerPlugin.initialize(self, config_parser)
        return True

    def fedoraMessage(self, message, obj, client):
        # Take a look at what content model we are dealing with
        # do some fun stuff based on this
        pp = pprint.PrettyPrinter(indent=4)        

        if 'jwa:audioCModel' in message['content_models']:
            if 'TN' not in obj:
               obj.addDataStream('TN', controlGroup=u'R', location=AUDIO_THUMB_LOCATION, \
                   mimeType=u'image/png')
        if 'jwa:imageCModel' in message['content_models'] and (message['dsid'] == 'ORIGINAL' or message['method'] == 'ingest'):
            DSC.create_jp2(obj, 'ORIGINAL', 'JP2')
            DSC.create_thumbnail(obj, 'ORIGINAL', 'TN')
        if 'jwa:documentCModel' in message['content_models'] and (message['dsid'] == 'ORIGINAL' or message['method'] == 'ingest'):
            if obj['ORIGINAL'].mimeType == 'application/pdf':
                DSC.create_swf(obj, 'ORIGINAL', 'FLEXPAPER')
                DSC.create_thumbnail(obj, 'ORIGINAL', 'TN')
            else:
                r = DSC.create_pdf(obj, 'ORIGINAL', 'PDF')
                if r == 0:
                    DSC.create_thumbnail(obj, 'PDF', 'TN')
                    DSC.create_swf(obj, 'PDF', 'FLEXPAPER')
                else:
                    obj.addDataStream('TN', controlGroup=u'R', location=BINARY_THUMB_LOCATION, \
                        mimeType=u'image/png')

    def islandoraMessage(self, method, message, client):
        pass        
