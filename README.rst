Postamt - Admin
===============

Objective
---------

Have a command line interface for managing the postamt of
https://github.com/diefans/postamt-docker.

Usage
-----

Install postamt with pip::

    $ pip install postamt


Just call it from CLI::

    $ postamt
    Usage: postamt [OPTIONS] COMMAND [ARGS]...

      Manage postamt sqlite database.

    Options:
      --debug / --no-debug
      --db PATH             The postamt database file
      --help                Show this message and exit.

    Commands:
      address  Manage Address table.
      alias    Manage Alias table.
      domain   Manage Domain table.
      init     Init or reset the whole postamt database.
      user     Manage VMailbox table.


You can set ``POSTAMT_DB`` environment to point to your database.



