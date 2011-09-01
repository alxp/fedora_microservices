from yapsy.IPlugin import IPlugin
from yapsy.FilteredPluginManager import FilteredPluginManager
from yapsy.PluginManager import PluginManager
import os
import logging
import ConfigParser

# this is the class that plugins should implement
# this class has a member: self.logger that is initialized with a logger named after the plugin
# this should be used instead of the root logger to output logging information from the plugin.
class IslandoraListenerPlugin(IPlugin):

    # if initialization is needed then initialize should be overriden instead.
    def __init__(self):
        pass

    # this function is called during application setup. If no init is needed for the plugin 
    # then this function doesn't need to be overidden.
    # Parameters:
    #   configparser - A config parser object initialized with the module configuration file
    #     this can be used to do plugin specific configuration. See URL below.
    #     http://docs.python.org/library/configparser.html
    # Return:
    #   True - if the plugin is successfully initialized.
    #   False - Plugin was not successfully initalized, it will not be loaded.
    def initialize(self, config_parser):
        self.logger.info('Initialized')
        return True

    # this is called when a message from fedora is recieved.
    # Parameters:
    #   message -  a dictionary containing the information in the ATOM feed sent with the Fedora
    #     STOMP message parsed so that python can easily access it.
    #     An example message:
    #     {
    #     'args': [   {   'name': 'pid', 'type': 'string', 'value': 'codearl:9044'},
    #                 {   'name': 'state', 'type': 'string', 'value': 'A'},
    #                 {   'name': 'label', 'type': 'string', 'value': 'test ingestt'},
    #                 {   'name': 'logMessage', 'type': 'string', 'value': 'null'}],
    #     'author': 'fedoraAdmin',
    #     'content_models': ['codearl:codearlBasicTest'],
    #     'dsid': None,
    #     'id': 'urn:uuid:a57eba81-d9bf-4803-97f5-53b3a62924e9',
    #     'method': 'modifyObject',
    #     'pid': 'codearl:9044',
    #     'return': '2011-09-01T16:58:46.303Z',
    #     'updated': datetime.datetime(2011, 9, 1, 16, 58, 46, 305000),
    #     'uri': 'http://fedora.coalliance.org:8080/fedora'
    #     }
    #     'method', 'pid' and 'dsid' are all guarenteed to exist. Although pid and dsid may be 
    #     set to None depending on the method. To find more information about the messages being
    #     parsed take a look at this page:
    #     http://fedora-commons.org/documentation/3.0/userdocs/server/messaging/
    #   obj - a initialized FCRepo object class representing the PID that is being maniplated by 
    #     Fedora. For some instances where the PID no longer exists (for instance purge messages) 
    #     this is set to None.
    #   client - the FCRepo client class, so that the repository can be accessed.
    def fedoraMessage(self, message, obj, client):
        pass

    # this is called when a message from islandora is recieved.
    # Parameters:
    #   method - string containing the method passed in the header from islandora
    #   message - the message that was passed by islandora. It has alrady been JSON decoded.
    #   client - fcrepo client, so the function can interact with the repository.
    def islandoraMessage(self, method, message, client):
        pass


class IslandoraPluginManager(PluginManager):

    def loadPlugins(self, callback = None):
        PluginManager.loadPlugins(self, callback)
        for pluginCategory in self.category_mapping.itervalues():
            for plugin in pluginCategory:
                name = os.path.basename(plugin.path)
                plugin.plugin_object.logger = logging.getLogger('IslandoraListener.' + name)
                initialized = plugin.plugin_object.initialize(plugin.config_parser)
                delattr(plugin, 'config_parser')
                if initialized:
                    logging.debug('Initialized %s' % name)
                else:
                    logging.debug('Failed to initialize %s' % name)
                    pluginCategory.remove(plugin)

    def gatherBasicPluginInfo(self, directory, filename):
        (plugin_info, config_parser) = self._gatherCorePluginInfo(directory, filename)
        if (plugin_info is None):
            return
        else:
            infofile = os.path.join(directory, filename)
            try:
                plugin_info.fedora_methods = [ v.strip() for v in config_parser.get('Fedora', 'methods').split(',') ]
                plugin_info.fedora_content_models = [ v.strip() for v in config_parser.get('Fedora', 'content_models').split(',') ]
                plugin_info.islandora_methods = [ v.strip() for v in config_parser.get('Islandora', 'methods').split(',') ]
            except (ConfigParser.NoOptionError, ConfigParser.NoSectionError), e:
                logging.error('Error Reading Plugin Config File %s' % infofile)
                logging.error(e)
                return
        plugin_info.config_parser = config_parser
        if config_parser.has_section('Documentation'):
            if config_parser.has_option('Documentation', 'Author'):
                plugin_info.author = config_parser.get('Documentation', 'Author')
            if config_parser.has_option('Documentation', 'Version'):
                plugin_info.setVersion(config_parser.get('Documentation', 'Version'))
            if config_parser.has_option('Documentation', 'Website'):
                plugin_info.website = config_parser.get('Documentation', 'Website')
            if config_parser.has_option('Documentation', 'Copyright'):
                plugin_info.copyright = config_parser.get('Documentation', 'Copyright')
            if config_parser.has_option('Documentation', 'Description'):
                    plugin_info.description = config_parser.get('Documentation', 'Description')
        return plugin_info


class IslandoraFilteredPluginManager(FilteredPluginManager):

    def __init__(self, enabled_plugins, decorated_manager = None, categories_filter = {'Default': IPlugin}, directories_list = None, plugin_info_ext = 'yapsy-plugin'):
        FilteredPluginManager.__init__(self, decorated_manager, categories_filter, directories_list, plugin_info_ext)
        self.enabled_plugins = enabled_plugins
        logging.debug('IslandoraPluginManager Enabled plugin list: %s' % enabled_plugins)

    def isPluginOk(self, info):
        name = os.path.basename(info.path)
        if (name in self.enabled_plugins):
            return True
        else:
            logging.debug('IslandoraPluginManager %s not enabled' % name)
            return False

