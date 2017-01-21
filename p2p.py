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

    def update_info(self):
        info_string = self.wpa_cli.get_peer_info(self.address)
        self.info = get_status_table(info_string)

    def provision(self):
        self.wpa_cli.provision_discovery(self.address);

    def connect(self):
        self.wpa_cli.connect_to_peer(self.address)

class P2P(object):
    def __init__(self, iface):
        self.wpa_cli = WpaCli(iface)
        self.connected = False
        self.connected_peer = None

        # Peers dictionary
        self._peers_lock = Condition()
        self.peers = {}

    def connect(self, peer):
        if self.connected:
            raise Exception("Already connected to a peer.")

        self.connected = True
        peer.connect()
        self.connected_peer = peer

    def disconnect(self):
        if not self.connected:
            raise Exception("Not connected to a peer.")

        self.wpa_cli.disconnect()
        self.connected_peer = None
        self.connected = False

    def add_peers(self, peer_addresses):
        if peers == None:
            return

        added = 0
        self._peers_lock.acquire()
        for address in peer_addresses:
            # have we already found this peer?
            if address not in peers:
                peer = Peer(address)
                peers[addresss] = peer

                # for now, we'll just auto provision.
                peer.provision()

                added += 1

        self._peers_lock.release()
        return added

    def start_discovery(self):
        pass

    def stop_discovery(self):
        pass

class PeerDiscovery(Thread):
    def __init__(self, p2p, polling_interval = 1):
        super(PeerDiscovery, self).__init__()
        self.P2P = p2p
        self.cancel = False
        self.polling_interval = polling_interval

    # support for 'with' keyword.
    def __enter__(self):
        return self.Start()

    def __exit__(self, exception_type, exception_value, traceback):
        self.Stop()
    
    def Stop(self):
        self.P2P.wpa_cli.stop_find()
        self.cancel = True

    def run(self):
        # if we were cancelled before we started, just exit out
        if self.cancel:
            return

        # issue the wpa command to start looking for peers.
        self.P2P.wpa_cli.start_find()

        # enter into the main loop.  This will run until we're cancelled.
        while True:
            if self.cancel:
                return

            peers = self.P2P.wpa_cli.get_peers()
            if peers is not None and length(peers) > 0:
                self.P2P.add_peers(peers)

            # sleep for a little bit while we wait for results.
            time.sleep(this.polling_interval)

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