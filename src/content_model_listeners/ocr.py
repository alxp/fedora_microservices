'''
Created on 2010-07-27

@author: aoneill
'''


import tempfile, os, subprocess
import fcrepo.connection
from shutil import rmtree
from fcrepo.client import FedoraClient
from fcrepo.utils import NS
from time import sleep

abbyy_cli_home = '/usr/local/ABBYYData/FRE80_M5_Linux_part_498-28_build_8-1-0-7030/Samples/CLI/'

def read_in_chunks(file_object, chunk_size=524288):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 512k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data

def book_create_thumbnail(obj, dsID):
    d = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(d)
    
    if dsID in ['JP2']:
        f = open(d+'/tmpfile.jp2', 'w')
        f.write(obj['JP2'].getContent().read())
        f.close()
        # Convert to .TIFF so ImageMagick can read it.
        subprocess.call(["kdu_expand", "-i", "tmpfile.jp2", "-o", "tmpfile.tiff", "-reduce", "2"])
        subprocess.call(["convert", "-size", "400x400", "tmpfile.tiff", "-thumbnail", "120x120", "-unsharp", "0x.5", "tmpfile_TN.jpg"])
    if os.path.exists('tmpfile_TN.jpg'):
        tn_file = open('tmpfile_TN.jpg', 'r')
        if 'TN' not in obj:
            obj.addDataStream('TN', 'tn', controlGroup=unicode('M'), mimeType=unicode('image/jpeg'))
        
        obj['TN'].setContent(tn_file)
        tn_file.close()
        
    rmtree(d, ignore_errors = True)        
    os.chdir(cwd)
    return obj

