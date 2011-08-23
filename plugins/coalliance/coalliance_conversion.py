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

# thumbnail constants
tn_postfix = '-tn.jpg'
tn_size = (150, 200)

#handle constants
handleServer='damocles.coalliance.org'
handleServerPort='9080'
handleServerApp='/handles/handle.jsp?'

def mangle_dsid(dsid):
    find = '[^a-zA-Z0-9\.\_\-]';
    replace = '';
    dsid = re.sub(find, replace, dsid)

    if( len(dsid) > 64 ):
        dsid = dsid[-64:]

    if( len(dsid) > 0 and not dsid[0].isalpha() ):
        letter = random.choice(string.letters)
        if( len(dsid) == 64 ):
            dsid = letter+dsid[1:]
        else:
            dsid = letter+dsid

    if( dsid == '' ):
        for i in range(10):
            dsid += random.choice(string.letters)

    return dsid

def get_handle(obj):
    try:
      conn = httplib.HTTPConnection(handleServer,handleServerPort,timeout=10)
      conn.request('GET', handleServerApp+'debug=true&adr3=true&pid='+obj.pid)
      res = conn.getresponse()
    except:
      logging.error("Error connecting to Handle Server. PID: %s." % (obj.pid))
      return False

    # convert the response to lowercase and see if it contains success
    text = string.lower(res.read())

    if ( string.find(text,'==>success') != -1 ):
        logging.info("Successfuly created handle for %s." % obj.pid)
        return True
    else:
        logging.info("Failed to create handle for %s." % obj.pid)
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
    else :
        logging.warning('PID:%s DSID:%s Thumbnail creation failed (return code:%d).' % (obj.pid, dsid, r))
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
    return r

