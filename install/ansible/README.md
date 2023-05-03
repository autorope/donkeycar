# Install Donkeycar

## TODO

- more opencv deps on buster ?! libgtk-3-0
- test PiCamera
- test Pi user password on RPi
- activate FAN on NANO
- createcar on NANO does not works
- review all code, remove TODOs
- sync script with host param
- check roles independently for vars deps

## Versions constaints

Jetson Nano

- JetPack 4.6.1 (JetPack 5.1 is not compatible with Nano)
- Tensorflow 2.7.0

RPi (WIP)

- Buster for PiCamera or activate legacy (?)
- Buster only in 32b (Raspi OS)
- Bulleyes avalaible in 32 and 64b
- Tensorflow wheel
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
pip install -e .\[pc\]

# !!! NO : DOES NOT WORKS !!!
# MacOS: install tensorflow, see https://developer.apple.com/metal/tensorflow-plugin/
# needs python 3.8 ; install tensorflow 2.11
# pip install tensorflow-macos
# pip install tensorflow-metal

pip install tensorflow==2.7.0
```

### Install Ansible

```bash
# Ubuntu ansible requirements
sudo apt-get install openssh-server git python3 python3-dev python3-pip sshpass python3-testresources

# MacOS ansible requirements 
brew install esolitos/ipa/sshpass

# install ansible and python requirements
pip install --upgrade pip setuptools wheel virtualenv
cd install/ansible
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
  - Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install [Raspberry Pi OS](https://www.raspberrypi.com/software/operating-systems/)
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

## Install OS on Jetson Nano

- Flash SD-card:
  - Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install [Jetson Nano 4.6](https://developer.nvidia.com/embedded/jetpack-sdk-46)
- Connect via serial
  - Serial cable is enough for power
  - See headless setup from [Jetson Nano instructions](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit#setup) :
  
```bash
ls /dev/cu.usbmodem*
sudo screen /dev/cu.usbmodemXXX
# ctrl+a,ctrl+k to exit
```

- Do initial config:
  - Select Fr and Eth network and Install without network
  - Create user: donkey / donkeycar (will be changed by ansible)
- Configure network:

```bash
nmcli dev wifi list

# Interface doesn't support scanning, network may be down. Activate with:
sudo ifconfig wlan0 up

# Add a WPA-EAP connection
sudo nmcli connection add type wifi con-name "xxx" ifname wlan0 \
 ssid "xxx" -- \
 ipv4.method auto \
 wifi-sec.key-mgmt wpa-eap \
 802-1x.eap peap \
 802-1x.phase2-auth mschapv2 \
 802-1x.identity "xxx" \
 802-1x.password "xxx"

# Add a WPA-PSK connection
sudo nmcli connection add type wifi con-name "xxx" ifname wlan0 \
 ssid "xxx" -- \
 ipv4.method auto \
 wifi-sec.key-mgmt wpa-psk \
 wifi-sec.psk "xxx"

# May be useful:
# nmcli dev status
# nmcli radio wifi
# nmcli radio wifi on
# nmcli connection # list
# nmcli connection show winet
# nmcli connection up winet # activate, if not
```

## Install DonkeyCar on remote node

### Node requirements

- Optional:
  - `ping raspberrypi` to get ip
  - use -e 'ansible_host=IP' with ansible-playbook aommand for first run if host is not reachable by hostname
  - update known hosts

```bash
# remove known host if needed
ssh-keygen -R < ip or hostnam >
# and connect to update known hosts
ssh < ip or hostnam >
```

```bash
# For RPi, on remote node
sudo apt-get install openssh-server python3 python3-pip
```

### Deploy to remote node

```bash
# from controller node
ansible-playbook -i hosts donkeycars.yml --vault-password-file ~/.donkey_vault_pass --limit hostname

# -e "ansible_host=raspberrypi" for first run if needed
# -e "system_default_user_password=XXX" for first run if needed
# --key-file to specify ssh key file
# --tags tag1 / --skip-tags "tag1,tag2"
# --limit HOST
# --list-hosts / --list-tasks / --list-tags confirm what would be run
# --check to see what way occur, with --diff to show diff in changed files
# -vvvv / --step / --check / --diff / --start-at-task to troubleshoot
```

**BEWARE for passwords:**

- Ansible uses 'ansible_user' and 'ansible_ssh_pass' and 'ansible_become_password' to connect
- 'ansible_user' and 'ansible_ssh_pass' and 'ansible_become_password' are overriden in group_vars (password comes from vault file): -k and -K command line options will not work
- If host is unreachable with user/password, a fallback task will try to create user, connecting with 'system_default_user' / 'system_default_user_password'
- Override 'system_default_user' / 'system_default_user_password' at command line (with -e option) if actual values are different from config ones
- Defaults are: pi/raspberry for RPi and donkey/donkeycar for Nano

Example on WINET, overriding hostname with IP address (or .local) and specifying manually actual SSH and sudo password :

```bash
ansible-playbook -i hosts donkeycars.yml --vault-password-file ~/.donkey_vault_pass --limit pc92 -e "ansible_host=172.32.65.167" -e "system_default_user_password=XXX" 
```

RPis:

- 1st run may fail with ufw could not determine version error: reboot and redo

## Add a new car

- Add hostname in `hosts` file under corresponding group (nanos or rpis)
- Create `<hostname>.yml` file in `host_vars` directory, set `system_hostname` in it and eventually add some custom settings
- Create `<hostname>` directory in `car_configs` and add `myconfig.py` in it

## Add a new User

The file `donkeycar/install/ansible/group_vars/all/vault.yml` contains public ssh keys. Add your own public key to this file to deploy it during install with ansible. See `ansible-vault` command below.

## Resources

### Encrypt / Decrypt vault

```bash
ansible-vault view vault.yml --vault-password-file ~/.donkey_vault_pass
ansible-vault decrypt vault.yml --vault-password-file ~/.donkey_vault_pass
ansible-vault encrypt vault.yml --vault-password-file ~/.donkey_vault_pass
```

## Links

- [raspi-config documentation](https://www.raspberrypi.org/documentation/configuration/raspi-config.md)
- [raspberry pi security configuration](https://www.raspberrypi.org/documentation/configuration/security.md)
- [Ansible best practices](https://spacelift.io/blog/ansible-best-practices)
