#!/usr/bin/python3
#-*- coding: utf-8 -*-
"""Shared HTTP helpers with retries for flaky public APIs."""

import logging
import time

import requests

from annotation.config import HTTP_RETRIES, HTTP_TIMEOUT

logger = logging.getLogger("annotation")

# Temporary upstream failures worth retrying
_RETRY_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}


def request_get(url, *, headers=None, params=None, timeout=None, retries=None):
    """GET with retries on timeout, connection errors, and transient HTTP codes."""
    timeout = HTTP_TIMEOUT if timeout is None else timeout
    retries = HTTP_RETRIES if retries is None else retries
    last_error = None
    last_response = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            if response.status_code not in _RETRY_HTTP_STATUS or attempt >= retries:
                return response
            last_response = response
            wait = min(2 ** (attempt - 1), 10)
            logger.warning(
                "HTTP retry %d/%d for %s (status %s, wait %ss)",
                attempt,
                retries,
                url,
                response.status_code,
                wait,
            )
            time.sleep(wait)
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            if attempt >= retries:
                break
            wait = min(2 ** (attempt - 1), 10)
            logger.warning(
                "HTTP retry %d/%d for %s after %s (wait %ss)",
                attempt,
                retries,
                url,
                error,
                wait,
            )
            time.sleep(wait)

    if last_error is not None:
        raise last_error
    return last_response
