from django.apps import AppConfig as _AppConfig

from mibios import __version__


class AppConfig(_AppConfig):
    name = 'mibios_glamr'
    verbose_name = 'GLAMR'
    version = __version__
