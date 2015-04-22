"""Postamt admin."""
import os
import click
import md5

from sqlalchemy import engine_from_config, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from postamt import model


def main():
    """Just the entrypoint."""

    cli(obj={})  # pylint: disable=E1120,E1123


@click.group()
@click.option('--debug/--no-debug', default=False, envvar="POSTAMT_DEBUG")
@click.option('--db', default="db.sqlite", help="The postamt database file",
              type=click.Path(exists=True, file_okay=True), envvar="POSTAMT_DB")
@click.pass_context
def cli(ctx, debug, db):
    """Manage postamt sqlite database."""

    ctx.obj['DEBUG'] = debug
    ctx.obj['DB'] = db

    # relative path
    engine = create_engine('sqlite:///{db}'.format(db=db))
    model.initialize_sql(engine)


@cli.command()
@click.pass_context
def reset(ctx):
    """Reset the whole postamt database."""

    if click.confirm('Really reset db?'):
        os.unlink(ctx.obj['DB'])

        engine = create_engine('sqlite:///{db}'.format(db=ctx.obj['DB']))
        model.initialize_sql(engine)

        # create local domain
        local_domain = model.Domain(id=0)
        model.DBSession.add(local_domain)

        null_address = model.Address(
            id=0, domain=local_domain, localpart="\0", active=False, rclass=None, transport=None)
        model.DBSession.add(null_address)

        model.DBSession.commit()


@cli.group()
@click.pass_context
def domain(ctx):
    """Manage Domain table."""
    pass


@domain.command(name="list")
@click.pass_context
def domain_list(ctx):
    """Show all domains."""

    domains = model.Domain.query.all()

    for domain in domains:
        click.echo(domain)


@domain.command(name="add")
@click.argument("domain_name")
@click.option("--active/--inactive", default=True)
# TODO make class either 0, 1, 2, 3 or a number above 800
@click.option("klass", "--class", "-c", default=801)
@click.option("--rclass", "-r", default=None)
@click.pass_context
def domain_add(ctx, domain_name, active, klass, rclass):
    """Add a new doman."""

    # test if already there
    try:
        domain = model.Domain.query.filter(model.Domain.name == domain_name).one()
        click.echo("Domain already exists: {}".format(domain_name))

    except NoResultFound:
        domain = model.Domain(name=domain_name, active=active, klass=3, rclass=20)
        model.DBSession.add(domain)

        # add default addresses
        postmaster = model.Address(localpart='postmaster', domain=domain)
        model.DBSession.add(postmaster)

        abuse = model.Address(localpart='abuse', domain=domain)
        model.DBSession.add(abuse)

        model.DBSession.commit()

        click.echo("Added domain: {}".format(domain))


    return domain

@cli.group()
@click.pass_context
def address(ctx):
    """Manage Address table."""


@address.command(name="list")
@click.pass_context
def address_list(ctx):
    """List all addresses."""

    addresses = model.Address.query.all()

    for address in addresses:
        click.echo(address)


@address.command(name="add")
@click.argument("address_name")
@click.option("--active/--inactive", default=True)
@click.option("--transport", "-t", default=None)
@click.option("--rclass", "-r", default=30)
@click.pass_context
def address_add(ctx, address_name, active, transport, rclass):
    """Add an address."""
    localpart, domain_name = address_name.split("@", 1)

    # domain lookup
    domain = ctx.invoke(domain_add, domain_name=domain_name)

    try:
        address = model.Address.query\
            .filter(model.Address.localpart == localpart, model.Address.domain == domain).one()

        click.echo("Address already exists: {}".format(address))

    except NoResultFound:
        address = model.Address(localpart=localpart, domain=domain, active=active, rclass=rclass)

        model.DBSession.add(address)
        model.DBSession.commit()

        click.echo("Address added: {}".format(address))

    return address


@cli.group()
@click.pass_context
def alias(ctx):
    """Manage Alias table."""


@alias.command(name="list")
@click.pass_context
def alias_list(ctx):
    """List all aliases."""

    aliases = model.Alias.query.all()

    for alias in aliases:
        click.echo(alias)


@alias.command(name="add")
@click.argument("source_address")
@click.argument("target_address")
@click.option("--active/--inactive", default=True)
@click.pass_context
def alias_add(ctx, source_address, target_address, active):
    """Add an alias."""

    # domain lookup
    source_address = ctx.invoke(address_add, address_name=source_address)
    target_address = ctx.invoke(address_add, address_name=target_address)

    try:
        alias = model.Alias.query\
            .filter(model.Alias.address == source_address,
                    model.Alias.target == target_address).one()

        click.echo("Alias already exists: {}".format(alias))

    except NoResultFound:
        alias = model.Alias(address=source_address, target=target_address, active=active)

        model.DBSession.add(alias)
        model.DBSession.commit()

        click.echo("Alias added: {}".format(alias))


@cli.group()
@click.pass_context
def user(ctx):
    """Manage VMailbox table."""


@user.command(name="list")
@click.pass_context
def user_list(ctx):
    """List all virtual users."""

    users = model.VMailbox.query.all()

    for user in users:
        click.echo(user)


@user.command(name="add")
@click.argument("address_name")
@click.option("--active/--inactive", default=True)
@click.option("--uid", "-u", default=500)
@click.option("--gid", "-g", default=500)
@click.option("--home", "-H", default=None)
@click.option("--password", "-p", prompt=True, hide_input=True,
              confirmation_prompt=True)
@click.pass_context
def user_add(ctx, address_name, active, uid, gid, home, password):
    """Add a virtual user."""

    address = ctx.invoke(address_add, address_name=address_name)

    try:
        user = model.VMailbox.query.filter(model.VMailbox.address == address).one()

        click.echo("User already exists: {}".format(user))

    except NoResultFound:
        user = model.VMailbox(
            address=address, active=active, uid=uid, gid=gid, password=md5.md5(password).hexdigest()
        )

        model.DBSession.add(user)
        model.DBSession.commit()

        click.echo("User added: {}".format(user))

