'''
Created on March 5, 2011

@author: jonathangreen
'''

from curl_fedora import get_datastream_as_file, update_datastream
from shutil import rmtree
from datetime import datetimefrom 
import fedora_relationships as frel
from lxml import etree
import os
import subprocess
import string
import types
import pprint

class CoallianceConversion():

    # thumbnail constants
    tn_postfix = '-tn.jpg'
    tn_size = (150, 200)

    def __init__(self, obj, dsid, logger):
        self.obj = obj
        self.dsid = dsid
        self.logger = logger
        self.relsint = frel.rels_int(obj, frel.rels_namespace('coal','http://www.coalliance.org/ontologies/relsint'), 'coal')
        self.relationships = rels.getRelationships()
        self.pp = pprint.PrettyPrint(index=4)

    # general derivative function
    def create_derivative(self, relationship, postfix, function):

        # get existing relationships
        relationships = self.relsint.getRelationships(subject=self.dsid, predicate=relationship)

        # see if we need a derivative
        if relationships:
            # the way we structure the relsint nothing should have more then one relationship of the same type
            if(len(relationships) > 1):
                self.logger.warning("Multiple relationships with same subject and predicate. Using first. Pid:%s Dsid: %s" % self.obj.pid, self.dsid)
            # get the dsid of the relation
            did = relationships[0][2].data
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
'''
    def create_thumbnail(self, obj, dsid, tnid):
        # We receive a file and create a jpg thumbnail
        directory, file = get_datastream_as_file(obj, dsid, "tmp")
        
        # Make a thumbnail with convert
        r = subprocess.call(['convert', directory+'/'+file+'[0]', '-colorspace', 'rgb', '-thumbnail', \
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
            self.logger.warning('PID:%s DSID:%s Thumbnail creation failed (return code:%d).' % (obj.pid, dsid, r))
            #if 'TN' not in obj:
            #    for ds in obj:
            #        print ds
            #    update_datastream(obj, 'TN', directory+'/'+tnid, label=obj[dsid].mimeType, mimeType='image/jpeg')
            #elif (obj[dsid].mimeType.split('/')[0] == 'image') and (obj['TN'].label.split('/')[0] != 'image'): 
            #    update_datastream(obj, 'TN', directory+'/'+tnid, label=obj[dsid].mimeType, mimeType='image/jpeg')
           
        self.logger.debug(directory)
        self.logger.debug(file)
        self.logger.debug(tnid)
        self.logger.debug(os.listdir(directory))

        rmtree(directory, ignore_errors=True)
        return r

    def create_jp2(self, obj, dsid, jp2id):
        # We receive a TIFF and create a Lossless JPEG 2000 file from it.
        directory, file = get_datastream_as_file(obj, dsid, 'tiff') 
        r = subprocess.call(["convert", directory+'/'+file, '+compress', directory+'/uncompressed.tiff'])
        if r != 0:
            self.logger.warning('PID:%s DSID:%s JP2 creation failed (convert return code:%d).' % (obj.pid, dsid, r))
            rmtree(directory, ignore_errors=True)
            return r;
        r = subprocess.call(["kdu_compress", "-i", directory+'/uncompressed.tiff', 
          "-o", directory+"/tmpfile_lossy.jp2",\
          "-rate", "0.5", "Clayers=1", "Clevels=7",\
          "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}",\
          "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
        if r != 0:
            self.logger.warning('PID:%s DSID:%s JP2 creation failed. Trying alternative.' % (obj.pid, dsid))
          r = subprocess.call(["convert", directory+'/'+file, '-compress', 'JPEG2000', '-quality', '50%', directory+'/tmpfile_lossy.jp2'])
            if r != 0:
                self.logger.warning('PID:%s DSID:%s JP2 creation failed (kdu_compress return code:%d).' % (obj.pid, dsid, r))

        if r == 0:
            update_datastream(obj, jp2id, directory+'/tmpfile_lossy.jp2', label='Compressed JPEG2000', mimeType='image/jp2')

        rmtree(directory, ignore_errors=True)
        return r

    def create_mp3(self, obj, dsid, mp3id):
        # We recieve a WAV file. Create a MP3
        directory, file = get_datastream_as_file(obj, dsid, "wav")
        
        # Make MP3 with lame
        r = subprocess.call(['lame', '-mm', '--cbr', '-b48', directory+'/'+file, directory+'/'+mp3id])
        if r == 0:
          update_datastream(obj, mp3id, directory+'/'+mp3id, label='compressed to mp3', mimeType='audio/mpeg')
        else:
          self.logger.warning('PID:%s DSID:%s MP3 creation failed (lame return code:%d).' % (obj.pid, dsid, r))

        rmtree(directory, ignore_errors=True)
        return r

    def create_ogg(self, obj, dsid, oggid):
        #recieve a wav file create a OGG
        directory, file = get_datastream_as_file(obj, dsid, "wav")
        
        # Make OGG with ffmpeg
        r = subprocess.call(['ffmpeg', '-i', directory+'/'+file, '-acodec', 'libvorbis', '-ab', '48k', directory+'/'+oggid])
        if r == 0:
            update_datastream(obj, oggid, directory+'/'+oggid, label='compressed to ogg', mimeType='audio/ogg')
        else:
            self.logger.warning('PID:%s DSID:%s OGG creation failed (ffmpeg return code:%d).' % (obj.pid, dsid, r))
        rmtree(directory, ignore_errors=True)
        return r

    def create_swf(self, obj, dsid, swfid):
        #recieve PDF create a SWF for use with flexpaper
        directory, file = get_datastream_as_file(obj, dsid, "pdf")
        
        r = subprocess.call(['pdf2swf', directory+'/'+file, '-o', directory+'/'+swfid,\
             '-T 9', '-f', '-t', '-s', 'storeallcharacters', '-G'])
        if r != 0:
            self.logger.warning('PID:%s DSID:%s SWF creation failed. Trying alternative.' % (obj.pid, dsid))
            r = subprocess.call(['pdf2swf', directory+'/'+file, '-o', directory+'/'+swfid,\
                 '-T 9', '-f', '-t', '-s', 'storeallcharacters', '-G', '-s', 'poly2bitmap'])
            if r != 0:
                self.logger.warning('PID:%s DSID:%s SWF creation failed (pdf2swf return code:%d).' % (obj.pid, dsid, r))

        if r == 0:
            update_datastream(obj, swfid, directory+'/'+swfid, label='pdf to swf', mimeType='application/x-shockwave-flash')

        rmtree(directory, ignore_errors=True)
        return r

    def check_dates(self, obj, dsid, derivativeid):
        date = datetime.strptime( obj[dsid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )
        derdate = datetime.strptime( obj[derivativeid].createdDate, '%Y-%m-%dT%H:%M:%S.%fZ' )

        if date > derdate:
            return True
        else:
            return False
'''
