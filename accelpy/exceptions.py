# coding=utf-8
"""Exceptions"""


class AccelizeException(Exception):
    """Base exception for all other exceptions"""


class ConfigurationException(AccelizeException):
    """Configuration error"""


class RuntimeException(AccelizeException):
    """Runtime error"""


class AuthenticationException(AccelizeException):
    """Authentication error"""
