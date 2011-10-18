'''
Created on March 5, 2011

@author: jonathangreen
'''

import string
from islandoraUtils import DSConverter as DSC
from islandoraUtils.metadata.fedora_relationships import rels_int, rels_namespace, rels_object
from islandoraUtils.fedoraLib import mangle_dsid
from fcrepo.connection import FedoraConnectionException

tn_postfix = '-tn.jpg'

class CoallianceMime():

    def __init__(self, obj, message):
        self.obj = obj
        self.message = message
   
    def create_thumbnail(self, obj, dsid, tnid):
        r = DSC.create_thumbnail(obj, dsid, tnid)

        if r == 0:
            relationships = self.relsint.getRelationships(subject='TN', predicate='fromMime')
            if (not relationships and 'TN' not in obj):
                DSC.create_thumbnail(obj, dsid, 'TN')
                self.relsint.addRelationship('TN', 'fromMime', rels_object(obj[dsid].mimeType, rels_object.LITERAL))
            elif(relationships):
                current_mime = relationships[0][2].data
                new_mime = obj[dsid].mimeType
                if (current_mime.split('/')[0] != 'image') and (new_mime.split('/')[0] == 'image'):
                    DSC.create_thumbnail(obj, dsid, 'TN')
                    self.relsint.purgeRelationships(subject='TN', predicate='fromMime')
                    self.relsint.addRelationship('TN', 'fromMime', new_mime)
        return r

    # general derivative creation function
    def create_derivative(self, relationship, postfix, function, dsid=None):
        # make sure we are not creating a derivative of a derivative
        if (not self.test_derivative()):
            # we default to creating a derivative of ourselves
            if not dsid:
                dsid = self.dsid
            # see if we need a derivative
            relationships = self.relsint.getRelationships(subject=self.dsid, predicate=relationship)
            if relationships:
                did = relationships[0][2].data
                try:
                    if DSC.check_dates(self.obj, self.dsid, did):
                        function(self.obj, dsid, did)
                except FedoraConnectionException:
                    function(self.obj, dsid, did)
            else:
                did = self.dsid.rsplit('.', 1)[0]
                did += postfix
                did = mangle_dsid(did)
                r = function(self.obj, dsid, did)
                if( r == 0 ):
                    self.relsint.addRelationship(self.dsid, relationship, did)
                    self.relsint.update()

    # test derivative - returns true is the dsid is a derivative.
    def test_derivative(self):
        relationships = self.relsint.getRelationships(object=self.dsid)
        if(relationships):
            return True
        else:
            return False

    # meta functions called by multiple mime functions
    def image_derivative(self):
        self.create_derivative('hasThumbnail', tn_postfix, self.create_thumbnail)
        self.create_derivative('hasJP2', '.jp2', DSC.create_jp2)

    def document_derivative(self):
        self.create_derivative('hasPDF', '.pdf', DSC.create_pdf)
        # get name of pdf to create swf and thumbnail from
        relationship = self.relsint.getRelationships(subject=self.dsid, predicate='hasPDF')
        if(relationship):
            pdfid = relationship[0][2].data
            self.create_derivative('hasThumbnail', tn_postfix, self.create_thumbnail, pdfid)
            self.create_derivative('hasSWF', '.swf', DSC.create_swf, pdfid)

    ##
    ## functions need to be defined for each mimetype to be worked on
    ##

    # document stuff
    def application_pdf(self):
        self.create_derivative('hasThumbnail', tn_postfix, self.create_thumbnail)
        self.create_derivative('hasSWF', '.swf', DSC.create_swf)
    def application_vnd_ms_powerpoint(self):
        self.document_derivative()
    def application_vnd_ms_excel(self):
        self.document_derivative()
    def application_msword(self):
        self.document_derivative()
    def application_vnd_openxmlformats_officedocument_spreadsheetml_sheet(self):
        self.document_derivative()
    def application_vnd_openxmlformats_officedocument_presentationml_presentation(self):
        self.document_derivative()
    def application_vnd_openxmlformats_officedocument_wordprocessingml_document(self):
        self.document_derivative()
    def text_rtf(self):
        self.document_derivative()

    # image stuff
    def image_jpeg(self):
        self.image_derivative()
    def image_png(self):
        self.image_derivative()
    def image_tif(self):
        self.image_derivative()
    def image_tiff(self):
        self.image_derivative()
    def image_jp2(self):
        self.image_derivative()
    def image_gif(self):
        self.create_derivative('hasThumbnail', tn_postfix, self.create_thumbnail)

    # audio stuff
    def audio_x_wav(self):
        self.create_derivative('hasMP3', '.mp3', DSC.create_mp3)
        self.create_derivative('hasOGG', '.ogg', DSC.create_ogg)

    # mimetype isn't found, do nothing
    def mimetype_none(self):
        pass

    # this is a simple dispatcher that will run functions based on mimetype
    def dispatch(self, dsid):
        self.relsint = rels_int(self.obj, rels_namespace('coal', 'http://www.coalliance.org/ontologies/relsint'), 'coal')
        self.dsid = dsid
        try:
            # translate - / + . into _ for the mimetype function
            trantab = string.maketrans('-/+.','____')
            mime =  self.obj[dsid].mimeType.encode('ascii')
            mime_function_name = mime.translate(trantab)
            # get the function from the self object and run it
            mime_function = getattr( self, mime_function_name, self.mimetype_none )
            mime_function()
        except KeyError:
            # we catch a key error because .mimeType throws one 
            # if no mimeType is defined 
            pass
