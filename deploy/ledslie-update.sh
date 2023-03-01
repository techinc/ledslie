#!/usr/bin/env bash
set -e

target=$1

if [ -z "$target" ]; then
    echo "Usage: $0 the_invertory_file"
    exit 1
fi

if [ "$target" == "vagrant" ]; then
    ansible-playbook -i .vagrant/provisioners/ansible/inventory/vagrant_ansible_inventory ledslie-install.yml --tags update
else
    ansible-playbook -i $target ledslie-install.yml -kK --tags update
fi
