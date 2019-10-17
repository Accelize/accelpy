# coding=utf-8
"""
This file run a basic HTTP server that read random bytes from the FPGA register
on "get" requests. The number of bytes to read can be specified by passing the
"bytes" argument to the URL of the request

Example: "https://<host_address>>/?size=256" to get 256 bytes.
"""
__version__ = '1.0.0'

from itertools import chain
from json import loads, dumps
import logging
from os import environ
import sys
from threading import Lock
from time import sleep
from urllib.request import urlopen

from accelize_drm import DrmManager
from accelize_drm.fpga_drivers import get_driver
from falcon import HTTPInternalServerError, API
from numpy import empty, int32, float128, dtype, uint8
from pyopencl import (
    get_platforms, Context, Program, command_queue_properties, CommandQueue,
    Kernel, Buffer, mem_flags, enqueue_migrate_mem_objects,
    enqueue_nd_range_kernel, mem_migration_flags)
from traceback import format_exception

#: Buffer size in bytes
BUFFER_BYTES = 1024 * 1024
MAX_REQUEST_SIZE = 128 * BUFFER_BYTES

# Logging and exception handling
INSTANCE = loads(urlopen(
    'http://169.254.169.254/latest/dynamic/instance-identity/document').read())
environ['AWS_DEFAULT_REGION'] = INSTANCE['region']
from watchtower import CloudWatchLogHandler

logging.basicConfig(format='%(asctime)s %(message)s')
LOGGER = logging.getLogger('secureic_trng')
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(CloudWatchLogHandler())
DEFAULT_PARAMS = dict(size=BUFFER_BYTES)


def log(level=logging.INFO, exc_info=None, **kwargs):
    """
    Log

    Args:
        level (int): Log level
        exc_info (tuple): Exception information.
        kwargs: Keyword arguments.
    """
    kwargs['version'] = __version__
    kwargs['instance_info'] = INSTANCE
    if exc_info:
        kwargs['exception'] = "".join(format_exception(*exc_info))
    LOGGER.log(level, dumps(kwargs))


# Initialize urandom function
log(event='START')


class _URandom:
    """FPGA True random number generator"""

    def __init__(self):
        # Get OpenCL device and context
        self._devices = get_platforms()[0].get_devices()
        self._device = self._devices[0]
        self._context = Context(devices=self._devices)

        # Program FPGA
        with open("{{ fpga_binary }}", "rb") as file:
            self._program = Program(self._context, self._devices, [file.read()])

        # Activate the DRM
        self._driver = get_driver(name="{{ accelize_drm_driver_name }}")()
        self._drm_manager = DrmManager(
            "{{ accelize_drm_conf_dst }}",
            "{{ accelize_drm_cred_dst }}",
           self._driver.read_register_callback,
           self._driver.write_register_callback)
        self._drm_manager.activate()

        sleep(2)

        # Create device lock
        self.device_lock = Lock()

        # Initialize OpenCL command queue
        self._queue = CommandQueue(
            context=self._context, device=self._device, properties=
            command_queue_properties.OUT_OF_ORDER_EXEC_MODE_ENABLE |
            command_queue_properties.PROFILING_ENABLE)

        # Create OpenCL kernel
        self._output_stage = Kernel(self._program, "krnl_output_stage_rtl")

        # Create a 4k page aligned float128 OpenCL buffer
        self._item_size = dtype(float128).itemsize
        self._buffer_size = BUFFER_BYTES // self._item_size
        buffer = empty(BUFFER_BYTES + 4096, uint8)
        index = -buffer.ctypes.data % 4096
        self._buffer = buffer[index:index + BUFFER_BYTES].view(float128)
        self._buffer_output = Buffer(
            self._context, mem_flags.USE_HOST_PTR | mem_flags.READ_ONLY,
            size=0, hostbuf=self._buffer)

        # Set the OpenCL kernel Arguments
        self._output_stage.set_args(
            self._buffer_output, int32(self._buffer_size))

    def __call__(self, size):
        """
        FPGA True Random number generator.

        Args:
            size (int): Number of bytes to generate.

        Yields:
            bytes: Random numbers.
        """
        sent_bytes = 0

        # To simplify loop code
        queue = self._queue
        queue_finish = queue.finish
        output_stage = self._output_stage
        buffer_output = (self._buffer_output,)
        flags = mem_migration_flags.HOST
        buffer = self._buffer
        device_lock = self.device_lock
        one_arg = (1,)

        # Generator loop
        while sent_bytes < size:
            with device_lock:

                # Get TRNG data from OpenCL
                enqueue_nd_range_kernel(queue, output_stage, one_arg, one_arg)
                enqueue_migrate_mem_objects(queue, buffer_output, flags=flags)
                queue_finish()

                # Return result as bytes
                to_send_bytes = size - sent_bytes
                if to_send_bytes > BUFFER_BYTES:
                    sent_bytes += BUFFER_BYTES
                    result = buffer.tobytes()

                else:
                    # Ending block
                    sent_bytes += to_send_bytes
                    unaligned = to_send_bytes % self._item_size
                    items_count = to_send_bytes // self._item_size + (
                        1 if unaligned else 0)
                    result = buffer[:items_count].tobytes()

                    if unaligned:
                        result = result[:to_send_bytes]

            yield result

    def __del__(self):
        # Deactivate the DRM
        try:
            self._drm_manager.deactivate()
        except AttributeError:
            pass


try:
    urandom = _URandom()
except Exception:
    log(logging.ERROR, exc_info=sys.exc_info(), event='ERROR')
    sys.exit(-1)


# WSGI application

class Resource:
    """Server resource"""

    @staticmethod
    def on_head(req, resp):
        """Handles HEAD requests"""
        # Get the length to read from the URL query parameters
        size = req.get_param_as_int('size', default=BUFFER_BYTES, min_value=0,
                                    max_value=MAX_REQUEST_SIZE)

        # Set data headers
        resp.content_length = size
        resp.accept_ranges = 'none'
        resp.content_type = 'application/octet-stream'
        resp.downloadable_as = f'random_{size}B.dat'

        # Log requests
        log(headers=req.headers, params=req.params or DEFAULT_PARAMS,
            event=req.method, url=req.uri)

        return size

    def on_get(self, req, resp):
        """Handles HEAD requests"""
        size = self.on_head(req, resp)

        # Content body
        # Note: Initialize the generator for early error detection
        try:
            generator = urandom(size)
            resp.set_stream(chain((next(generator),), generator), size)

        except Exception:
            # Raise 500 Error
            log(logging.ERROR, exc_info=sys.exc_info(), event='ERROR')
            raise HTTPInternalServerError()


application = API()
application.add_route('/', Resource())
