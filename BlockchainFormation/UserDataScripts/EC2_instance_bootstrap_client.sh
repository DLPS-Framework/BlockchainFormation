  # ======== Install needed Client packages ========
  sudo apt update
  sudo apt upgrade

  sudo apt-get install -y nodejs || sudo apt-get install -y nodejs
  sudo apt install -y gcc || sudo apt install -y gcc
  sudo apt install -y npm ||sudo apt install -y npm
  sudo apt install -y python2.7 python-pip || sudo apt install -y python2.7 python-pip
  sudo apt install -y python3-pip || sudo apt install -y python3-pip
  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash



  sudo apt update


  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF