  # ======== Install needed Client packages ========
  sudo apt update
  sudo apt upgrade

  sudo apt install -y gcc
  sudo apt install -y python2.7 python-pip
  sudo apt install -y python3-pip
  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash
  nvm install 8.16.0




  sudo apt update


  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF