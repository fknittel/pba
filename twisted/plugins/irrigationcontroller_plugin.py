# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from web import create_site
from ConfigParser import SafeConfigParser
import logging.config
from twisted.python.log import PythonLoggingObserver
from twistedlogging import LogObserverInjectingMultiService
from twisted.application.internet import TCPServer  # @UnresolvedImport


class IrrigationControllerServiceOptions(usage.Options):
    optParameters = [
            ["port", "p", 8080, "The port number to listen on."],
            ["config-file", "c", "irrigationcontroller.conf",
                    "The configuration file."],
        ]


class IrrigationControllerServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "irrigationcontroller"
    description = "Starts the irrigation controller service"
    options = IrrigationControllerServiceOptions

    def makeService(self, options):
        config_file_name = options["config-file"]
        http_port_nr = int(options["port"])

        logging.config.fileConfig(config_file_name)
        config = SafeConfigParser()
        config.read(config_file_name)
        site = create_site(config)

        multi_service = LogObserverInjectingMultiService(
                observer=PythonLoggingObserver().emit)
        http_service = TCPServer(http_port_nr, site)
        multi_service.addService(http_service)

        return multi_service


# Create an instance.  Name is irrelevant.
serviceMaker = IrrigationControllerServiceMaker()
