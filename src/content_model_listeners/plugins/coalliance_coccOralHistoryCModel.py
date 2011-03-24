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
from fedorarelsint import RELSINTDatastream
from fcrepo.utils import NS
from fcrepo.connection import FedoraConnectionException
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
      return False

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
   
    if r == 0:
        update_datastream(obj, tnid, directory+'/'+tnid, label='thumbnail', mimeType='image/jpeg')

        # this is necessary because we are using curl, and the library caches 
        try:
            if (obj['TN'].label.split('/')[0] != 'image'): 
                if(obj[dsid].mimeType.split('/')[0] == 'image'):
                    update_datastream(obj, 'TN', directory+'/'+tnid, label=obj[dsid].mimeType, mimeType='image/jpeg')
        except FedoraConnectionException:
            update_datastream(obj, 'TN', directory+'/'+tnid, label=obj[dsid].mimeType, mimeType='image/jpeg')

        #if 'TN' not in obj:
        #    for ds in obj:
        #        print ds
        #    update_datastream(obj, 'TN', directory+'/'+tnid, label=obj[dsid].mimeType, mimeType='image/jpeg')
        #elif (obj[dsid].mimeType.split('/')[0] == 'image') and (obj['TN'].label.split('/')[0] != 'image'): 
        #    update_datastream(obj, 'TN', directory+'/'+tnid, label=obj[dsid].mimeType, mimeType='image/jpeg')
       
    logging.debug(directory)
    logging.debug(file)
    logging.debug(tnid)
    logging.debug(os.listdir(directory))

    rmtree(directory, ignore_errors=True)

def create_jp2(obj, dsid, jp2id):
    # We receive a TIFF and create a Lossless JPEG 2000 file from it.
    directory, file = get_datastream_as_file(obj, dsid, 'tiff') 
    r = subprocess.call(["convert", directory+'/'+file, '+compress', directory+'/uncompressed.tiff'])
    r = subprocess.call(["kdu_compress", "-i", directory+'/uncompressed.tiff', 
      "-o", directory+"/tmpfile_lossy.jp2",\
      "-rate", "0.5", "Clayers=1", "Clevels=7",\
      "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}",\
      "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
    if r == 0:
        update_datastream(obj, jp2id, directory+'/tmpfile_lossy.jp2', label='Compressed JPEG2000', mimeType='image/jp2')

    rmtree(directory, ignore_errors=True)

def create_mp3(obj, dsid, mp3id):
    # We recieve a WAV file. Create a MP3
    directory, file = get_datastream_as_file(obj, dsid, "wav")
    
    # Make MP3 with lame
    r = subprocess.call(['lame', '-mm', '--cbr', '-b48', directory+'/'+file, directory+'/'+mp3id])
    if r == 0:
      update_datastream(obj, mp3id, directory+'/'+mp3id, label='compressed to mp3', mimeType='audio/mpeg')

    #rmtree(directory, ignore_errors=True)

def create_ogg(obj, dsid, oggid):
    #recieve a wav file create a OGG
    directory, file = get_datastream_as_file(obj, dsid, "wav")
    
    # Make OGG with ffmpeg
    r = subprocess.call(['ffmpeg', '-i', directory+'/'+file, '-acodec', 'libvorbis', '-ab', '48k', directory+'/'+oggid])
    if r == 0:
        update_datastream(obj, oggid, directory+'/'+oggid, label='compressed to ogg', mimeType='audio/ogg')
    rmtree(directory, ignore_errors=True)

def create_swf(obj, dsid, swfid):
    #recieve PDF create a SWF for use with flexpaper
    directory, file = get_datastream_as_file(obj, dsid, "pdf")
    
    r = subprocess.call(['pdf2swf', directory+'/'+file, '-o', directory+'/'+swfid, '-T 9', '-f'])
    if r == 0:
        update_datastream(obj, swfid, directory+'/'+swfid, label='pdf to swf', mimeType='application/x-shockwave-flash')
    rmtree(directory, ignore_errors=True)

def check_dates(obj, dsid, derivativeid):
    date = datetime.strptime( obj[dsid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )
    derdate = datetime.strptime( obj[derivativeid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )

    if date > derdate:
        return True
    else:
        return False

class coalliance_coccOralHistoryCModel(FedoraMicroService):
    name = "Coalliance Oral History Cmodel"
    content_model = "coalliance:ADRBasicModel"

    # general derivative function
    def create_derivative(self, relationship, postfix, function):
        # see if we need a derivative
        if relationship in self.relationships:
            did = self.relationships[relationship][0]
            try:
                if check_dates(self.obj, self.dsid, did):
                    function(self.obj, self.dsid, did)
            except FedoraConnectionException:
                function(self.obj, self.dsid, did)
        else:
            did = self.dsid.rsplit('.', 1)[0]
            did += postfix
            function(self.obj, self.dsid, did)
            self.relsint.addRelationship(self.dsid, relationship, did) 
            self.relsint.update()

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
    def mimetype_dispatch(self):
        # translate - / + . into _ for the mimetype function
        trantab = string.maketrans('-/+.','____')
        mime =  self.obj[self.dsid].mimeType.encode('ascii')
        mime_function_name = mime.translate(trantab)
        # get the function from the self object and run it
        mime_function = getattr( self, mime_function_name, self.mimetype_none )
        mime_function()

    def runRules(self, obj, dsid, body):
 
        self.obj = obj
        self.dsid = dsid
        self.relsint = RELSINTDatastream(obj)
        self.relationships = self.relsint.getRelationships(dsid)

        # work on the files based on mimetype
        self.mimetype_dispatch()

        #TODO
        #handle MODS handle stuff 

    def __init__(self):
        '''
        Constructor
        '''
        
