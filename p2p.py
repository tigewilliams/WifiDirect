import subprocess
import time
from threading import Thread
from threading import Condition

class WpaCli(object):
    """
    Wraps the wpa_cli command line interface.
    """

    # Some constants
    OK = "OK\n"
    TraceCalls = False
 
    def __init__(self, iface):
        """
        iface: string
            Wifi interface to connect wpa_cli to.  Generally this is wlan0 or wlan1
        """
        self.iface = iface

        # currently only supporting Push Button Connect 
        self.authentication_type = "pbc"

    def cmd(self, command):
        """
        Issues a command to wpa_cli.  Mostly for internal use.  Use the convience functions instead for most operations.
        """
        cmd_str = "sudo wpa_cli -i {} {}".format(self.iface, command)
        if WpaCli.TraceCalls:
            print " ** WPA Command: " + cmd_str

        p = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, shell=True)
        stdout = p.communicate()[0]
        return stdout

    def start_find(self):
        find_status = self.cmd("p2p_find")
        if find_status != WpaCli.OK:
            raise Exception("Error starting WIFI P2P Find process.  Status: " + find_status)

    def stop_find(self):
        self.cmd("p2p_stop_find")

    def get_peers(self):
        peers = []
        address_list = self.cmd("p2p_peers")
        if address_list:
            addresses = address_list.split()
            for addr in addresses:
                p = Peer(self.iface, addr)
                peers.append(p)

        return peers

    def get_peer_info(self, address):
        """
        Gets information about a peer.

        address: string
            MAC address of the peer.
        """
        self.cmd("p2p_peer " + address)

    def provision_discovery(self, address):
        """
        Provisions discovery of the peer.
        """
        prov_string = "p2p_prov_disc {} {}".format(address, self.authentication_type)
        self.cmd(prov_string)

    def connect_to_peer(self, address):
        self.cmd("p2p_connect {} {} persistent go_intent=0".format(address, self.authentication_type))

    def disconnect(self):
        self.cmd("disconnect")

    def status(self):
        status = self.cmd("status")
        return get_status_table(status)

class Peer(object):
    def __init__(self, wpa_cli, address):
        self.wpa_cli = wpa_cli
        self.address = address
        self.info = {}

    def __str__(self):
        return self.address

    def update_info(self):
        info_string = self.wpa_cli.get_peer_info(self.address)
        self.info = get_status_table(info_string)

    def provision(self):
        self.wpa_cli.provision_discovery(self.address);

    def connect(self):
        self.wpa_cli.connect_to_peer(self.address)
        return None

class P2P(object):
    def __init__(self, iface, trace = False):
        self.wpa_cli = WpaCli(iface)
        self.connected = False
        self.connected_peer = None
        self.discovery = None
        self.trace = trace

        # Peers dictionary
        self._peers_lock = Condition()
        self.peers = {}

    def status(self):
        return self.wpa_cli.status()

    def connect(self, peer):
        if self.connected:
            raise Exception("Already connected to a peer.")

        self.tracemsg("Connecting to peer {}.".format(peer.address))
        self.connected = True
        socket = peer.connect()
        self.connected_peer = peer
        self.tracemsg("Connected to peer {}.".format(peer.address))

        return socket

    def disconnect(self):
        if not self.connected:
            raise Exception("Not connected to a peer.")

        self.tracemsg("Disconnecting")
        self.wpa_cli.disconnect()
        self.connected_peer = None
        self.connected = False
        self.tracemsg("Disconnected")

    def add_peers(self, peer_addresses):
        if peer_addresses is None:
            return

        added = 0
        self._peers_lock.acquire()
        for address in peer_addresses:
            # have we already found this peer?
            if address not in self.peers:
                self.tracemsg("Peer found: {}".format(address))
                peer = Peer(self.wpa_cli, address)
                self.peers[address] = peer
                self.tracemsg("peer {} added".format(peer))

                # for now, we'll just auto provision.
                peer.provision()
                self.tracemsg("peer {} provisioned".format(peer))

                added += 1

        self._peers_lock.release()
        return added

    def start_discovery(self):
        if self.discovery is not None:
            return

        self.tracemsg("Starting discovery")
        self.discovery = PeerDiscovery(self, trace = self.trace)
        self.discovery.start()
        self.tracemsg("Discovery started")

    def stop_discovery(self):
        if self.discovery is None:
            return

        self.tracemsg("Stopping discovery")
        self.discovery.stop()
        self.discovery = None
        self.tracemsg("Discovery stopped")

    def tracemsg(self, message):
        if self.trace:
            print "[P2P] {}".format(message)

class PeerDiscovery(Thread):
    def __init__(self, p2p, polling_interval = 1, trace = False):
        super(PeerDiscovery, self).__init__()
        self.P2P = p2p
        self.cancel = False
        self.polling_interval = polling_interval
        self.trace = trace

    # support for 'with' keyword.
    def __enter__(self):
        return self.start()

    def __exit__(self, exception_type, exception_value, traceback):
        self.Stop()
    
    def stop(self):
        self.tracemsg("stopping")
        self.P2P.wpa_cli.stop_find()
        self.cancel = True

    def run(self):
        try:
            self.tracemsg("starting")

            # if we were cancelled before we started, just exit out
            if self.cancel:
                self.tracemsg("cancelled")
                return

            # issue the wpa command to start looking for peers.
            self.P2P.wpa_cli.start_find()

            # enter into the main loop.  This will run until we're cancelled.
            while True:
                if self.cancel:
                    self.tracemsg("cancelled")
                    return

                peers = self.P2P.wpa_cli.get_peers()
                if peers is not None and len(peers) > 0:
                    self.tracemsg("peers found.")
                    self.P2P.add_peers(peers)

                # sleep for a little bit while we wait for results.
                self.tracemsg("sleeping.")
                time.sleep(self.polling_interval)

        except:
            print("Unexpected error:", sys.exc_info()[0])
            self.stop()
            return

    def tracemsg(self, message):
        if self.trace:
            print "[PeerDiscovery] {}".format(message)

# ===========================
# Utility methods
# =============================
def get_status_table(status_string):
	props = {}
	if status_string:
		proplines = status_string.split()
		for line in proplines:
				namevalue = line.split("=")
				props[namevalue[0]] = namevalue[1]	
		return props
