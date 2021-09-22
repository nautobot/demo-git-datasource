import re
from nautobot.extras.jobs import Job, StringVar, MultiObjectVar
from nautobot.dcim.models import Device, Site, DeviceRole, DeviceType
from nautobot.circuits.models import Circuit


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


def filter_devices(data, log):
    """Returns a list of devices per filter parameters
    
    Args:
        data: A dictionary from the job input
        log: The log instance for logs
    """

    devices = Device.objects.all()

    site = data["site"]
    if site:
        log(f"Filter sites: {normalize(site)}")
        # *__in enables to pass the query set as a parameter
        devices = devices.filter(site__in=site)

    device_role = data["device_role"]
    if device_role:
        log(f"Filter device roles: {normalize(device_role)}")
        devices = devices.filter(device_role__in=device_role)

    device_type = data["device_type"]
    if device_type:
        log(f"Filter device types: {normalize(device_type)}")
        devices = devices.filter(device_type__in=device_type)

    return devices


class FormData:

    site = MultiObjectVar(
        model = Site,
        required = False,
    )
    device_role = MultiObjectVar(
        model = DeviceRole,
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

    site = FormData.site
    device_role = FormData.device_role
    device_type = FormData.device_type
    hostname_regex = StringVar(
        description = "Regular expression to check the hostname against",
        default = ".*",
        required = True
    )

    def run(self, data=None, commit=None):
        """Executes the job"""

        regex = data["hostname_regex"]
        self.log(f"Using the regular expression: {regex}") 
        for device in filter_devices(data, self.log_debug):
            if re.search(regex, device.name):
                self.log_success(obj=device, message="Hostname is compliant.")
            else:
                self.log_failure(obj=device, message="Hostname is not compliant.")


class VerifyPlatform(Job):
    """Demo job that verifies that platform is defined for devices"""

    class Meta:
        """Meta class for VerifyPlatform"""

        name = "Verify Platform"
        description = "Verify a device has platform defined"

    site = FormData.site
    device_role = FormData.device_role
    device_type = FormData.device_type

    def run(self, data=None, commit=None):
        """Executes the job"""

        for device in filter_devices(data, self.log_debug):
            if device.platform:
                self.log_success(obj=device, message="Platform is defined.")
            else:
                self.log_failure(obj=device, message="Platform is not defined.")


class VerifyPrimaryIP(Job):
    """Demo job that verifies that a primary IP is defined for devices."""

    class Meta:
        """Meta class for VerifyPrimaryIP"""

        name = "Verify Primary IP"
        description = "Verify a device has a primary IP defined"

    site = FormData.site
    device_role = FormData.device_role
    device_type = FormData.device_type

    def run(self, data=None, commit=None):
        """Executes the job"""

        for device in filter_devices(data, self.log_debug):

            # Skip if not master of virtual chassis as only master should have primary IP
            if device.virtual_chassis:
                if not device.virtual_chassis.master_id == device.id:
                    continue

            if not device.primary_ip:
                self.log_failure(obj=device, message="No primary IP is defined")
            else:
                self.log_success(obj=device, message=f"Primary IP is defined ({device.primary_ip})")


class VerifyHasRack(Job):
    """Demo job that verifies that a device is inside a rack."""

    class Meta:
        """Meta class for VerifyHasRack"""

        name = "Verify Device Rack"
        description = "Verify a device is inside a rack"

    site = FormData.site
    device_role = FormData.device_role
    device_type = FormData.device_type

    def run(self, data=None, commit=None):
        """Executes the job"""

        for device in filter_devices(data, self.log_debug):
            if not device.rack:
                self.log_failure(obj=device, message="Device is not inside a rack")
            else:
                self.log_success(obj=device, message=f"Device is in rack ({device.rack})")


class VerifyCircuitTermination(Job):
    """Demo job that verifies if each circuit has termination and an IP address"""

    class Meta:
        """Meta class for VerifyCircuitTermination"""

        name = "Verify Circuit Termination"
        description = "Verify a circuit has termination and an IP address"


    def run(self, data=None, commit=None):
        """Executes the job"""

        for circuit in Circuit.objects.all():
            termination = circuit.termination_a
            if not termination.path:
                self.log_failure(obj=circuit, message="Circuit is not terminated")
                continue

            interface = termination.path.destination.name
            device = termination.path.destination.device.name
            self.log_success(obj=circuit, message=f"Circuit terminated on {device}:{interface}")

            ip_addresses = termination.path.destination.ip_addresses.all()
            if not ip_addresses:
                self.log_failure(obj=circuit, message="IP address is not assigned")
                continue
            first = str(ip_addresses.first().address)
            self.log_success(obj=circuit, message=f"IP address is assigned ({first})")
