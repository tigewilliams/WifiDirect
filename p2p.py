import subprocess
import time

class WpaCli(object):
	def __init__(self, iface):
		self.iface = iface

	def cmd(self, command):
		cmd_str = "sudo wpa_cli -i {} {}".format(self.iface, command)
		p = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, shell=True)
		stdout = p.communicate()[0]
		return stdout

class Peer(WpaCli):
	def __init__(self, iface, address):
		super(Peer, self).__init__(iface)
		self.address = address
		self.info = {}

	def update_info(self):
		info_string = self.cmd("p2p_peer " + self.address)
		self.info = get_status_table(info_string)
		
	def provision_discovery(self):
		prov_string = "p2p_prov_disc {} pbc".format(self.address)
		self.cmd(prov_string)

class P2P(WpaCli):
	OK = "OK\n"

	def __init__(self, iface):
		super(P2P, self).__init__(iface)
		self.connected = False
		self.connected_peer = None

	def find_peers(self, duration):
		find_status = self.cmd("p2p_find")
		if find_status != P2P.OK:
			raise Exception("Error starting WIFI P2P Find process.  Status: " + find_status)

		peers = []
		for i in range(1, duration):
			# sleep for a second to let P2P Find do its thing
			time.sleep(1)

			address_list = self.cmd("p2p_peers")
			if address_list:
				addresses = address_list.split()
				for addr in addresses:
					p = Peer(self.iface, addr)
					p.provision_discovery()
					peers.append(p)
		
		self.cmd("p2p_stop_find")
		return peers

	def connect(self, peer):
		if self.connected:
			raise Exception("Already connected to a peer.")

		connect_str = "p2p_connect {} pbc persistent go_intent=0".format(peer.address)
		self.cmd(connect_str)
		self.connected_peer = peer
		self.connected = True
	
	def disconnect(self):
		if not self.connected:
			raise Exception("Not connected to a peer.")
		
		result = self.cmd("disconnect")
		self.connected_peer = None
		self.connected = False

	def status(self):
		status = self.cmd("status")
		return get_status_table(status)

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
