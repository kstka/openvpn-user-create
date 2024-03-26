#!/usr/bin/env python3

import sys
import os
import re
import subprocess
from config import *


def main():

    # user name
    if len(sys.argv) < 2:
        sys.exit(f"INFO : Usage: {sys.argv[0]} name")
    else:
        user_name = sys.argv[1]

    # script dir
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    print(f'INFO : OpenVPN user creation script running from {script_dir}')

    # checks
    if not os.path.isdir(RSA_DIR):
        sys.exit("ERROR : easyrsa directory does not exist")

    if not os.path.isdir(CCD_DIR):
        os.makedirs(CCD_DIR)
        print("INFO : Created CCD directory")

    full_conf_dir = CONF_DIR if os.path.isabs(CONF_DIR) else os.path.join(script_dir, CONF_DIR)
    if not os.path.isdir(full_conf_dir):
        os.makedirs(full_conf_dir)
        print(f"INFO : Created CONF directory {full_conf_dir}")

    if not re.match("^[a-zA-Z0-9-_]+$", user_name):
        sys.exit("ERROR : Only 'a-zA-Z0-9-_' characters are allowed")

    if len(user_name) > 24:
        sys.exit("ERROR : Maximum number of 24 symbols allowed")

    if os.path.isfile(f"{RSA_DIR}/pki/private/{user_name}.key"):
        sys.exit(f"ERROR : Client {user_name} key already exists\n")

    # check ip
    ips = []  # existing ips
    files = [f for f in os.listdir(CCD_DIR) if os.path.isfile(os.path.join(CCD_DIR, f))]
    for file in files:
        ccd_file_path = os.path.join(CCD_DIR, file)
        with open(ccd_file_path, 'r') as content_file:
            content = content_file.read()
            matches = re.search("ifconfig-push (\d{1,3}\.\d{1,3}\.\d{1,3}\.)(\d{1,3})", content)
            if matches:
                if matches.group(1) != NETWORK_PREFIX:
                    print(f"WARNING : Check for an IP in {ccd_file_path}")
                ips.append(int(matches.group(2)))
            else:
                print(f"WARNING : Can not find IP in {ccd_file_path}")

    all_ips = list(range(2, 257))  # all possible ip addresses
    available_ips = list(set(all_ips) - set(ips))  # possible minus existing
    if not available_ips:
        sys.exit("ERROR : No more IPs left")

    ip = NETWORK_PREFIX + str(available_ips[0])  # new ip address

    os.chdir(RSA_DIR)

    print(f"INFO : Creating client {user_name} key")
    subprocess.call(f"./easyrsa --batch --req-cn={user_name} gen-req {user_name} nopass", shell=True)
    print(f"INFO : Signing client {user_name} key")
    subprocess.call(f"./easyrsa --batch sign-req client {user_name}", shell=True)

    ca = open("pki/ca.crt").read()
    cert = open(f"pki/issued/{user_name}.crt").read()
    key = open(f"pki/private/{user_name}.key").read()
    tc = open("pki/tc.key").read()

    # read template
    full_template_path = os.path.join(script_path, TEMPLATE_FILE)
    print(f"INFO : Reading config template {full_template_path}")
    with open(full_template_path, 'r') as file:
        config_template = file.read()

    # create config
    config_filled = config_template.format(
        project_name=PROJECT_NAME,
        remote_server=REMOTE_SERVER,
        remote_port=REMOTE_PORT,
        ca=ca,
        cert=cert,
        key=key,
        tc=tc,
    )

    # write config
    config_path = f"{full_conf_dir}/{CONF_PREFIX}{user_name}.ovpn"
    print(f"INFO : Writing config file {config_path}")
    with open(config_path, 'w') as config_file:
        config_file.write(config_filled)

    ccd_path = f'{CCD_DIR}/{user_name}'
    print(f"INFO : Creating CCD file {ccd_path} for {user_name} {ip}")
    with open(f"{ccd_path}", 'w') as f:
        f.write(f"ifconfig-push {ip} 255.255.255.0")


if __name__ == '__main__':
    main()
