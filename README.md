# Postamt - Admin

## Objective

Have a command line interface for managing the postamt sqlite database as it is defined in http://rob0.nodns4.us/howto/postfix-dovecot-sqlite.howto.

## Usage

``` bash
$ pip install postamt

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
  reset    Reset the whole postamt database.
  user     Manage VMailbox table.

```
