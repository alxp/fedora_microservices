'''
Created on March 5, 2011

@author: jonathangreen
'''

import string

tn_postfix = '-tn.jpg'

class CoallianceMime():

    # functions need to be defined for each mimetype to be worked on
    @staticmethod
    def application_pdf(CC):
        CC.create_derivative('hasThumbnail', tn_postfix, CC.create_thumbnail)
        CC.create_derivative('hasSWF', '.swf', CC.create_swf)

    @staticmethod
    def image_jpeg(CC):
        # since thumnails are JPGs make sure we aren't recursing
        if (not dsid.endswith(tn_postfix)) and dsid != 'TN':
            CC.create_derivative('hasThumbnail', tn_postfix, CC.create_thumbnail)

    @staticmethod
    def image_tif(CC):
        image_tiff(CC)

    @staticmethod
    def image_tiff(CC):
        CC.create_derivative('hasThumbnail', tn_postfix, CC.create_thumbnail)
        CC.create_derivative('hasJP2', '.jp2', CC.create_jp2)

    @staticmethod
    def audio_x_wav(CC):
        CC.create_derivative('hasMP3', '.mp3', CC.create_mp3)
        CC.create_derivative('hasOGG', '.ogg', CC.create_ogg)

    # mimetype isn't found, do nothing
    @staticmethod
    def mimetype_none(CC):
      pass

    # this is a simple dispatcher that will run functions based on mimetype
    @staticmethod
    def dispatch(obj, dsid, CC):
        try:
            # translate - / + . into _ for the mimetype function
            trantab = string.maketrans('-/+.','____')
            mime =  obj[dsid].mimeType.encode('ascii')
            mime_function_name = mime.translate(trantab)
            # get the function from the self object and run it
            mime_function = getattr( CoallianceMime, mime_function_name, CoallianceMime.mimetype_none )
            mime_function(CC)
        except KeyError:
            # we catch a key error because .mimeType throws one 
            # if no mimeType is defined 
            pass
