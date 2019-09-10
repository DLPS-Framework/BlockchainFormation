  # ======== Install needed Client packages ========
  sudo apt update || sudo apt update

  sudo apt upgrade || sudo apt upgrade || echo "Upgrading in client_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  sudo apt-get install -y make || sudo apt-get install -y make
  sudo apt install -y g++ || sudo apt install -y g++
  sudo apt install -y python2.7 python-pip || sudo apt install -y python2.7 python-pip
  # sudo apt install -y python3-pip || sudo apt install -y python3-pip
  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash
  . ~/.nvm/nvm.sh
  . ~/.profile
  . ~/.bashrc
  # NVM_DIR="$HOME/.nvm"
  # [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
  # [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
  nvm install 8.16.0
  echo "export PATH=$PATH:/home/ubuntu/.nvm/versions/node/v8.16.0/bin" >> /home/ubuntu/.profile
  . ~/.profile
  . ~/.bashrc
  echo "node version: $(node -v)"
  echo "npm version: $(npm -v)"
  echo "nvm version: $(nvm version)"
  sudo apt update

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF

