#! /bin/bash

HOST="127.0.0.1"
PORT="7766"

qemu-system-x86_64 \
	-drive file=openwrt-x86-64-combined-ext4.img,id=d0,if=none -device ide-hd,drive=d0,bus=ide.0 \
	-drive if=none,id=usbstick,file=/tmp/ii.img \
	-nographic -m 1024 \
	-usb \
	-device ich9-usb-uhci1,id=usb \
	-device usb-storage,bus=usb.0,drive=usbstick \
	-chardev socket,id=charredir,host="$HOST",port="$PORT",reconnect=2 \
	-device usb-redir,chardev=charredir,id=redir,bus=usb.0

reset
