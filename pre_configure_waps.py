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
	print "\n\nChecking for new APs..."
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

def wait_for_waps_to_be_ready(shell, waps):
	# Check to make sure they are registered and not downloading updates
	print "\n\nWaiting on WAPs to be ready for processing..."
	for wap in waps:
		registered = False
		while not registered:
			shell.send("show ap config general " + wap + "\n")
			time.sleep(1)
			output = shell.recv(10000)
			operation_state_results = operational_state_finder.findall(output)
			if len(operation_state_results) > 0:
				if operation_state_results[0] == 'REGISTERED':
					registered = True
					print wap + " is ready to process."
				else:
					print wap + " is not ready to process yet. Sleeping 10 seconds."
					time.sleep(10) # Change to yaml option
			else:
				print wap + " is not ready to process yet. Sleeping 10 seconds."
				time.sleep(10) # Change to yaml option

def change_waps_mode(shell, waps):
	print "\n\nSwitching APs to " + mode + " mode..."
	# Loop through WAPs setting mode
	for wap in waps:
		shell.send("config ap mode " + mode + " " + wap + "\n")
		shell.send("y\n")
		time.sleep(1)
		output = shell.recv(10000)
		# TODO Check if WAP was reconfigured... should have a check for what mode it is in
		print "Rebooting " + wap

def wait_for_waps_to_reboot(shell, waps):
	print "\n\nWaiting for reboots to finish..."
	time.sleep(60) # TODO replace with yaml option
	for wap in waps:
		up = False
		while not up:
			shell.send("show ap summary " + wap + "\n")
			time.sleep(1)
			output = shell.recv(10000)
			wap_results = wap_finder.findall(output)
			if len(wap_results) > 0:
				up = True
				print wap + " is up"

def configure_flexconnect_vlan(shell, waps):
	print "\n\nConfiguring FlexConnect settings..."
	for wap in waps:
		shell.send("config ap disable " + wap + "\n")
		shell.send("config ap flexconnect vlan enable " + wap + "\n")
		shell.send("config ap flexconnect vlan native " + str(flex_native_vlan) + " " + wap + "\n")
		shell.send("config ap enable " + wap + "\n")
		# TODO Confirm settings
		print "FlexConnect native vlan set to " + str(flex_native_vlan) + " for WAP " + wap

def configure_waps_group(shell, waps):
	print "\n\nAdding APs to their group..."
	for wap in waps:
		shell.send("config ap group-name " + ap_group + " " + wap + "\n")
		shell.send("y\n")
		print wap + " added to AP group " + ap_group + ", now rebooting..."
		
def logout(shell):
	shell.send('logout\n')
	print '\nDisconnected from WLC\n'

console.clear()

# Prep regex expressions
wap_finder = re.compile('^(AP[0-9,a-z,A-Z]{4}\.[0-9,a-z,A-Z]{4}\.[0-9,a-z,A-Z]{4})', re.MULTILINE)
#wap_finder = re.compile('^(\w+)\s+\d', re.MULTILINE)
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

# Scan for WAPs to configure
waps = check_for_new_waps(shell, wap_filter)

# Wait for the WAPs found to be ready for modification.
# If they are brand new, they may need to download firmware and reboot.
wait_for_waps_to_be_ready(shell, waps)

# Change the mode and reboot the WAPs.
change_waps_mode(shell, waps)
wait_for_waps_to_reboot(shell, waps)

# Configure flexconnect if specified, no reboot required.
if flex_native_vlan:
	configure_flexconnect_vlan(shell, waps)

# Configure the AP group if specified and reboot.
if ap_group:
	configure_waps_group(shell, waps)
	wait_for_waps_to_reboot(shell, waps)

logout(shell)

print '\n\nComplete!'
console.hud_alert('Pre Configuration Complete!',duration=5)