'''
Created on March 5, 2011

@author: jonathangreen
'''

# These will appear in an IDE as broken dependencies.
# This is OK because they live in the plugins folder but are invoked in the app's main folder
# by the plugin manager
from plugin_manager import IslandoraListenerPlugin
from categories import get_datastream_as_file, update_datastream
from shutil import rmtree
from datetime import datetime
from fedorarelsint import RELSINTDatastream
from fcrepo.utils import NS
from fcrepo.connection import FedoraConnectionException
from lxml import etree
import logging, os, subprocess, string, httplib, re, random, types

class CoallianceMime():

    # functions need to be defined for each mimetype to be worked on
    def application_pdf(self):
        self.create_derivative('hasThumbnail', tn_postfix, create_thumbnail)
        self.create_derivative('hasSWF', '.swf', create_swf)

    def image_jpeg(self):
        # since thumnails are JPGs make sure we aren't recursing
        if (not self.dsid.endswith(tn_postfix)) and self.dsid != 'TN':
            self.create_derivative('hasThumbnail', tn_postfix, create_thumbnail)

    def image_tiff(self):
        self.create_derivative('hasThumbnail', tn_postfix, create_thumbnail)
        self.create_derivative('hasJP2', '.jp2', create_jp2)

    def audio_x_wav(self):
        #TODO
        # deal with datastreams that already have .mp3 in format
        # original: namem#.wav
        # derived: name#.mp3
        self.create_derivative('hasMP3', '.mp3', create_mp3)
        self.create_derivative('hasOGG', '.ogg', create_ogg)

    # mimetype isn't found, do nothing
    def mimetype_none(self):
      pass

    # this is a simple dispatcher that will run functions based on mimetype
    def dispatch(self):
        try:
            # translate - / + . into _ for the mimetype function
            trantab = string.maketrans('-/+.','____')
            mime =  self.obj[self.dsid].mimeType.encode('ascii')
            mime_function_name = mime.translate(trantab)
            # get the function from the self object and run it
            mime_function = getattr( self, mime_function_name, self.mimetype_none )
            mime_function()
        except KeyError:
            # we catch a key error because .mimeType throws one 
            # if no mimeType is defined 
            return; 
