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
import logging, os, subprocess, string, httplib

# thumbnail constants
tn_postfix = '-tn.jpg'
tn_size = (150, 200)

#handle constants
handleServer='sword.coalliance.org'
handleServerPort='9080'
handleServerApp='/handles/handles.jsp?'

def get_handle(obj):
    try:
      conn = httplib.HTTPConnection(handleServer,handleServerPort,timeout=10)
      conn.request('GET', handleServerApp+'debug=true&pid='+obj.pid)
      res = conn.getresponse()
    except:
      logging.error("Error Connecting")
      return False;

    # convert the response to lowercase and see if it contains success
    text = string.lower(res.read())

    if ( string.find(text,'success') != -1 ):
        return True
    else:
        return False

def create_thumbnail(obj, dsid, tnid):
    
    # We receive a file and create a jpg thumbnail
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

#returns the name of the object to create if needed
def object_needed(obj, dsid, postfix):

    # test if we are in an generated dsid
    if dsid.endswith(postfix):
        return ''

    #test if a thumbnail exists
    genid = dsid.rsplit('.', 1)[0]
    genid += postfix
    
    #test if it was created after
    if genid in obj:
        date = datetime.strptime( obj[dsid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )
        tndate = datetime.strptim( obj[genid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )
        if( date < tndate ):
            return ''

    #need thumbnail
    return genid


class coalliance_coccOralHistoryCModel(FedoraMicroService):
    '''
    classdocs
    '''
    name = "Coalliance Oral History Cmodel"
    content_model = "coalliance:coccOralHistoryCModel"

    #functions need to be defined for each mimetype to be worked on

    def application_pdf(self, obj, dsid):
        tnid = object_needed(obj, dsid, tn_postfix)
        if tnid:
            create_thumbnail(obj, dsid, tnid)

    def image_jpeg(self, obj, dsid):
        tnid = object_needed(obj, dsid, tn_postfix)
        if tnid:
            create_thumbnail(obj, dsid, tnid)

    def audio_x_wav(self, obj, dsid):
        genid = object_needed(obj, dsid, '.mp3')
        if genid:
            directory, file = get_datastream_as_file(obj, dsid, "wav")
            
            # Make MP3 with ffmpeg
            r = subprocess.call(['ffmpeg', '-i '+directory+'/'+file, '-ab 64k', directory+'/'+genid])
           
            update_datastream(obj, genid, directory+'/'+genid, label=dsid+'compressed to mp3', mimeType='audio/mpeg')
           
            rmtree(directory, ignore_errors=True)

    # mimetype isn't found, do nothing
    def mimetype_none(self, obj, dsid):
      pass

    # this is a simple dispatcher that will run functions based on mimetype
    def mimetype_dispatch(self, obj, dsid):
        # translate - / + . into _ for the mimetype function
        trantab = string.maketrans('-/+.','____')
        mime =  obj[dsid].mimeType.encode('ascii')
        mime_function_name = mime.translate(trantab)
        # get the function from the self object and run it
        mime_function = getattr( self, mime_function_name, self.mimetype_none )
        mime_function(obj, dsid)

    def runRules(self, obj, dsid, body):
        # work on the files based on mimetype
        self.mimetype_dispatch(obj, dsid)

    def __init__(self):
        '''
        Constructor
        '''
        
