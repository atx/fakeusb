
import enum

from fakeusb.protocol import Base, T, Array


class DescriptorType(enum.IntEnum):
    DEVICE = 0x01
    CONFIGURATION = 0x02
    STRING = 0x03
    INTERFACE = 0x04
    ENDPOINT = 0x05
    DEVICE_QUALIFIER = 0x06
    OTHER_SPEED_CONFIGURATION = 0x07
    INTERFACE_POWER = 0x08


class EndpointAttribute(enum.IntEnum):
    # TODO: More of these?
    CONTROL = 0
    ISO = 1
    BULK = 2
    INTERRUPT = 3


class SetupRequest(enum.IntEnum):
    GET_STATUS = 0x00
    CLEAR_FEATURE = 0x01
    SET_FEATURE = 0x03
    SET_ADDRESS = 0x05
    GET_DESCRIPTOR = 0x06
    SET_DESCRIPTOR = 0x07
    GET_CONFIGURATION = 0x08
    SET_CONFIGURATION = 0x09


class DeviceDescriptor(Base):
    length: T.U8 = 18
    descriptor_type: T.U8 = DescriptorType.DEVICE.value
    bcd_usb: T.U16
    device_class: T.U8
    device_subclass: T.U8
    device_protocol: T.U8
    max_packet_size0: T.U8
    id_vendor: T.U16
    id_product: T.U16
    bcd_device: T.U16
    i_manufacturer: T.U8
    i_product: T.U8
    i_serial_number: T.U8
    num_configurations: T.U8


class EndpointDescriptor(Base):
    length: T.U8 = 7
    descriptor_type: T.U8 = DescriptorType.ENDPOINT.value
    endpoint_address: T.U8
    bm_attributes: T.U8
    max_packet_size: T.U16
    interval: T.U8


class InterfaceDescriptor(Base):
    length: T.U8 = 9
    descriptor_type: T.U8 = DescriptorType.INTERFACE.value
    interface_number: T.U8
    alternate_setting: T.U8 = 0
    num_endpoints: T.U8
    interface_class: T.U8
    interface_subclass: T.U8
    interface_protocol: T.U8
    i_interface: T.U8
    endpoints: Array(EndpointDescriptor)


class ConfigurationDescriptor(Base):
    length: T.U8 = 9
    descriptor_type: T.U8 = DescriptorType.CONFIGURATION.value
    total_length: T.U16  # TODO: Calculate this automatically
    num_interfaces: T.U8
    configuration_value: T.U8
    i_configuration: T.U8
    bm_attributes: T.U8
    max_power: T.U8
    # TODO: More than one interface
    interfaces: Array(InterfaceDescriptor)


class StringDescriptor(Base):
    length: T.U8
    descriptor_type: T.U8 = DescriptorType.STRING.value
    data: Array(T.U8)

    @classmethod
    def language(class_, language_id):
        if len(language_id) != 2:
            raise ValueError("Invalid language id values")
        return class_(
            length=(class_.raw_length + len(language_id)),
            data=bytes(language_id),
        )

    @classmethod
    def build(class_, string):
        encoded = string.encode("utf-16")
        return class_(
            length=(class_.raw_length + len(encoded)),
            data=encoded,
        )
