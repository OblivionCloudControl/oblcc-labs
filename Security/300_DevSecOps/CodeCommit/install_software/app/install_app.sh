#!/usr/bin/env bash

###################################
# Build and install application   #
###################################
. ~/.nvm/nvm.sh
nvm install --lts
node -e "console.log('Running Node.js ' + process.version)"

sudo cp -r app/build/* /var/www/html/
