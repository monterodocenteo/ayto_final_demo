#!/usr/bin/env bash

set -e

# Instalar dependencias
apt-get update
apt-get install -y wget unzip curl gnupg

# Instalar Google Chrome estable
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb

# Instalar ChromeDriver compatible
CHROME_VERSION=$(google-chrome --version | awk '{ print $3 }' | cut -d '.' -f 1)
DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}")
wget -N https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/
rm chromedriver_linux64.zip
chmod +x /usr/local/bin/chromedriver
