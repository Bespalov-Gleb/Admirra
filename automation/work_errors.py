"""Explicit failure evidence for durable jobs; never infer safety from text."""


class RejectedBeforeExternalIO(RuntimeError):
    """Validation failed before ANY external write/charge/send was attempted.

    Only raise at a proven pre-side-effect boundary. In particular, timeouts,
    provider rejections and failures after earlier recipients are NOT this case.
    It is a failed job, not success and not permission for automatic retries.
    """
