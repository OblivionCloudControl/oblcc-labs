#!/usr/bin/env bash

##########################
# Patching OS/software   #
##########################
yum update openssl -y


##########################
# Install dependencies   #
##########################
chmod +x ./app/install_custom_libs.sh
./app/install_custom_libs.sh

##########################
# Install server         #
##########################
sudo yum install httpd -y
sudo service httpd start
sudo chkconfig httpd on

##########################
# Install application    #
##########################
chmod +x ./app/install_app.sh
./app/install_app.sh
