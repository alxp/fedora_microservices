'''
Created on Dec 1, 2010

@author: jesterhazy
'''
from categories import FedoraMicroService
from categories import get_datastream_as_file, update_datastream
import os, tempfile
from shutil import rmtree
import logging, os

abby_home = '/usr/local/ABBYYData/FRE80_M5_Linux_part_498-28_build_8-1-0-7030/Samples/CLI/'

def sysout(msg, end='\n'):
    sys.stdout.write(str(msg) + end)

def make_jp2(directory, file):
    return 0 == subprocess.call(["kdu_compress", "-i", "tmp.tiff", "-o", "tmp.jp2", "-rate", "0.5", "Clayers=1", "Clevels=7", "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
    
def make_jp2_lossless(directory, file):
    return 0 == subprocess.call(["kdu_compress", "-i", "tmp.tiff", "-o", "tmp_lossless.jp2", "-rate", "-,0.5", "Clayers=2", "Creversible=yes", "Clevels=8", "Cprecincts={256,256},{256,256},{128,128}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}"])

def make_tn(directory, file):
    # would like 85x110^ instead of 85x110!, but need imagemagick upgrade first ( >= 6.3.8-2)
    return 0 == subprocess.call(["convert", "tmp.tiff", "-thumbnail", "85x110!", "-gravity", "center", "-extent", "85x110", "tmp.jpg"])
    
def make_ocr(directory):
    global abby_home
    os.chdir(abby_home)
    return 0 == subprocess.call(["./CLI", "-ics", "-if", "%(dir)s/%(file)s" % {'dir': directory, 'file': file}, 
        "-f", "PDF", "-pem", "ImageOnText", "-pfpf", "Automatic", "-pfq", "90", "-pfpr", "150", "-of", "%(dir)s/tmp.pdf" % {'dir': directory}, 
        "-f", "XML", "-xaca", "-of", "%(dir)s/tmp.xml" % {'dir': directory}, 
        "-f", "Text", "-tel", "-tpb", "-tet", "UTF8", "-of", "%(dir)s/tmp.txt" % {'dir': directory}])

def run_conversions(tmpdir):
    if not make_tn():
        logging.error("error creating thumbnail for " + obj.pid)
        return False
    
    if not make_jp2():
        logging.error("error creating jp2 for " + obj.pid)
        return False
    
    if not make_jp2_lossless():
        logging.error("error creating lossless jp2 for " + obj.pid)
        return False
    
    if not make_ocr(tmpdir):
        logging.error("error creating ocr output for " + obj.pid)
        return False

    return True

def update_fedora():
    # nice if this method returned a status boolean
    update_datastream(obj, 'tn', tmpdir + '/tmp.jpg', 'thumbnail image', 'image/jpeg')
    update_datastream(obj, 'jp2', tmpdir + '/tmp.jp2', 'jp2 image', 'image/jp2')
    update_datastream(obj, 'jp2lossless', tmpdir + '/tmp_lossless.jp2', 'jp2 image (lossless)', 'image/jp2')
    update_datastream(obj, 'xml', tmpdir + '/tmp.xml', 'ocr xml', 'text/xml')
    update_datastream(obj, 'text', tmpdir + '/tmp.txt', 'ocr text', 'text/plain')
    update_datastream(obj, 'pdf', tmpdir + '/tmp.pdf', 'pdf', 'application/pdf')

class islandoradm(FedoraMicroService):
    '''
    classdocs
    '''
    name = "Islandora DM Plugin"
    content_model = "islandora-dm:po-page-cmodel"
    dsIDs = ['tiff', 'jp2', 'jp2lossless', 'tn', 'xml', 'text', 'pdf']

    def runRules(self, obj, dsid):
        sysout("doing something!")
	logging.info("in runRules")
        if dsid == 'tiff':
            try:
                tmpdir, file = get_datastream_as_file(obj, dsid, 'tiff')
            
                cwd = os.getcwd()
                os.chdir(tmpdir)
                        
                run_conversions() and update_fedora(tmpdir)
            
            except Exception as e:
                logging.error("an exception occurred: " + e);
                
            os.chdir(cwd)
        else:
            logging.info("ignoring dsid: " + dsid)

    def __init__(self):
        '''
        Constructor
        '''
