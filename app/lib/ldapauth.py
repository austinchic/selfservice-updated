import ldap, json, struct
import ConfigParser, os
from time import sleep

class LDAPAuth(object):

	def __init__(self, config_file):

		#### LDAP SETTINGS ####

		config = ConfigParser.ConfigParser()
		config.readfp(open(config_file))

		# Server Settings
		server = config.get('Server', 'server')
		port = config.get('Server', 'port')
		self.host = server + ":" + str(port)

		# Bind Settings
		self.user_cn = config.get('Bind', 'user_cn')
		self.user_pw = config.get('Bind', 'user_pw')
		#######################

		#### Variables ####
		self.search_scope = ldap.SCOPE_SUBTREE
		self.timeout = float(config.get('Search', 'timeout'))
		self.sizelimit = int(config.get('Search', 'sizelimit'))
		self.search_base = config.get('Search', 'base')

	def bind(self):
		self.LDAPInstance = ldap.initialize(self.host)
		print "init"
		# Start TLS session before binding to the server
		try:
			self.LDAPInstance.start_tls_s()
			print "TLS open for vsgtools bind"
		except ldap.LDAPError, e:
			print e.message['info']
			if type(e.message) == dict and e.message.has_key('desc'):
				print e.message['desc']
			else:
				print e

		self.LDAPInstance.simple_bind_s(self.user_cn, self.user_pw)

	def getCN(self, sAMAccountName):
		res = None
		self.bind()
		try: 
			search_filter = "(&(objectCategory=person)(sAMAccountName="+sAMAccountName+"))"

			ldap_result_id = self.LDAPInstance.search_ext(self.search_base, self.search_scope, search_filter, ["dn"], 0, None, None, self.timeout, self.sizelimit)

			while 1:
				result = self.LDAPInstance.result(ldap_result_id, 0)
				result_code = result[0]
				result_data = result[1]

				if result_code == 100:
					res = result_data[0][0]
				else:
					break

		except ldap.LDAPError, e:
			print e

		return res

	def auth(self, username, password):
		resp = 0

		cn = self.getCN(username)

		# Reinit and bind for LDAP session time out
		if cn is None:
			self.bind()
			print "Rebinding - LDAP Timed Out"
			cn = self.getCN(username)

		if cn is not None:
			try:
				LDAPAuthInstance = ldap.initialize(self.host)
			except ldap.LDAPError, e:
				print e
			# Start TLS session for usernames/pswds before binding to the server
			try:
				LDAPAuthInstance.start_tls_s()
				print "TLS SUCCESS!!!!"
			except ldap.LDAPError, e:
				print e
			try:
				ret = LDAPAuthInstance.simple_bind_s(cn, password)
				resp = 1
			except ldap.INVALID_CREDENTIALS, e:
				print e
				resp = -1

			
		else:
			resp = -1
			print "Error in LDAP CN lookup."

		return resp