def create_jp2(obj, dsid, jp2id):
    # We receive a TIFF and create a Lossless JPEG 2000 file from it.
    directory, file = get_datastream_as_file(obj, dsid, 'tiff') 
    r = subprocess.call(["convert", directory+'/'+file, '+compress', directory+'/uncompressed.tiff'])
    if r != 0:
        logging.warning('PID:%s DSID:%s JP2 creation failed (convert return code:%d).' % (obj.pid, dsid, r))
        rmtree(directory, ignore_errors=True)
        return r;
    r = subprocess.call(["kdu_compress", "-i", directory+'/uncompressed.tiff', 
      "-o", directory+"/tmpfile_lossy.jp2",\
      "-rate", "0.5", "Clayers=1", "Clevels=7",\
      "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}",\
      "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
    if r != 0:
        logging.warning('PID:%s DSID:%s JP2 creation failed. Trying alternative.' % (obj.pid, dsid))
    	r = subprocess.call(["convert", directory+'/'+file, '-compress', 'JPEG2000', '-quality', '50%', directory+'/tmpfile_lossy.jp2'])
        if r != 0:
            logging.warning('PID:%s DSID:%s JP2 creation failed (kdu_compress return code:%d).' % (obj.pid, dsid, r))

    if r == 0:
        update_datastream(obj, jp2id, directory+'/tmpfile_lossy.jp2', label='Compressed JPEG2000', mimeType='image/jp2')

    rmtree(directory, ignore_errors=True)
    return r

def create_mp3(obj, dsid, mp3id):
    # We recieve a WAV file. Create a MP3
    directory, file = get_datastream_as_file(obj, dsid, "wav")
    
    # Make MP3 with lame
    r = subprocess.call(['lame', '-mm', '--cbr', '-b48', directory+'/'+file, directory+'/'+mp3id])
    if r == 0:
      update_datastream(obj, mp3id, directory+'/'+mp3id, label='compressed to mp3', mimeType='audio/mpeg')
    else:
      logging.warning('PID:%s DSID:%s MP3 creation failed (lame return code:%d).' % (obj.pid, dsid, r))

    rmtree(directory, ignore_errors=True)
    return r

def create_ogg(obj, dsid, oggid):
    #recieve a wav file create a OGG
    directory, file = get_datastream_as_file(obj, dsid, "wav")
    
    # Make OGG with ffmpeg
    r = subprocess.call(['ffmpeg', '-i', directory+'/'+file, '-acodec', 'libvorbis', '-ab', '48k', directory+'/'+oggid])
    if r == 0:
        update_datastream(obj, oggid, directory+'/'+oggid, label='compressed to ogg', mimeType='audio/ogg')
    else:
        logging.warning('PID:%s DSID:%s OGG creation failed (ffmpeg return code:%d).' % (obj.pid, dsid, r))
    rmtree(directory, ignore_errors=True)
    return r

def create_swf(obj, dsid, swfid):
    #recieve PDF create a SWF for use with flexpaper
    directory, file = get_datastream_as_file(obj, dsid, "pdf")
    
    r = subprocess.call(['pdf2swf', directory+'/'+file, '-o', directory+'/'+swfid,\
         '-T 9', '-f', '-t', '-s', 'storeallcharacters', '-G'])
    if r != 0:
        logging.warning('PID:%s DSID:%s SWF creation failed. Trying alternative.' % (obj.pid, dsid))
        r = subprocess.call(['pdf2swf', directory+'/'+file, '-o', directory+'/'+swfid,\
             '-T 9', '-f', '-t', '-s', 'storeallcharacters', '-G', '-s', 'poly2bitmap'])
        if r != 0:
            logging.warning('PID:%s DSID:%s SWF creation failed (pdf2swf return code:%d).' % (obj.pid, dsid, r))

    if r == 0:
        update_datastream(obj, swfid, directory+'/'+swfid, label='pdf to swf', mimeType='application/x-shockwave-flash')

    rmtree(directory, ignore_errors=True)
    return r

def check_dates(obj, dsid, derivativeid):
    date = datetime.strptime( obj[dsid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )
    derdate = datetime.strptime( obj[derivativeid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )

    if date > derdate:
        return True
    else:
        return False

class coalliance_cmodel(FedoraMicroService):
    name = "Coalliance Oral History Cmodel"
    content_model =  ['codearl:codearlBasicObject', 'coccc:cocccBasicObject', 'cog:cogBasicObject', 'cogru:cogruBasicObject', 'wyu:wyuBasicObject', 'codu:coduBasicObject', 'codr:codrBasicObject', 'cogjm:cogjmBasicObject', 'co:coBasicObject', 'cowjcpl:cowjcplBasicObject', 'gopig:gopigBasicObject', 'coccc:cocccBasicETD', 'cog:cogBasicETD', 'cogru:cogruBasicETD', 'wyu:wyuBasicETD', 'codu:coduBasicETD', 'codr:codrBasicETD', 'cogjm:cogjmBasicETD', 'codr:codrBasicVRA', 'co:coPublications', 'codearl:coPublications']

    # general derivative function
    def create_derivative(self, relationship, postfix, function):
        # see if we need a derivative
        if relationship in self.relationships:
            did = self.relationships[relationship][0]
            if( did != mangle_dsid(did) ):
                logging.warning("DSID mismatch Pid:%s Dsid:%s" % (self.obj.pid, self.dsid))
            try:
                if check_dates(self.obj, self.dsid, did):
                    function(self.obj, self.dsid, did)
            except FedoraConnectionException:
                function(self.obj, self.dsid, did)
        else:
            did = self.dsid.rsplit('.', 1)[0]
            did += postfix
            did = mangle_dsid(did)
            r = function(self.obj, self.dsid, did)
            if( r == 0 ):
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

    def runRules(self, obj, dsid, body):
 
        self.obj = obj
        self.dsid = dsid
        try:
            if dsid == 'MODS':
                # some functions use the wrong namespace 
                # determine what to use
                mods_namespace = '{http://www.loc.gov/mods/v3}'

                parser = etree.XMLParser(remove_blank_text=True)
                root = etree.fromstring(obj['MODS'].getContent().read(), parser)

                ns = None

                for k in root.nsmap:
                    if(type(k) == types.StringType and k.lower().find('mods') != -1):
                        ns = '{%s}' % root.nsmap[k]

                if ns == None:
                    ns = mods_namespace

                url = root.find(ns+'location/'+ns+'url')
                if(url == None and get_handle(obj)):
                    location = root.find(ns+'location')
                    if(location == None):
                        location = etree.SubElement(root, ns+'location')
                    url = etree.SubElement(location, ns+'url')
                    url.attrib['usage']='primary display'
                    url.text = 'http://hdl.handle.net/10176/'+obj.pid
                    obj['MODS'].setContent(etree.tostring(root, pretty_print=True))
            else:
                self.relsint = RELSINTDatastream(obj)
                self.relationships = self.relsint.getRelationships(dsid)
                self.mimetype_dispatch()

            #TODO
            #handle MODS handle stuff 
        except FedoraConnectionException:
            logging.warning('Object %s does not exist.' % obj.pid)
            

class coalliance(IslandoraListenerPlugin):

    def fedoraMessage(self, message, obj, client):

        try:
            # do actions based on DSID then on MIME
            if self.dsid == 'MODS': 
                coalliance_conversions.add_handle_to_mods(obj['MODS'])
            else: 
                coalliance_mime.dispatch(obj,message)
                
        except FedoraConnectionException:
            self.logger.warning('Object %s does not exist.' % obj.pid)

    def islandoraMessage(self, method, message, client):
        pass
        
