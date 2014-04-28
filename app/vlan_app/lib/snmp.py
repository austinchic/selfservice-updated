from pysnmp.entity.rfc3413.oneliner import cmdgen
from pyasn1.type import univ
import ConfigParser, os

def snmpGet(host, host_port, targetOID, portID, community_r):
	target = targetOID + (int(portID),)
	errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
	cmdgen.CommunityData(community_r, community_r),
	cmdgen.UdpTransportTarget((host, host_port)),
	# Plain OID
	(target))

	print varBinds
	if errorIndication:
		print errorIndication
	else:
		if errorStatus:
			print '%s at %s\n' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex)-1] or '?')
		else:
			results = 0
			for name, val in varBinds:
				oidString = ".".join(map(str, target))
				try:
					results = int(val)
				except:
					results = str(val)

			return results

def snmpSet(host, host_port, targetOID, portID, newValue, community_rw):
	target = targetOID + (portID,)
	errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().setCmd(
	cmdgen.CommunityData(community_rw, community_rw),
	cmdgen.UdpTransportTarget((host, host_port)),
	# Plain OID
	((target), univ.Integer(newValue))
	)

	if errorIndication:
		print errorIndication
	else:
		if errorStatus:
			print '%s at %s\n' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex)-1] or '?')
		else:
			results = 0
			for name, val in varBinds:
				try:
					results = int(val)
				except:
					results = str(val)

			return results

def snmpWalk(host, host_port, targetOID, community_r):
	target = targetOID
	errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().nextCmd(
	cmdgen.CommunityData(community_r, community_r),
	cmdgen.UdpTransportTarget((host, host_port)),
	# Plain OID
	(target))

	if errorIndication:
		print errorIndication
	else:
		if errorStatus:
			print '%s at %s\n' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex)-1] or '?')
		else:
			results = {}
			for i in varBinds:
				key, val = i[0]
				key = str(key)

				substr_index = key.rindex('.') + 1
				port_num = key[substr_index::]

				try:
					results[port_num] = int(val)
				except:
					results[port_num] = str(val)

			return results

# takes a OID string and converts to a tuple
# Ex: "10.2.1.1.1.1" > (10, 2, 1, 1, 1, 1)
def convertOID(oid):
	return tuple( map( lambda x: int(x), oid.split('.') ) )