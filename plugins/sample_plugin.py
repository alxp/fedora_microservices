
from plugin_manager import IslandoraListenerPlugin
import pprint
import ConfigParser

class sample_plugin(IslandoraListenerPlugin):

    def initialize(self, config_parser):
        # call the parent function (this just prints an init message to the logs
        # this is a good practice
        IslandoraListenerPlugin.initialize(self, config_parser)
 
        # setup a prettyprint object
        self.pp = pprint.PrettyPrinter(indent=4)

        # get the demo section from the config
        try:
            data = config_parser.get('Custom','demo')

            # log it
            self.logger.info('Got this data from config file: "%s".' % data)

        except ConfigParser.Error:
            self.logger.exception('Parsing config file failed.')
            return False

        return True

    def fedoraMessage(self, message, obj, client):
        # format the message nicely using the initialized pretty printer
        formatted_message = self.pp.pformat(message)

        # print it and log it
        print formatted_message
        self.logger.info(formatted_message)

        #print it and log it
        print obj.pid
        self.logger.info(obj.pid)
        print ""

    def islandoraMessage(self, method, message, client):
        #print it and log it
        print method
        self.logger.info(method)

        #print it and log it
        print message
        self.logger.info(message)
        print ""
        
