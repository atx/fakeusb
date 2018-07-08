
import asyncio
import logging


from fakeusb import protocol, usb

log = logging.getLogger(__name__)


class ServerMeta(type):

    def __new__(meta, name, bases, dict_):
        base_handlers = dict()
        for base in bases:
            base_handlers.update(getattr(base, "packet_handlers", dict()))
        if "packet_handlers" in dict_:
            base_handlers.update({k: v for k, v in dict_["packet_handlers"].items()})
        dict_["packet_handlers"] = base_handlers
        dict_["_id_to_packet_type"] = {k.type_id: k for k in base_handlers}
        return super().__new__(meta, name, bases, dict_)


class Server(metaclass=ServerMeta):

    version_string = "fakeusb"
    # TODO: We need DEVICE_QUALIFIER for High speed devices
    device_speed = protocol.DeviceConnect.Speed.FULL

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.configuration_number = 1

    @classmethod
    async def make_instance(class_, reader, writer):
        return await class_(reader, writer).handle()

    def send_packet(self, packet, id_=0):
        log.debug("Sending #{} {}".format(id_, packet))
        data = packet.serialize()
        header = protocol.Header(
            type_=packet.type_id,
            length=len(data),
            id_=id_
        )
        self.writer.write(header.serialize())
        self.writer.write(data)

    async def handle_ignore(self, header, packet):
        pass  # Do nothing

    async def handle_hello(self, header, packet):
        version = type(self).version_string.encode().ljust(64, b"\x00")
        # TODO: Check length
        response = protocol.Hello(
            version=version,
            capabilities=[0x00]  # No idea
        )
        self.send_packet(response)

    def get_descriptor(self, d_type, d_idx):
        if d_type == usb.DescriptorType.DEVICE and d_idx == 0x00:
            data = self.device_descriptor.serialize()
        elif d_type == usb.DescriptorType.CONFIGURATION and d_idx < len(self.configuration_descriptors):
            data = self.configuration_descriptors[d_idx].serialize()
        elif d_type == usb.DescriptorType.STRING and d_idx < len(self.string_descriptors):
            data = self.string_descriptors[d_idx].serialize()
        else:
            data = []
            log.warn("Unable to get descriptor type {} index {}".format(d_type, d_idx))
        return data

    async def handle_control(self, header, packet):
        # TODO: Structure this better
        if packet.request_type == 0x80 and packet.request == usb.SetupRequest.GET_DESCRIPTOR:
            d_type = packet.value >> 8
            d_idx = packet.value & 0xff
            data = self.get_descriptor(d_type, d_idx)
        elif packet.request_type == 0x80 and packet.request == usb.SetupRequest.GET_STATUS:
            data = bytes([0x00, 0x00])  # Some unimportant flags for now
        elif packet.request_type == 0x00 and packet.request in {5, 9}:
            data = []
        else:
            data = []
            log.warn("Unhandled control request {}".format(packet))

        response = packet.derive(
            data=data,
            length=len(data)
        )
        self.send_packet(response, id_=header.id_)

    async def handle_configuration(self, header, packet):
        response = protocol.ConfigurationStatus(
            status=protocol.Status.Success,
            configuration=self.configuration_number,
        )
        self.send_packet(response, id_=header.id_)

    packet_handlers = {
        protocol.Reset: handle_ignore,
        protocol.Hello: handle_hello,
        protocol.ControlPacket: handle_control,
        protocol.SetConfiguration: handle_configuration,
        protocol.GetConfiguration: handle_configuration,
        protocol.CancelDataPacket: handle_ignore,
    }

    async def handle_packet(self, header, packet):
        await self.packet_handlers[self._id_to_packet_type[header.type_]](self, header, packet)

    def send_ep_info(self):

        def ep_to_idx(n):
            idx = n & ~0x80
            if n & 0x80:
                idx += 16
            return idx

        length = 32
        types = [0xff] * length
        intervals = [0xff] * length
        interfaces = [0x00] * length
        for intfd in self.interface_descriptors:
            for epd in intfd.endpoints:
                if not hasattr(epd, "endpoint_address"):
                    continue  # TODO This is for CDC to allow trailing data, make nicer...
                idx = ep_to_idx(epd.endpoint_address)
                types[idx] = int(epd.bm_attributes)
                intervals[idx] = epd.interval
                interfaces[idx] = intfd.interface_number

        for n in [0x00, 0x80]:
            idx = ep_to_idx(n)
            types[idx] = protocol.EpInfo.Type.CONTROL
            intervals[idx] = 0xff
            interfaces[idx] = 0

        packet = protocol.EpInfo(
            type_=types,
            interval=intervals,
            interface=interfaces,
        )
        self.send_packet(packet)

    async def connect(self):
        self.send_ep_info()

        length = 32
        interfaces = [0xff] * length
        classes = [0xff] * length
        subclasses = [0xff] * length
        protocols = [0xff] * length
        intfs = sorted(self.interface_descriptors, key=lambda x: x.interface_number)
        for ind in intfs:
            i = ind.interface_number
            interfaces[i] = ind.interface_number
            classes[i] = ind.interface_class
            subclasses[i] = ind.interface_subclass
            protocols[i] = ind.interface_protocol

        packet = protocol.InterfaceInfo(
            interface_count=len(self.interface_descriptors),
            interface=interfaces,
            interface_class=classes,
            interface_subclass=subclasses,
            interface_protocol=protocols,
        )
        self.send_packet(packet)

        packet = protocol.DeviceConnect(
            speed=self.device_speed,
            device_class=self.device_descriptor.device_class,
            device_subclass=self.device_descriptor.device_subclass,
            device_protocol=self.device_descriptor.device_protocol,
            vendor_id=self.device_descriptor.id_vendor,
            product_id=self.device_descriptor.id_product,
        )
        self.send_packet(packet)

    async def handle(self):
        log.info("Entering the handler loop")
        try:
            while True:
                # First, get the header
                data = await self.reader.readexactly(protocol.Header.raw_length)
                header = protocol.Header.unserialize(data)

                # Then the packet
                data = await self.reader.readexactly(header.length)
                if header.type_ in self._id_to_packet_type:
                    packet = self._id_to_packet_type[header.type_].unserialize(data)
                    log.debug("Got packet #{} {}".format(header.id_, packet))
                    await self.handle_packet(header, packet)
                else:
                    log.error("Unable to handle packet type {}".format(header.type_))
        except asyncio.streams.IncompleteReadError:
            log.info("Connection terminated by the client")
