#! /bin/bash

HOST="127.0.0.1"
PORT="7766"
IMAGE="openwrt-x86-64-combined-ext4.img"

if [ ! -f $IMAGE ]; then
	echo "Image file '$IMAGE' not found"
	echo "You can download an OpenWRT image on 'https://downloads.openwrt.org/snapshots/targets/x86/64/'"
	exit 1
fi

qemu-system-x86_64 \
	-drive file=$IMAGE,id=d0,if=none -device ide-hd,drive=d0,bus=ide.0 \
	-nographic -m 256 \
	-usb \
	-device ich9-usb-uhci1,id=usb \
	-chardev socket,id=charredir,host="$HOST",port="$PORT",reconnect=2 \
	-device usb-redir,chardev=charredir,id=redir,bus=usb.0

reset