def book_page_ocr(obj, dsID):
    """
    Create XML, PDF and TXT streams for an image stream and add them to the Fedora object.
    """
    global abbyy_cli_home
    d = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(d)
    success = False
    if dsID == 'TIFF':
        for i in range(0, 4):
            f = open(d+'/tmpfile.tiff', 'w')
            content = obj['TIFF'].getContent()
            for piece in read_in_chunks(content):
                f.write(piece)
            #f.write(obj['TIFF'].getContent().read())
            f.flush()
            os.fsync(f.fileno())
            f.close()
            
            r1 = subprocess.call(["kdu_compress", "-i", "tmpfile.tiff", "-o", "tmpfile.jp2", "-rate", "0.5", "Clayers=1", "Clevels=7", "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
            # Make a lossless JP2
            # kdu_compress -i $i -o $bn.jp2 -rate -,0.5 Clayers=2 Creversible=yes Clevels=8 "Cprecincts={256,256},{256,256},{128,128}" Corder="RPCL" ORGgen_plt="yes" ORGtparts="R" Cblk="{32,32}" 
            r2 = subprocess.call(["kdu_compress", "-i", "tmpfile.tiff", "-o", "tmpfile_lossless.jp2", "-rate", "-,0.5", "Clayers=2", "Creversible=yes", "Clevels=8", "Cprecincts={256,256},{256,256},{128,128}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}"])
            if r1 == r2 == 0:
                success = True
                break
    if not success:
        print("******* Failed to retrieve "+obj.pid+"/TIFF")
        return
        
    if os.path.exists('tmpfile.tiff'):
        # Perform the OCR using ABBYY FineReader
        os.chdir(abbyy_cli_home)
        subprocess.call(["./CLI", "-ics", "-if", "%(dir)s/tmpfile.tiff" % {'dir': d}, "-f", "PDF", "-pem", "ImageOnText", 
                         "-pfpf", "Automatic", "-pfq", "90", "-pfpr", "150", "-of", "%(dir)s/tmpfile.pdf" % {'dir': d},
                         "-f", "XML", "-xaca", "-of", "%(dir)s/tmpfile.xml" % {'dir': d}, 
                         "-f", "Text", "-tel", "-tpb", "-tet", "UTF8", "-of", "%(dir)s/tmpfile.txt" % {'dir': d}])
        subprocess.call(["ls", "-l", d]) 
        
        txt_file = open('%(dir)s/tmpfile.txt' % {'dir': d}, 'r')
        if 'OCR' not in obj:
            obj.addDataStream('OCR', 'Loading datastream', controlGroup=unicode('M'), mimeType=unicode('text/plain'))
        obj['OCR'].setContent(txt_file)
        txt_file.close()
        
        xml_file = open('%(dir)s/tmpfile.xml' % {'dir': d}, 'r')
        if 'ABBYY_XML' not in obj:
            obj.addDataStream('ABBYY_XML', '<?xml version="1.0"?>', controlGroup=unicode('M'), mimeType=unicode('text/xml'))
            #obj.client.addDatastream(obj.pid, 'ABBYY_XML', xml_file, label=unicode("ABYY XML"), mimeType=unicode("text/xml"), controlGroup=unicode('M'))
        
        obj['ABBYY_XML'].setContent(xml_file)
        xml_file.close()
        
        pdf_file = open('%(dir)s/tmpfile.pdf' % {'dir': d}, 'r')
        if 'PagePDF' not in obj:
            obj.addDataStream('PagePDF', 'pdf', controlGroup=unicode('M'), mimeType=unicode('text/pdf'))
            #obj.client.addDatastream(obj.pid, 'PagePDF', pdf_file, label=unicode("Page PDF"), mimeType=unicode("text/pdf"), controlGroup=unicode('M'))
        
        obj['PagePDF'].setContent(pdf_file)
        pdf_file.close()
        
        if dsID == 'TIFF':
            # Update the JP2 stream
            jp2_file = open('%(dir)s/tmpfile.jp2' % {'dir': d}, 'r')
            if 'JP2' not in obj:
                obj.addDataStream('JP2', 'jp2', controlGroup=unicode('M'), mimeType=unicode('image/jp2'))
                #obj.client.addDatastream(obj.pid, 'JP2', jp2_file, label=unicode("Web Version JP2"), mimeType=unicode("image/jp2"), controlGroup=unicode('M'))
            
            obj['JP2'].setContent(jp2_file)
            jp2_file.close()
            jp2_lossless_file = open('%(dir)s/tmpfile_lossless.jp2' % {'dir': d}, 'r')
            if 'LosslessJP2' not in obj:
                obj.addDataStream('LosslessJP2', 'jp2', controlGroup=unicode('M'), mimeType=unicode('image/jp2'))
                #obj.client.addDatastream(obj.pid, 'LosslessJP2', jp2_lossless_file, label=unicode("Archival JP2"), mimeType=unicode("image/jp2"), controlGroup=unicode('M'))
            
            obj['LosslessJP2'].setContent(jp2_lossless_file)
            jp2_lossless_file.close()
                
    rmtree(d, ignore_errors = True)        
    os.chdir(cwd)
    return obj

def do_ocr(obj, dsID):
    """
    Create XML, PDF and TXT streams for an image stream and add them to the Fedora object.
    """
    global abbyy_cli_home
    d = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(d)
    
    if dsID == 'JP2':
        f = open(d+'/tmpfile.jp2', 'w')
        f.write(obj['JP2'].getContent().read())
        f.close()
        # Now do the conversion to get a TIFF
        subprocess.call(["kdu_expand", "-i", "tmpfile.jp2", "-o", "tmpfile.tiff"])
    elif dsID == 'TIFF':
        f = open(d+'/tmpfile.tiff', 'w')
        f.write(obj['TIFF'].getContent().read())
        f.close()
        subprocess.call(["kdu_compress", "-i", "tmpfile.tiff", "-o", "tmpfile.jp2", "-rate", "0.5", "Clayers=1", "Clevels=7", "Cprecincts={256,256},{256,256},{256,256},{128,128},{128,128},{64,64},{64,64},{32,32},{16,16}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}", "Cuse_sop=yes"])
        # Make a lossless JP2
        # kdu_compress -i $i -o $bn.jp2 -rate -,0.5 Clayers=2 Creversible=yes Clevels=8 "Cprecincts={256,256},{256,256},{128,128}" Corder="RPCL" ORGgen_plt="yes" ORGtparts="R" Cblk="{32,32}" 
        subprocess.call(["kdu_compress", "-i", "tmpfile.tiff", "-o", "tmpfile_lossless.jp2", "-rate", "-,0.5", "Clayers=2", "Creversible=yes", "Clevels=8", "Cprecincts={256,256},{256,256},{128,128}", "Corder=RPCL", "ORGgen_plt=yes", "ORGtparts=R", "Cblk={32,32}"])
    
    if os.path.exists('tmpfile.tiff'):
        # Perform the OCR using ABBYY FineReader
        os.chdir(abbyy_cli_home)
        subprocess.call(["./CLI", "-ics", "-if", "%(dir)s/tmpfile.tiff" % {'dir': d}, "-f", "PDF", "-pem", "ImageOnText", 
                         "-pfpf", "Automatic", "-pfq", "90", "-pfpr", "150", "-of", "%(dir)s/tmpfile.pdf" % {'dir': d},
                         "-f", "XML", "-xaca", "-of", "%(dir)s/tmpfile.xml" % {'dir': d}, 
                         "-f", "Text", "-tel", "-tpb", "-tet", "UTF8", "-of", "%(dir)s/tmpfile.txt" % {'dir': d}])
        subprocess.call(["ls", "-l", d]) 
        
        txt_file = open('%(dir)s/tmpfile.txt' % {'dir': d}, 'r')
        if 'OCR' not in obj:
            obj.addDataStream('OCR', mimetype='text/plain')
        obj['OCR'].setContent(txt_file)
        txt_file.close()
        
        xml_file = open('%(dir)s/tmpfile.xml' % {'dir': d}, 'r')
        if 'ABBYY_XML' not in obj:
            obj.addDataStream('ABBYY_XML', mimetype='text/xml')
        obj['ABBYY_XML'].setContent(xml_file)
        xml_file.close()
        
        pdf_file = open('%(dir)s/tmpfile.pdf' % {'dir': d}, 'r')
        if 'PagePDF' not in obj:
            obj.addDataStream('PagePDF', mimetype='text/pdf')
        obj['PagePDF'].setContent(pdf_file)
        pdf_file.close()
        
        if dsID == 'TIFF':
            # Update the JP2 stream
            jp2_file = open('%(dir)s/tmpfile.jp2' % {'dir': d}, 'r')
            if 'JP2' not in obj:
                obj.addDataStream('JP2', mimetype='image/jp2')
            obj['JP2'].setContent(jp2_file)
            jp2_file.close()
            jp2_lossless_file = open('%(dir)s/tmpfile_lossless.jp2' % {'dir': d}, 'r')
            if 'LosslessJP2' not in obj:
                obj.addDataStream('LosslessJP2', mimetype='image/jp2')
            obj['LosslessJP2'].setContent(jp2_lossless_file)
            jp2_lossless_file.close()

                
    rmtree(d, ignore_errors = True)        
    os.chdir(cwd)
    return obj