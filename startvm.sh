#!/bin/bash

# Usage: ./startvm.sh qemu_bin rootfs external_disk iothreads vm_id
#echo qemu_bin: $1, rootfs: $2, external_disk: $3, iothreads: $4, vm_id: $5

QEMU_BIN=$1
ROOTFS=$2
EXTERNAL_DISK=$3
IOTHREADS=$4
NET_PORT=$((5000+$5))
VNC_PORT=$(($5+1))
FOLDER=$6

if [ $IOTHREADS == "1" ]; then
    CONFIG_IOTHREADS="-object iothread,id=iothread0 -device virtio-blk-pci,id=image2,drive=drive_image2,x-data-plane=on,iothread=iothread0"
else
    CONFIG_IOTHREADS="-device virtio-blk-pci,id=image2,drive=drive_image2"
fi

$QEMU_BIN \
    -M pc  \
    -nodefaults  \
    -vga std  \
    -vnc :$VNC_PORT \
    -device virtio-net-pci,mac=9a:b1:b2:b3:b4:b5,id=idqmcxu6,vectors=4,netdev=idsegdFJ,bus=pci.0,addr=05  \
    -netdev user,id=idsegdFJ,hostfwd=tcp::$NET_PORT-:22  \
    -drive format=raw,id=drive_image1,if=none,format=raw,file=$ROOTFS \
    -device virtio-blk-pci,id=image1,drive=drive_image1,bootindex=0,bus=pci.0,addr=04 \
    -drive id=drive_image2,if=none,cache.direct=on,format=raw,aio=native,file=$EXTERNAL_DISK \
    ${CONFIG_IOTHREADS} \
    -m 1024  \
    -smp 2,maxcpus=10,cores=1,threads=1,sockets=2  \
    -cpu 'SandyBridge' \
    -rtc base=utc,clock=host,driftfix=none  \
    -boot order=d,menu=on \
    -enable-kvm &

PID=$!
i=0
while $(kill -0 $PID >/dev/null 2>&1); do
    cpu_usage=$(top -b -d1 -n1 -p $PID|grep $PID|awk '{print $9}'|sed -e 's/,/\./g');
    echo "${i},${cpu_usage}" >> $FOLDER/cpu_on_host.csv
    i=$((i+1))
    sleep 1;
done
