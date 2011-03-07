'''
Created on March 5, 2011

@author: jonathangreen
'''

# These will appear in an IDE as broken dependencies.
# This is OK because they live in the plugins folder but are invoked in the app's main folder
# by the plugin manager
from categories import FedoraMicroService
from categories import get_datastream_as_file, update_datastream
from shutil import rmtree
from datetime import datetime
import logging, os, subprocess

tn_postfix = '-tn.jpg'
tn_size = (150, 200)

def create_thumbnail(obj, dsid, tnid):
    
    # We receive a TIFF and create a Lossless JPEG 2000 file from it.
    directory, file = get_datastream_as_file(obj, dsid, "tmp")
    
    # Make a thumbnail with convert
    r = subprocess.call(['convert', directory+'/'+file+'[0]', '-thumbnail', \
         '%sx%s' % (tn_size[0], tn_size[1]), directory+'/'+tnid])
   
    update_datastream(obj, tnid, directory+'/'+tnid, label='thumbnail', mimeType='image/jpeg')
   
    logging.debug(directory)
    logging.debug(file)
    logging.debug(tnid)
    logging.debug(os.listdir(directory))

    rmtree(directory, ignore_errors=True)

#returns the name of the thumbnail id if needed
def test_thumbnail(obj, dsid):

    # test if this is already a thumbnail
    if dsid.endswith(tn_postfix):
        return ''

    #test if a thumbnail exists
    tndsid = dsid.rsplit('.', 1)[0]
    tndsid += tn_postfix
    
    #test if it was created after
    if tndsid in obj:
        date = datetime.strptime( obj[dsid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )
        tndate = datetime.strptim( obj[tndsid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )
        if( date < tndate ):
            return ''

    #need thumbnail
    return tndsid


class coalliance_coccOralHistoryCModel(FedoraMicroService):
    '''
    classdocs
    '''
    name = "Coalliance Oral History Cmodel"
    content_model = "coalliance:coccOralHistoryCModel"

    #functions need to be defined for each mimetype to be worked on

    def application_pdf(self, obj, dsid):
        tnid = test_thumbnail(obj, dsid)
        if tnid:
            create_thumbnail(obj, dsid, tnid)

    def image_jpeg(self, obj, dsid):
        tnid = test_thumbnail(obj, dsid)
        if tnid:
            create_thumbnail(obj, dsid, tnid)

    # mimetype isn't found, do nothing
    def mimetype_none(self, obj, dsid):
      pass

    def mimetype_dispatch(self, obj, dsid):
        # this is a simple dispatcher that will run functions based on mimetype
        mime_function = getattr( self, obj[dsid].mimeType.replace('/','_'), self.mimetype_none )
        mime_function(obj, dsid)

    def runRules(self, obj, dsid, body):
        # work on the files based on mimetype
        self.mimetype_dispatch(obj, dsid)

    def __init__(self):
        '''
        Constructor
        '''
        
