#!/bin/bash
sudo sudo hcitool con > log/hciList.log
sudo hcidump -x > log/hciDump.log &
sleep 0.1
sudo pkill hcidump
