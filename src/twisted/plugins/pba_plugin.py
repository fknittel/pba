# vim:set ts=4 sw=4 et:
from __future__ import (absolute_import, division, print_function,
        unicode_literals)
from ConfigParser import SafeConfigParser
import logging.config
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import (IServiceMaker, Service)
from twisted.python.log import PythonLoggingObserver
from twisted.application.internet import TCPServer  # @UnresolvedImport
from pba.core.logging import LogObserverInjectingMultiService
from pba.core import daemon
from pba.client.web import create_site


class IrrigationControllerServiceOptions(usage.Options):
    optParameters = [
            ["port", "p", 8080, "The port number to listen on."],
            ["config-file", "c", "irrigationcontroller.conf",
                    "The configuration file."],
        ]


class StopSprinklersService(Service):
    def __init__(self, job_queue):
        self._job_queue = job_queue

    def stopService(self):
        self._job_queue.remove_all_jobs()


class IrrigationControllerServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "pba"
    description = "Starts the irrigation controller service"
    options = IrrigationControllerServiceOptions

    def makeService(self, options):
        config_file_name = options["config-file"]
        http_port_nr = int(options["port"])

        logging.config.fileConfig(config_file_name)
        config = SafeConfigParser()
        config.read(config_file_name)
        job_queue, sprinkler_ctrl = daemon.main(config)
        site = create_site(job_queue, sprinkler_ctrl)

        multi_service = LogObserverInjectingMultiService(
                observer=PythonLoggingObserver().emit)
        http_service = TCPServer(http_port_nr, site)
        multi_service.addService(http_service)

        stop_sprinklers = StopSprinklersService(job_queue)
        multi_service.addService(stop_sprinklers)

        return multi_service


# Create an instance.  Name is irrelevant.
serviceMaker = IrrigationControllerServiceMaker()
