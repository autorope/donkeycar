# Install Donkeycar

## TODO

- move become to each role call in playbook
- mount tmpfs ??
- alternatives ??
- check things from basic and secure conf
- How to include differents cars hostnames / config

## Versions constaints

Jetson Nano : Tensorflow 2.4.1 max by now, see [Qengineering](https://github.com/Qengineering/TensorFlow-Raspberry-Pi_64-bit)

RPi

- Buster for PiCamera or activate legacy (?)
- Buster only in 32b (Raspi OS)
- Bulleyes avalaible in 32 and 64b

Tensorflow wheel

- From [Qengineering](https://github.com/Qengineering/TensorFlow-Raspberry-Pi_64-bit) : 2.4.1 + 64b + py 3.6
- From [lhelontra](https://github.com/lhelontra/tensorflow-on-arm/releases) : 2.4.0 + 32 / 64b + py 3.7
- From [PINTO0309](https://github.com/PINTO0309/Tensorflow-bin/tree/main/previous_versions)
  - 32b
    - py 3.7: 2.4.0, 2.5.0
  - 64b
    - py 3.7: 2.4.0 -> 2.7.0
    - py 3.8: 2.4.0 -> 2.9.0
    - py 3.9: 2.5.0 -> 2.9.0
    - py 3.10: 2.9.0

## Install on controller

### Install DonkeyCar for Mac

```bash
# clone repo
git clone git@github.com:roboracingleague/donkeycar.git
cd donkeycar

# create and activate a venv
pyenv install 3.8.15
pyenv virtualenv 3.8.15 donkeycar
pyenv local donkeycar
pip install .\[pc\]

# MacOS: install tensorflow !!! NO : DOES NOT WORKS !!!
# https://developer.apple.com/metal/tensorflow-plugin/
# needs python 3.8 ; install tensorflow 2.11
# pip install tensorflow-macos
# pip install tensorflow-metal

pip install tensorflow
```

### Install Ansible

```bash
# Ubuntu ansible requirements
sudo apt-get install openssh-server git python3 python3-dev python3-pip sshpass python3-testresources

# MacOS ansible requirements 
brew install esolitos/ipa/sshpass

# install ansible and python requirements
pip install --upgrade pip setuptools wheel virtualenv
cd scripts/ansible
pip install -r requirements.txt
```

```bash
# install external roles
ansible-galaxy install gantsign.keyboard
```

```bash
# create vault password files
vi ~/.donkey_vault_pass
chmod 600 ~/.donkey_vault_pass
```

## Install OS on RPi

- Flash SD-card:
  - RPI: use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install [Raspberry Pi OS](https://www.raspberrypi.com/software/operating-systems/)
    - Open "Advanced options" in Raspberry Pi Imager and set
      - hostname ; if not set, for first install, use ansible option -e "ansible_host=your_hostname"
      - enable ssh
      - public key ; if not set, will be done by ansible
      - set user / password (password will be overriden by ansible) ; if not set, ansible will try a default login / password (ie pi/raspberry)
      - configure wireless LAN
- If not done with Raspberry Pi Imager:
  - Add empty file named `ssh` in boot-partition of the flashed SD-card.
  - To enable wifi create a file called `wpa_supplicant.conf` in the boot-partition of the flashed SD-card with the following content (multiple networks possible):

```conf
country=FR # Your 2-digit country code
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
network={
    ssid="YOUR_NETWORK_NAME"
    psk="YOUR_PASSWORD"
    key_mgmt=WPA-PSK
}

network={
    ssid="YOUR_NETWORK_NAME"
    proto=RSN
    key_mgmt=WPA-EAP
    pairwise=CCMP
    auth_alg=OPEN
    eap=PEAP
    identity="YOUR_USER"
    password="YOUR_PASSWORD"
    phase1="Peaplabel = 0"
    phase2="auth = MSCHAPV2"
}
```

- Boot pi
- Optional:
  - `ping raspberrypi` to get ip
  - set 'ansible_host=IP' in hosts for first run if host is not reachable by hostname
  - update known hosts

```bash
# remove known host if needed
ssh-keygen -R <ip or hostname>
# and connect to update known hosts
ssh <ip or hostname>
```

## Install DonkeyCar on remote node

### Node requirements

```bash
# on remote node
sudo apt-get install openssh-server python3 python3-pip
```

### Deploy to remote node

```bash
# from controller node
ansible-playbook -i hosts donkeycars.yml --vault-password-file ~/.donkey_vault_pass --limit donkey

# -e "ansible_host=raspberrypi" for first run
# -K to enter sudo password - or do any sudo command before in local
# -k to enter ssh password
# --key-file to specify ssh key file
# --tags tag1 / --skip-tags "tag1,tag2"
# --limit HOST
# --list-hosts / --list-tasks / --list-tags confirm what would be run
# --check to see what way occur, with --diff to show diff in changed files
# -vvvv / --step / --check / --diff / --start-at-task to troubleshoot
```

RPis:

- 1st fails to connect: fallback to creating the ssh user using user pi/raspberry and then uses ssh user to do everything else
- 1st run may fail with ufw could not determine version error: reboot and redo

## Resources

### Encrypt / Decrypt vault

```bash
ansible-vault view vault.yml --vault-password-file ~/.donkey_vault_pass
ansible-vault encrypt vault.yml --vault-password-file ~/.donkey_vault_pass
ansible-vault decrypt vault.yml --vault-password-file ~/.donkey_vault_pass
```

## Links

- [raspi-config documentation](https://www.raspberrypi.org/documentation/configuration/raspi-config.md)
- [raspberry pi security configuration](https://www.raspberrypi.org/documentation/configuration/security.md)
- [Ansible best practices](https://spacelift.io/blog/ansible-best-practices)
