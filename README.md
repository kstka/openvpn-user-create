# OpenVPN user creation script

This script automates the process of creating configurations for OpenVPN clients. It handles the generation of client  
keys, signing of the certificates, and creation of client configuration files with predefined template. The script also  
manages client-specific settings in the CCD (Client Configuration Directory) by automatically assigning unique IP  
addresses to each client.  

# Requirements
 
* Python 3.x
* OpenVPN with Easy-RSA for certificate management
* Access to the OpenVPN server's Easy-RSA directory and the CCD directory

# Setup

## Install OpenVPN and EasyRSA
```sh
sudo -i
apt update
apt install easy-rsa openvpn -y
```

## Set up new OpenVPN server
```sh
PROJECT_NAME=vpn-server
mkdir /etc/openvpn/${PROJECT_NAME}
cp -r /usr/share/easy-rsa /etc/openvpn/${PROJECT_NAME}
cd /etc/openvpn/${PROJECT_NAME}/easy-rsa

echo "set_var EASYRSA_ALGO     ec
set_var EASYRSA_CURVE    secp521r1
set_var EASYRSA_DIGEST   \"sha512\"
set_var EASYRSA_CA_EXPIRE       36500
set_var EASYRSA_CERT_EXPIRE     36500" \
| tee -a vars > /dev/null

EASYRSA_VARS_FILE=/etc/openvpn/${PROJECT_NAME}/easy-rsa/vars
./easyrsa init-pki
dd if=/dev/urandom of=pki/.rnd bs=256 count=1
./easyrsa build-ca nopass
./easyrsa gen-req server nopass
./easyrsa sign-req server server
openvpn --genkey --secret pki/tc.key
```

Create OpenVPN server configuration  
Change port, proto and server fields according to your parameters!  


vi /etc/openvpn/${PROJECT_NAME}.conf
```
# Define the network port and protocol
port 6543
proto udp
dev tun

# Specify locations of the certificate authority (CA), server certificate, and private key
ca project-name/easy-rsa/pki/ca.crt
cert project-name/easy-rsa/pki/issued/server.crt
key project-name/easy-rsa/pki/private/server.key

# Disable Diffie-Hellman parameters
dh none

# VPN server IP and subnet configuration
server 10.10.10.0 255.255.255.0
topology subnet

# Keepalive settings to maintain active connections
keepalive 10 120

# Encrypt control channel with a pre-shared key
tls-crypt project-name/easy-rsa/pki/tc.key

# Security parameters for authentication and encryption
auth SHA512
keysize 256
tls-server
tls-version-min 1.2
tls-cipher TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384
cipher AES-256-GCM

# Set renegotiation time in seconds
reneg-sec 360

# Ensure the client certificate is for client authentication
remote-cert-eku "TLS Web Client Authentication"

# Enable script execution
script-security 2

# Allow VPN clients to communicate with each other
client-to-client

# Directory for client-specific configuration
client-config-dir /etc/openvpn/project-name-ccd

# Uncomment these lines to drop privileges after startup for added security
#user nobody
#group nobody

# Persist key and tunnel information across restarts
persist-key
persist-tun

# Logging configuration
status /var/log/openvpn/project-name-status.log
log /var/log/openvpn/project-name.log

# Set the maximum number of concurrently connected clients
;max-clients 100

# Use a fast compression algorithm
;compress lz4-v2

# Redirect all client traffic through the VPN (uncomment to enable)
;push "redirect-gateway def1 bypass-dhcp"

# Specify a DNS server to be used by the VPN clients
;push "dhcp-option DNS 8.8.8.8"

# Harden the server against Denial of Service attacks
;tls-auth databox/easy-rsa/pki/ta.key 0

# Limit the number of incoming connections per second to mitigate DoS attacks
;tcp-queue-limit 64

# Add explicit-exit-notify to notify the client about VPN session termination
;explicit-exit-notify 1
```

```sh
sed -i "s/project-name/$PROJECT_NAME/g" /etc/openvpn/${PROJECT_NAME}.conf
```

```sh
systemctl start openvpn@${PROJECT_NAME}
systemctl enable openvpn@${PROJECT_NAME}
systemctl status openvpn@${PROJECT_NAME}
```

Change port to yours
```sh
ufw allow 6543
```

## Configure the script
```shell
git clone https://github.com/kstka/openvpn-user-create
cd openvpn-user-create
cp config.py.sample config.py
chmod +x create-user.py
```

Edit config.py and define your variables
```python
PROJECT_NAME = 'vpn-server'
RSA_DIR = f"/etc/openvpn/{PROJECT_NAME}/easy-rsa"
CCD_DIR = f"/etc/openvpn/{PROJECT_NAME}-ccd"
CONF_DIR = "client-configurations"
CONF_PREFIX = f"{PROJECT_NAME}-"
NETWORK_PREFIX = "10.10.10."
REMOTE_SERVER = 'example.com'
REMOTE_PORT = '6543'
TEMPLATE_FILE = 'template.ovpn'
```

# Usage
```shell
./create-user.py username
```

This command will:
* Check if the necessary directories exist (CCD and client config directory), creating them if necessary.
* Generate a unique IP address for the client.
* Generate client keys and sign them using Easy-RSA.
* Fill in the client's OpenVPN configuration template and save it to the specified directory.
* Create a CCD file for the client with the assigned IP address.
