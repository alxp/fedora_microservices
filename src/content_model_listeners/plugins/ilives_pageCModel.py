'''
Created on Oct 19, 2010

@author: aoneill
'''
import subprocess
# These will appear in an IDE as broken dependencies.
# This is OK because they live in the plugins folder but are invoked in the app's main folder
# by the plugin manager
from categories import FedoraMicroService
from categories import get_datastream_as_file, update_datastream
from shutil import rmtree
import logging, os

abbyy_cli_home = '/usr/local/ABBYYData/FRE80_M5_Linux_part_498-28_build_8-1-0-7030/Samples/CLI/'

def do_abbyy_ocr(obj, dsid):
    # Download a datastream as a temp file and get its location and filename.
    directory, file = get_datastream_as_file(obj, dsid, 'tiff')
    
    # ABBYY must be run while you are in the CLI directory.
    oldpwd = os.getcwd()
    os.chdir(abbyy_cli_home)
    txtfile = "%(dir)s/tmpfile.txt" % {'dir': directory}
    pdffile = "%(dir)s/tmpfile.pdf" % {'dir': directory}
    xmlfile = "%(dir)s/tmpfile.xml" % {'dir': directory}
    
    r = subprocess.call(["./CLI", "-ics", "-if", "%(dir)s/%(file)s" % {'dir': directory, 'file': file},
              "-f", "PDF", "-pem", "ImageOnText", "-pfpf", "Automatic", "-pfq", "90", "-pfpr", "150", "-of", pdffile,
              "-f", "XML", "-xaca", "-of", xmlfile, 
              "-f", "Text", "-tel", "-tpb", "-tet", "UTF8", "-of", txtfile])
    logging.debug(os.listdir(directory))
    if r == 0:
        if os.path.exists(txtfile):
            update_datastream(obj, 'OCR', txtfile, label='OCR Text', mimeType='text/plain')
        if os.path.exists(xmlfile):
            update_datastream(obj, 'ABBYY', xmlfile, label='FineReader XML data', mimeType='application/xml')
        if os.path.exists(pdffile):
            update_datastream(obj, 'PDF', pdffile, label='Page PDF', mimeType='application/pdf')
    else:
        logging.error("Error calling ABBYY FineReader CLI. Error code %(err)d." % {'err': r})
    
    rmtree(directory, ignore_errors=True)
    # Go back to the prevsious working directory
    os.chdir(oldpwd)


def create_jp2(obj, dsid):
    
    # We receive a TIFF and create a Lossless JPEG 2000 file from it.
    directory, file = get_datastream_as_file(obj, dsid, 'tiff')
    
    # Make a lossless JP2
    # kdu_compress -i $i -o $bn.jp2 -rate -,0.5 Clayers=2 Creversible=yes Clevels=8 "Cprecincts={256,256},{256,256},{128,128}" Corder="RPCL" ORGgen_plt="yes" ORGtparts="R" Cblk="{32,32}" 
    r = subprocess.call(["kdu_compress", "-i", directory+'/'+file, "-o", directory+"/tmpfile_lossless.jp2", "-rate", "-,0.5", "Clayers=2", "Creversible=yes", "Clevels=8", "Cprecincts={256,256},{256,256},{128,128}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}"])
    if r == 0:
        update_datastream(obj, 'LosslessJP2', directory+'/tmpfile_lossless.jp2', label='Lossless JPEG2000', mimeType='image/jp2')
    r2 = subprocess.call(["kdu_compress", "-i", directory+'/'+file, "-o", directory+"/tmpfile_lossy.jp2", "-rate", "0.5", "Clayers=1", "Clevels=7", "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
    if r2 == 0:
        update_datastream(obj, 'JP2', directory+'/tmpfile_lossy.jp2', label='Compressed JPEG2000', mimeType='image/jp2')
    r3 = subprocess.call(["convert", "-thumbnail", "200x200", directory+'/'+file, directory+"/tmpfile_TN.jpg"])
    if r3 == 0:
        update_datastream(obj, 'TN', directory+'/tmpfile_TN.jpg', label='Thumbnail', mimeType='image/jpg')
    logging.debug(os.listdir(directory))
    rmtree(directory, ignore_errors=True)


class ilives_pageCModel(FedoraMicroService):
    '''
    classdocs
    '''
    name = "Book page content model"
    content_model = "ilives:pageCModel"
    dsIDs = ['TIFF', 'JP2', 'LosslessJP2']

    def runRules(self, obj, dsid):
        if dsid == 'TIFF':
            # Create JPEG2000 images.
            create_jp2(obj, dsid)
            if os.path.exists("%(abbyy)s/CLI" % {'abbyy': abbyy_cli_home}):
                do_abbyy_ocr(obj, dsid)
        return 

    def __init__(self):
        '''
        Constructor
        '''
        