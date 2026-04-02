from urllib.error import URLError


# Exceptions to retry on - connection and transient errors
RETRY_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    URLError,
    OSError,  # Can include network-related OS errors
)
