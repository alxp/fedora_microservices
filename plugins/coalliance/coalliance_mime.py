'''
Created on March 5, 2011

@author: jonathangreen
'''

from coalliance_conversions import CoallianceConversions as CC

tn_postfix = '-tn.jpg'

class CoallianceMime():

    # functions need to be defined for each mimetype to be worked on
    def application_pdf(self, obj, dsid):
        CC.create_derivative('hasThumbnail', tn_postfix, CC.create_thumbnail)
        CC.create_derivative('hasSWF', '.swf', CC.create_swf)

    def image_jpeg(self, obj, dsid):
        # since thumnails are JPGs make sure we aren't recursing
        if (not dsid.endswith(tn_postfix)) and dsid != 'TN':
            CC.create_derivative('hasThumbnail', tn_postfix, CC.create_thumbnail)

    def image_tif(self, obj, dsid):
        image_tiff(obj, dsid)

    def image_tiff(self, obj, dsid):
        CC.create_derivative('hasThumbnail', tn_postfix, CC.create_thumbnail)
        CC.create_derivative('hasJP2', '.jp2', CC.create_jp2)

    def audio_x_wav(self, obj, dsid):
        CC.create_derivative('hasMP3', '.mp3', CC.create_mp3)
        CC.create_derivative('hasOGG', '.ogg', CC.create_ogg)

    # mimetype isn't found, do nothing
    def mimetype_none(self, obj, dsid):
      pass

    # this is a simple dispatcher that will run functions based on mimetype
    def dispatch(self, obj, message):
        try:
            # translate - / + . into _ for the mimetype function
            trantab = string.maketrans('-/+.','____')
            mime =  obj[message['dsid']].mimeType.encode('ascii')
            mime_function_name = mime.translate(trantab)
            # get the function from the self object and run it
            mime_function = getattr( self, mime_function_name, self.mimetype_none )
            mime_function(obj, message['dsid'])
        except KeyError:
            # we catch a key error because .mimeType throws one 
            # if no mimeType is defined 
            pass
