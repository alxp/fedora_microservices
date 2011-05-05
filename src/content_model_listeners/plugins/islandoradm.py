'''
Created on Dec 1, 2010

@author: jesterhazy
'''
import subprocess
import string
from categories import FedoraMicroService
from categories import get_datastream_as_file, update_datastream
import os, tempfile
from shutil import rmtree
import logging, os

abby_home = '/usr/local/ABBYYData/FRE80_M5_Linux_part_498-28_build_8-1-0-7030/Samples/CLI/'
kdu_compress = '/usr/local/bin/kdu_compress'
convert = '/usr/bin/convert'

def sysout(msg, end='\n'):
    sys.stdout.write(str(msg) + end)

def make_jp2(tiff_file):
    logging.debug([kdu_compress, "-i", tiff_file, "-o", "tmp.jp2", "-rate", "0.5", "Clayers=1", "Clevels=7", "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])

    return 0 == subprocess.call([kdu_compress, "-i", tiff_file, "-o", "tmp.jp2", "-rate", "0.5", "Clayers=1", "Clevels=7", "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
    
def make_jp2_lossless(tiff_file):
    return 0 == subprocess.call([kdu_compress, "-i", tiff_file, "-o", "tmp_lossless.jp2", "-rate", "-,0.5", "Clayers=2", "Creversible=yes", "Clevels=8", "Cprecincts={256,256},{256,256},{128,128}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}"])

def make_tn(tiff_file):
    # would like 85x110^ instead of 85x110!, but need imagemagick upgrade first ( >= 6.3.8-2)
    return 0 == subprocess.call([convert, tiff_file, "-thumbnail", "85x110!", "-gravity", "center", "-extent", "85x110", "tmp.jpg"])
    
def make_ocr(directory, tiff_file):
    global abby_home
    os.chdir(abby_home)
    return 0 == subprocess.call(["./CLI", "-ics", "-if", "%(dir)s/%(file)s" % {'dir': directory, 'file': tiff_file}, 
        "-f", "PDF", "-pem", "ImageOnText", "-pfpf", "Automatic", "-pfq", "90", "-pfpr", "150", "-of", "%(dir)s/tmp.pdf" % {'dir': directory}, 
        "-f", "XML", "-xaca", "-of", "%(dir)s/tmp.xml" % {'dir': directory}, 
        "-f", "Text", "-tel", "-tet", "UTF8", "-of", "%(dir)s/tmp.txt" % {'dir': directory}])

def run_conversions(obj, tmpdir, tiff_file):
    if not make_tn(tiff_file):
        logging.error("error creating thumbnail for " + obj.pid)
        return False

    logging.debug("finished jpg for " + obj.pid)
    
    if not make_jp2(tiff_file):
        logging.error("error creating jp2 for " + obj.pid)
        return False
    
    logging.debug("finished jp2 lossy for " + obj.pid)
    
    if not make_jp2_lossless(tiff_file):
        logging.error("error creating lossless jp2 for " + obj.pid)
        return False
    
    logging.debug("finished jp2 lossless for " + obj.pid)
    
    if not make_ocr(tmpdir, tiff_file):
        logging.error("error creating ocr output for " + obj.pid)
        return False

    logging.debug("finished abbyy for " + obj.pid)
    
    return True

def update_fedora(obj, tmpdir):
    if not update_fedora_add_datastreams(obj, tmpdir):
        logging.error("error adding datastreams to " + obj.pid)
        return False

    if not update_fedora_relsext(obj):
        logging.error("error updating relationships for " + obj.pid)
        return False

    try:
        del obj['tiff']
    except Exception as e:
        logging.error("error removing tiff datastream from pid " + obj.pid + " - " + str(e))
        return False
    
    return True

def update_fedora_relsext(obj):
    try:
        ds = obj['RELS-EXT']

        xmlstring = ds.getContent().read()
        logging.debug('before rdf: ' + xmlstring)

        # treating xml as text, because fcrepo ops add weird namespaces, 
        # and no DOM modules are available
        lines = [line for line in string.split(xmlstring, '\n') if line.find('islandora-dm:purchase-orders-incomplete-import') < 0]
        updated_xml_string = string.join(lines, '\n')

        logging.debug('after rdf: ' + updated_xml_string)

        ds.setContent(updated_xml_string)
    except Exception as e:
        logging.error("exception: " + str(e))
        return False
        
    return True

def update_fedora_add_datastreams(obj, tmpdir):
    return (update_datastream(obj, 'tn', tmpdir + '/tmp.jpg', 'thumbnail image', 'image/jpeg') and
            update_datastream(obj, 'jp2', tmpdir + '/tmp.jp2', 'jp2 image', 'image/jp2') and
            update_datastream(obj, 'jp2lossless', tmpdir + '/tmp_lossless.jp2', 'jp2 image (lossless)', 'image/jp2') and
            update_datastream(obj, 'xml', tmpdir + '/tmp.xml', 'ocr xml', 'text/xml') and
            update_datastream(obj, 'text', tmpdir + '/tmp.txt', 'ocr text', 'text/plain') and
            update_datastream(obj, 'pdf', tmpdir + '/tmp.pdf', 'pdf', 'application/pdf'))

class IslandoraDM(FedoraMicroService):
    '''
    classdocs
    '''
    name = "Islandora DM Plugin"
    content_model = "islandora-dm:cmodel-page"
    def runRules(self, obj, dsid, body):
        logging.info("pid:" + obj.pid + ", dsid:" + dsid)

        # is this a reschedule request?
        if dsid == '' and body.find('reschedule import') >= 0:
            dsid = 'tiff'

        if dsid == 'tiff':
            try:
                tmpdir, tiff_file = get_datastream_as_file(obj, dsid, 'tiff')
            
                cwd = os.getcwd()
                os.chdir(tmpdir)
                        
                run_conversions(obj, tmpdir, tiff_file) and update_fedora(obj, tmpdir)
                
                rmtree(tmpdir, ignore_errors=True)
            except Exception as e:
                logging.error("an exception occurred: " + str(e))
                
            os.chdir(cwd)
        else:
            logging.debug("ignoring dsid: " + dsid)

    def __init__(self):
        '''
        Constructor
        '''
