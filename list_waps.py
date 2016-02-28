import sys
import yaml
import paramiko
import base64
import time
import keychain
import re
import console

def connect_to_wlc(ssh):
	print "\n\nConnecting to WLC..."
	keys = ssh.get_host_keys()
	keys.add(hostname,'ssh-rsa',public_key)
	ssh.connect(hostname,username='admin',password='pass')
	password = keychain.get_password(hostname,
	                                 username)
	
	shell = ssh.invoke_shell()
	print "Connected to WLC."
	shell.send(username + "\n")
	shell.send(password + "\n")
	shell.send("config paging disable\n")
	return shell

def check_for_new_waps(shell, wap_filter):
	print "\n\nChecking for APs..."
	shell.send("show ap summary " + wap_filter + "*\n")
	time.sleep(1)
	output = shell.recv(10000)
	waps = wap_finder.findall(output)
	
	if len(waps) == 0:
		print "No unnamed APs found."
		sys.exit()
	
	for wap in waps:
		print "Found " + wap + " for processing."
	return waps

def logout(shell):
	shell.send('logout\n')
	print '\nDisconnected from WLC\n'

console.clear()

# Prep regex expressions
wap_finder = re.compile('^([\w\d-]+)\s+\d+', re.MULTILINE)
operational_state_finder = re.compile('^Operation State \\.+ (\\w+)', re.MULTILINE)

# Load options
with open('pre_configure_waps.yaml', 'r') as file:
		wlc_list = yaml.load(file)

hostname = wlc_list['wlc1']['host']
public_key_string = wlc_list['wlc1']['public_key']
username = wlc_list['wlc1']['username']
mode = wlc_list['wlc1']['mode']
flex_native_vlan = wlc_list['wlc1']['flex_native_vlan']
initial_sleep = wlc_list['wlc1']['initial_sleep']
ap_group = wlc_list['wlc1']['ap_group']
public_key = paramiko.RSAKey(data=base64.b64decode(public_key_string))
wap_filter = wlc_list['wlc1']['filter']

# Wait if an initial sleep period is specified. This allows running the script
# as soon as the APs are plugged in. The goal is for the sleep period to give
# the APs enough time to boot up and connect to the controller
if initial_sleep:
	print "Waiting " + str(initial_sleep) + " seconds before starting."
	time.sleep(initial_sleep)

# Prep the SSH connection
ssh = paramiko.SSHClient()
shell = connect_to_wlc(ssh)

# Scan for WAPs
current_waps = check_for_new_waps(shell, wap_filter)


logout(shell)

print '\n\nComplete!'
console.hud_alert('Pre Configuration Complete!',duration=5)