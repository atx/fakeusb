# fakeusb
Python package implementing server-side of the SPICE [usbredir](https://www.spice-space.org/usbredir.html) protocol
aimed at faking USB devices to virtual guests in qemu.

Potential uses include mock devices for automated driver/application testing or exploit development.

_Note: I mostly hacked this together over two afternoons, consider the code work in progress._ 

## Installation

The Python package can be installed using

```
$ pip3 install https://github.com/atx/fakeusb/archive/master.zip
```

## Usage

An example emulating a generic CDC-ACM serial port device can be found in
[`examples/cdc.py`](https://github.com/atx/fakeusb/blob/master/examples/cdc.py). A script for running
qemu with the necessary options to enable usb redirection is provided in [`examples/run_qemu.sh`](https://github.com/atx/fakeusb/blob/master/examples/run_qemu.sh).


![cdc](https://user-images.githubusercontent.com/3966931/42657682-49a97090-8623-11e8-9b7f-c6ca48b6904e.png)
![qemu](https://user-images.githubusercontent.com/3966931/42657683-49c45f7c-8623-11e8-9412-54c03b3b82d9.png)
