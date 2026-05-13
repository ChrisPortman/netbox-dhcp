from netbox.jobs import JobRunner
from .models import DhcpLease


class CheckLeaseAcknowledgedJob(JobRunner):

    def run(self, *args, **kwargs):
        lease: DhcpLease = self.job.object

        if not lease.acknowledged:
            lease.delete()

    class Meta:
        name = "Check Lease Acknowledged"

