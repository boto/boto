#!/bin/bash

if [ -z $1 ];
then
  echo "Please specify a branch or tag!"
  exit 1
fi

echo "Cloning python-certifi..."
git clone --branch $1 https://github.com/certifi/python-certifi
echo "Updating the cacerts file..."
cp -a python-certifi/certifi/cacert.pem cacerts.txt
echo "Cleaning up..."
rm -rf python-certifi
