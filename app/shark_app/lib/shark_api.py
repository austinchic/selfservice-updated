import requests, json
from flask import flash

class SharkAPI(object):
	def __init__(self):

		# API Config #
		self.config = {
			'host': "https://10.223.15.180/",
			'api_base': "https://10.223.15.180/api/shark/4.0/",
			'api_un': "admin",
			'api_pw': "admin",
			'verify_ssl': False
		}

		self.auth = (self.config.get('api_un'), self.config.get('api_pw'))

		self.endpoints = {
			'jobs': self.config.get('api_base') + 'jobs',
			'job': self.config.get('api_base') + 'jobs/'
		}

		## use admin to manage these?
		self.capture_devices = [ "tc0", "tc1" ]
		self.size_limit = {
			'lower': 269484032,	# 256 MB
			'higher': 1073741824	# 1 GB
		}

	"""
	 Executes a API query and returns a JSON response. 
	 	usage: query_api('https://10.223.15.180/api/shark/4.0/jobs.json', type='POST', payload={'var1': 'val1'})
	 		
	 		uri: address of api resource
		 	type: GET, POST, PUT, DELETE
		 	payload: dict of key val pairs
	"""
	def __query_api__(self, uri, **kwargs):
		if uri is None:
			return;

		uri += '.json';

		type = kwargs.get('type') or 'GET'
		payload = kwargs.get('payload') or {}
		payload = json.dumps(payload)

		if type == 'GET':
			req = requests.get(uri, params=payload, auth=self.auth, verify=self.config.get('verify_ssl'), stream=True)

		if type == 'POST':
			req = requests.post(uri, data=payload, auth=self.auth, verify=self.config.get('verify_ssl'))

		if type == 'PUT':
			req = requests.put(uri, data=payload, auth=self.auth, verify=self.config.get('verify_ssl'))

		if type == 'DELETE':
			req = requests.delete(uri, auth=self.auth, verify=self.config.get('verify_ssl'))

		if req.status_code in [200, 201, 202, 203]:
			if kwargs.get('raw') == True:
				return req
			else:
				return json.loads(req.text)
		elif req.status_code is 204:
			return None
		else:
			error = json.loads(req.text)
			flash(error.get('error_id') + ': ' + error.get('error_text'))
			return req

	def get_jobs(self):
		return self.__query_api__(self.endpoints.get('jobs'))

	def get_job(self, id):
		url = self.endpoints.get('job') + id
		req = self.__query_api__(url)
		return req

	def create_job(self, payload):
		limit = payload.get("packet_retention").get('size_limit')
		lower = self.size_limit.get('lower')
		higher = self.size_limit.get('higher')

		# enforce upper limit
		if limit <= higher:
			req = self.__query_api__(self.endpoints.get('jobs'), type="POST", payload=payload, raw=True)
			return req
		else:
			error = requests.Request()
			error.status_code = 400
			error.text = "Packet capture size must be smaller than 1 GB."
			return error

	def start_job(self, id):
		url = self.endpoints.get('job') + id + '/status'
		return self.__query_api__(url, type="PUT", payload={"state":"RUNNING"});

	def stop_job(self, id):
		url = self.endpoints.get('job') + id + '/status'
		return self.__query_api__(url, type="PUT", payload={"state":"STOPPED"});

	def delete_job(self, id):
		url = self.endpoints.get('job') + id
		return self.__query_api__(url, type="DELETE");

	def download_job(self, id):
		url = self.endpoints.get('job') + id + '/packets.json?packets=&bytes=&start_time=&end_time=&file_format=PCAP_US'
		query = self.__query_api__(url, type="GET", raw=True)
		return query
