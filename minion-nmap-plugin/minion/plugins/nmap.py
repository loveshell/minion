# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import re
import urlparse
from minion.plugin_api import AbstractPlugin, ExternalProcessPlugin


def parse_nmap_output(output):
    ports = []
    for line in output.split("\n"):
        match = re.match('^(\d+)/(tcp|udp)\s+open\s+(\w+)', line)
        if match is not None:
            #ports.append({'port':match.group(1),'protocol':match.group(2), 'service':match.group(3)})
            port = int(match.group(1))
            severity = 'high'
            if port in (80,443):
                severity = 'info'
            ports.append({'summary': 'Port %d is open' % port, 'severity': severity})
    return ports


class NMAPPlugin(ExternalProcessPlugin):

    NMAP_NAME = "nmap"

    def _validate_ports(self, ports):
        # U:53,111,137,T:21-25,139,8080
        return re.match(r"(((U|T):)\d+(-\d+)?)(,((U|T):)?\d+(-\d+)?)*", ports)

    def do_start(self):
        nmap_path = self.locate_program(self.NMAP_NAME)
        if nmap_path is None:
            raise Exception("Cannot find nmap in path")
        self.output = ""
        u = urlparse.urlparse(self.configuration['target'])
        args = ["--open"]
        ports = self.configuration.get('ports')
        if ports:
            if not self._validate_ports(ports):
                raise Exception("Invalid ports specification")
            args += ["-p", ports]
        args += [u.hostname]
        self.spawn(nmap_path, args)

    def do_process_stdout(self, data):
        self.output += data

    def do_process_ended(self, status):
        self.callbacks.report_results(parse_nmap_output(self.output))
        self.callbacks.report_finish()
