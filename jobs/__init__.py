from nautobot.core.celery import register_jobs

from demo_git_datasource.jobs.data_quality import (
    VerifyHostnames, VerifyPlatform, VerifyPrimaryIP, VerifyHasRack, VerifyCircuitTermination
)

register_jobs(VerifyHostnames, VerifyPlatform, VerifyPrimaryIP, VerifyHasRack, VerifyCircuitTermination)
