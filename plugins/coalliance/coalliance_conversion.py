'''
Created on March 5, 2011

@author: jonathangreen
'''

# These will appear in an IDE as broken dependencies.
# This is OK because they live in the plugins folder but are invoked in the app's main folder
# by the plugin manager
from curl_fedora import get_datastream_as_file, update_datastream
from shutil import rmtree
from datetime import datetime
from fedora_relationships import rels_int
from lxml import etree
import os, subprocess, string, httplib, re, random, types

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
