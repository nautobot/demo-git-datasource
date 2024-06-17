import re

from nautobot.circuits.models import Circuit
from nautobot.dcim.models import Device, DeviceType, Location
from nautobot.extras.jobs import get_task_logger, Job, StringVar, MultiObjectVar
from nautobot.extras.models import Role


logger = get_task_logger(__name__)


name = "Data Quality"


def normalize(query_set):
    """Returns a list of names for the log entry

    Args:
        query_set: QuerySet object
    """
    list_of_names = []
    for element in query_set:
        if hasattr(element, "name"):
            list_of_names.append(element.name)
        else:
            list_of_names.append(element.slug)
    return ', '.join(list_of_names)


def filter_devices(location=None, device_role=None, device_type=None):
    """Returns a list of devices per filter parameters."""
    devices = Device.objects.all()

    if location:
        logger.debug("Filter locations: %s", normalize(location))
        # *__in enables to pass the query set as a parameter
        devices = devices.filter(location__in=location)

    if device_role:
        logger.debug("Filter device roles: %s", normalize(device_role))
        devices = devices.filter(role__in=device_role)

    if device_type:
        logger.debug("Filter device types: %s", normalize(device_type))
        devices = devices.filter(device_type__in=device_type)

    return devices


class FormData:

    location = MultiObjectVar(
        model = Location,
        required = False,
    )
    device_role = MultiObjectVar(
        model = Role,
        required = False
    )
    device_type = MultiObjectVar(
        model = DeviceType,
        required = False
    )


class VerifyHostnames(Job):
    """Demo job that verifies device hostnames match corporate standards."""

    class Meta:
        """Meta class for VerifyHostnames"""

        name = "Verify Hostnames"
        description = "Verify device hostnames match corporate standards"

    location = FormData.location
    device_role = FormData.device_role
    device_type = FormData.device_type
    hostname_regex = StringVar(
        description = "Regular expression to check the hostname against",
        default = ".*",
        required = True
    )

    def run(self, location, device_role, device_type, hostname_regex):
        """Executes the job"""

        logger.info(f"Using the regular expression: %s", hostname_regex)
        for device in filter_devices(location, device_role, device_type):
            if re.search(hostname_regex, device.name):
                logger.info("Hostname is compliant.", extra={"obj": device})
            else:
                logger.warning("Hostname is not compliant.", extra={"obj": device})


class VerifyPlatform(Job):
    """Demo job that verifies that platform is defined for devices"""

    class Meta:
        """Meta class for VerifyPlatform"""

        name = "Verify Platform"
        description = "Verify a device has platform defined"

    location = FormData.location
    device_role = FormData.device_role
    device_type = FormData.device_type

    def run(self, location, device_role, device_type):
        """Executes the job"""

        for device in filter_devices(location, device_role, device_type):
            if device.platform:
                logger.info("Platform is defined.", extra={"obj": device})
            else:
                logger.warning("Platform is not defined.", extra={"obj": device})


class VerifyPrimaryIP(Job):
    """Demo job that verifies that a primary IP is defined for devices."""

    class Meta:
        """Meta class for VerifyPrimaryIP"""

        name = "Verify Primary IP"
        description = "Verify a device has a primary IP defined"

    location = FormData.location
    device_role = FormData.device_role
    device_type = FormData.device_type

    def run(self, location, device_role, device_type):
        """Executes the job"""

        for device in filter_devices(location, device_role, device_type):

            # Skip if not master of virtual chassis as only master should have primary IP
            if device.virtual_chassis:
                if not device.virtual_chassis.master_id == device.id:
                    continue

            if not device.primary_ip:
                logger.warning("No primary IP is defined", extra={"obj": device})
            else:
                logger.info("Primary IP is defined (%s)", device.primary_ip, extra={"obj": device})


class VerifyHasRack(Job):
    """Demo job that verifies that a device is inside a rack."""

    class Meta:
        """Meta class for VerifyHasRack"""

        name = "Verify Device Rack"
        description = "Verify a device is inside a rack"

    location = FormData.location
    device_role = FormData.device_role
    device_type = FormData.device_type

    def run(self, location, device_role, device_type):
        """Executes the job"""

        for device in filter_devices(location, device_role, device_type):
            if not device.rack:
                logger.warning("Device is not inside a rack", extra={"obj": device})
            else:
                logger.info("Device is in rack (%s)", device.rack, extra={"obj": device})


class VerifyCircuitTermination(Job):
    """Demo job that verifies if each circuit has termination and an IP address"""

    class Meta:
        """Meta class for VerifyCircuitTermination"""

        name = "Verify Circuit Termination"
        description = "Verify a circuit has termination and an IP address"


    def run(self):
        """Executes the job"""

        for circuit in Circuit.objects.all():
            termination = circuit.termination_a
            if not termination.path:
                logger.warning("Circuit is not terminated", extra={"obj": circuit})
                continue

            interface = termination.path.destination.name
            device = termination.path.destination.device.name
            logger.info("Circuit terminated on %s:%s", device, interface, extra={"obj": circuit})

            ip_addresses = termination.path.destination.ip_addresses.all()
            if not ip_addresses:
                logger.warning("IP address is not assigned", extra={"obj": circuit})
                continue
            first = str(ip_addresses.first().address)
            logger.info("IP address is assigned (%s)", first, extra={"obj": circuit})
