#! /usr/bin/env python3

import asyncio
import logging
import queue

import fakeusb.protocol as p
from fakeusb import usb, server


log = logging.getLogger(__name__)


class CDC:

    class HeaderDescriptor(p.Base):
        function_length: p.T.U8 = 5
        descriptor_type: p.T.U8 = 0x24
        descriptor_subtype: p.T.U8 = 0x00
        bcd_cdc: p.T.U16 = 0x0110

    class UnionDescriptor(p.Base):
        function_length: p.T.U8 = 5
        descriptor_type: p.T.U8 = 0x24
        descriptor_subtype: p.T.U8 = 0x06
        control_interface: p.T.U8
        subordinate_interface0: p.T.U8

    class CallManagementDescriptor(p.Base):
        function_length: p.T.U8 = 5
        descriptor_type: p.T.U8 = 0x24
        descriptor_subtype: p.T.U8 = 0x01
        bm_capabilities: p.T.U8
        data_interface: p.T.U8

    class ACMDescriptor(p.Base):
        function_length: p.T.U8 = 4
        descriptor_type: p.T.U8 = 0x24
        descriptor_subtype: p.T.U8 = 0x02
        bm_capabilities: p.T.U8


class CDCServer(server.Server):

    USB_CLASS_CDC = 0x02
    USB_CLASS_DATA = 0x0a
    USB_CDC_SUBCLASS_ACM = 0x02
    USB_CDC_PROTOCOL_AT = 0x01

    device_descriptor = usb.DeviceDescriptor(
        bcd_usb=0x200,
        device_class=USB_CLASS_CDC,
        device_subclass=0x00,
        device_protocol=0x00,
        max_packet_size0=64,
        id_vendor=0x16c0,
        id_product=0x05dc,
        bcd_device=0x00,
        i_manufacturer=0x01,
        i_product=0x00,
        i_serial_number=0x00,
        num_configurations=0x01,
    )

    ENDPOINT_ITR = 0x83
    ENDPOINT_RX = 0x01
    ENDPOINT_TX = 0x82

    endpoint_descriptors_data = [
        usb.EndpointDescriptor(
            endpoint_address=ENDPOINT_RX,
            bm_attributes=usb.EndpointAttribute.BULK,
            max_packet_size=64,
            interval=100,
        ),
        usb.EndpointDescriptor(
            endpoint_address=ENDPOINT_TX,
            bm_attributes=usb.EndpointAttribute.BULK,
            max_packet_size=64,
            interval=100,
        )
    ]

    endpoint_descriptors_comm = [
        usb.EndpointDescriptor(
            endpoint_address=ENDPOINT_ITR,
            bm_attributes=usb.EndpointAttribute.INTERRUPT,
            max_packet_size=64,
            interval=255,
        )
    ]

    endpoint_descriptors = endpoint_descriptors_data + endpoint_descriptors_comm

    cdc_descriptors = [
        CDC.HeaderDescriptor(),
        CDC.CallManagementDescriptor(
            bm_capabilities=0,
            data_interface=1,
        ),
        CDC.ACMDescriptor(
            bm_capabilities=0
        ),
        CDC.UnionDescriptor(
            control_interface=0,
            subordinate_interface0=1,
        )
    ]

    interface_descriptors = [
        # Communication interface
        usb.InterfaceDescriptor(
            interface_number=0,
            num_endpoints=1,
            interface_class=USB_CLASS_CDC,
            interface_subclass=USB_CDC_SUBCLASS_ACM,
            interface_protocol=USB_CDC_PROTOCOL_AT,
            i_interface=0,
            endpoints=endpoint_descriptors_comm,
            extra=cdc_descriptors,
        ),
        # Data interface
        usb.InterfaceDescriptor(
            interface_number=1,
            num_endpoints=2,
            interface_class=USB_CLASS_DATA,
            interface_subclass=0x00,
            interface_protocol=0x00,
            i_interface=0,
            endpoints=endpoint_descriptors_data,
        ),
    ]

    configuration_descriptors = [usb.ConfigurationDescriptor(
        total_length=(9 + 2*9 + 3*7 + 19),  # TODO: Compute this automatically...
        num_interfaces=len(interface_descriptors),
        configuration_value=1,
        i_configuration=0,
        bm_attributes=0x80,
        max_power=100,
        interfaces=interface_descriptors
    )]

    string_descriptors = [
        usb.StringDescriptor.language((0x09, 0x04)),
        usb.StringDescriptor.build("fakeusb"),
    ]

    def __init__(self, reader, writer):
        super().__init__(reader, writer)
        self._buffer = []

    async def handle_bulk(self, header, packet):
        if packet.endpoint == CDCServer.ENDPOINT_RX:
            log.info("Received {}".format(packet.data))
            self._buffer.extend(bytes(packet.data).upper())

            data = []
            status = p.Status.Success
            length = packet.length
        elif packet.endpoint == CDCServer.ENDPOINT_TX:
            data, self._buffer = self._buffer[:packet.length], self._buffer[packet.length:]
            status = p.Status.Success
            length = len(data)

            if packet.data:
                log.info("Polled for data, sent {}".format(packet.data))
        else:
            data = []
            status = p.Status.Inval
            length = 0
            log.warn("Received bulk transfer on invalid endpoint {:2x}".format(packet.endpoint))

        response = packet.derive(
            data=data,
            status=status,
            length=length,
        )
        self.send_packet(response, id_=header.id_)

    async def handle_hello(self, header, packet):
        await super().handle_hello(header, packet)
        await self.connect()

    packet_handlers = {
        p.Hello: handle_hello,
        p.BulkPacket: handle_bulk
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-p", "--port", type=int, default=7766)
    parser.add_argument("-b", "--bind", type=str, default="127.0.0.1")
    args = parser.parse_args()

    logging.basicConfig(level=(logging.DEBUG if args.verbose else logging.INFO))
    loop = asyncio.get_event_loop()

    coro = asyncio.start_server(CDCServer.make_instance, args.bind, args.port, loop=loop)
    handle = loop.run_until_complete(coro)

    log.info("Serving on {}".format(handle.sockets[0].getsockname()))
    try:
        loop.run_forever()
    finally:
        handle.close()
        loop.run_until_complete(handle.wait_closed())
        loop.close()
