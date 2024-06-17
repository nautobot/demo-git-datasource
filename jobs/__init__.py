from nautobot.core.celery import register_jobs

from .data_quality import (
    VerifyHostnames, VerifyPlatform, VerifyPrimaryIP, VerifyHasRack, VerifyCircuitTermination
)

register_jobs(VerifyHostnames, VerifyPlatform, VerifyPrimaryIP, VerifyHasRack, VerifyCircuitTermination)
