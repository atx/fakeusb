# fakeusb
Python library implementing the SPICE usbredir protocol aimed at faking
USB devices to virtual guests in qemu.

Potential uses include mock devices for driver testing or exploit development.

## Usage

An example emulating a generic CDC-ACM serial port device can be found in
`examples/cdc.py`. A script for running qemu with the necessary options to enable
usb redirection is provided in `examples/run_qemu.sh`.


![cdc](https://user-images.githubusercontent.com/3966931/42657682-49a97090-8623-11e8-9b7f-c6ca48b6904e.png)
![qemu](https://user-images.githubusercontent.com/3966931/42657683-49c45f7c-8623-11e8-9412-54c03b3b82d9.png)
