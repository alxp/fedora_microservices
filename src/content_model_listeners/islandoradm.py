'''
Created on 2010-10-16

@author: jesterhazy
'''

import os
import subprocess
import sys
import fcrepo.connection
import tempfile 

from shutil import rmtree
from fcrepo.client import FedoraClient
from fcrepo.utils import NS

abby_home = '/usr/local/ABBYYData/FRE80_M5_Linux_part_498-28_build_8-1-0-7030/Samples/CLI/'

def read_in_chunks(file_object, chunk_size=524288):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 512k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data

def sysout(msg, end='\n'):
    sys.stdout.write(str(msg) + end)

def make_jp2():
    subprocess.call(["kdu_compress", "-i", "tmp.tiff", "-o", "tmp.jp2", "-rate", "0.5", "Clayers=1", "Clevels=7", "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
    
def make_jp2_lossless():
    subprocess.call(["kdu_compress", "-i", "tmp.tiff", "-o", "tmp_lossless.jp2", "-rate", "-,0.5", "Clayers=2", "Creversible=yes", "Clevels=8", "Cprecincts={256,256},{256,256},{128,128}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}"])

def make_tn():
    # would like 85x110^ instead of 85x110!, but need imagemagick upgrade first ( >= 6.3.8-2)
    subprocess.call(["convert", "tmp.tiff", "-thumbnail", "85x110!", "-gravity", "center", "-extent", "85x110", "tmp.jpg"])
    
def make_ocr(tmpdir):
    global abby_home
    os.chdir(abby_home)
    subprocess.call(["./CLI", "-ics", "-if", "%(dir)s/tmp.tiff" % {'dir': tmpdir}, 
        "-f", "PDF", "-pem", "ImageOnText", "-pfpf", "Automatic", "-pfq", "90", "-pfpr", "150", "-of", "%(dir)s/tmp.pdf" % {'dir': tmpdir}, 
        "-f", "XML", "-xaca", "-of", "%(dir)s/tmp.xml" % {'dir': tmpdir}, 
        "-f", "Text", "-tel", "-tpb", "-tet", "UTF8", "-of", "%(dir)s/tmp.txt" % {'dir': tmpdir}])

def attach_datastream(obj, tmpdir, filename, dsid, dslabel, mime_type):
    if dsid not in obj:
        f = open('%s/%s' % (tmpdir, filename), 'r')
        obj.addDataStream(dsid, dslabel, controlGroup=unicode('M'), mimeType=unicode(mime_type))
        obj[dsid].setContent(f)
        f.close()
    else:
        sysout('datastream %s already exists' % (dsid))

def process(obj, dsid):
    if dsid == 'tiff':
        cwd = os.getcwd()
        tmpdir = tempfile.mkdtemp()
        os.chdir(tmpdir)
            
        # fetch tiff
        f = open(tmpdir + '/tmp.tiff', 'w')
        # f.write(obj['tiff'].getContent().read())
	    # f.close()
        content = obj['tiff'].getContent()
        for chunk in read_in_chunks(content):
            f.write(chunk)
        f.flush()        
        os.fsync(f.fileno())
        f.close()
        
        # do conversions
        make_tn()
        make_jp2()
        make_jp2_lossless()
        make_ocr(tmpdir)

        # attach to fedora object
        attach_datastream(obj, tmpdir, 'tmp.jpg', 'tn', 'thumbnail image', 'image/jpeg')
        attach_datastream(obj, tmpdir, 'tmp.jp2', 'jp2', 'jp2 image', 'image/jp2')
        attach_datastream(obj, tmpdir, 'tmp_lossless.jp2', 'jp2lossless', 'jp2 image (lossless)', 'image/jp2')
        attach_datastream(obj, tmpdir, 'tmp.xml', 'xml', 'ocr xml', 'text/xml')
        attach_datastream(obj, tmpdir, 'tmp.txt', 'text', 'ocr text', 'text/plain')
        attach_datastream(obj, tmpdir, 'tmp.pdf', 'pdf', 'pdf', 'application/pdf')
        
        rmtree(tmpdir, ignore_errors = True)        
        os.chdir(cwd)
    else:
        sysout('islandoradm: ignoring dsid: %s' % (dsid))
        
    return obj
