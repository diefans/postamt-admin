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
              type=click.Path(file_okay=True), envvar="POSTAMT_DB")
@click.pass_context
def cli(ctx, debug, db):
    """Manage postamt sqlite database."""

    engine = create_engine('sqlite:///{db}'.format(db=db))
    model.initialize_sql(engine)

    ctx.obj['DEBUG'] = debug
    ctx.obj['DB'] = db
    ctx.obj['ENGINE'] = engine


def init_db(engine):
    model.create_model(engine)

    # create local domain
    try:
        local_domain = model.Domain.query.filter(model.Domain.id == 0).one()

    except NoResultFound:
        local_domain = model.Domain(id=0)
        model.DBSession.add(local_domain)

    try:
        nul_address = model.Address.query.filter(model.Address.id == 0).one()

    except NoResultFound:
        null_address = model.Address(
            id=0, domain=local_domain, localpart="\0", active=False, rclass=None, transport=None)
        model.DBSession.add(null_address)

    model.DBSession.commit()


@cli.command()
@click.option("--reset", "-r", default=False, is_flag=True)
@click.pass_context
def init(ctx, reset):
    """Init or reset the whole postamt database."""

    if os.path.isfile(ctx.obj['DB']) and reset and click.confirm('Really reset db?'):
        os.unlink(ctx.obj['DB'])

    if not os.path.isfile(ctx.obj['DB']):
        init_db(ctx.obj['ENGINE'])
        click.echo("Database initialized: {}".format(ctx.obj['DB']))


@cli.group()
@click.pass_context
def domain(ctx):
    """Manage Domain table."""

    # implicitelly init db if not existing
    if not os.path.isfile(ctx.obj['DB']):
        ctx.invoke(init)


@domain.command(name="list")
@click.pass_context
def domain_list(ctx):
    """Show all domains."""

    domains = model.Domain.query.all()

    for domain in domains:
        click.echo(domain)


class DomainClass(click.ParamType):
    name = 'domain class'
    type_map = {
        'internet': 0,
        'local': 1,
        'relay': 2,
        'alias': 3,
        'virtual': 801
    }

    def convert(self, value, param, ctx):

        try:
            if value in self.type_map:
                return self.type_map[value]

            # else it must be a number
            elif int(value) in self.type_map.values() or int(value) > 800:
                return int(value)

        except ValueError:
            self.fail('%s is not a valid domain class (0, 1, 2, 3, >800)' % value, param, ctx)


@domain.command(name="add")
@click.argument("domain_name")
@click.option("--active/--inactive", default=True)
# TODO make class either 0, 1, 2, 3 or a number above 800
@click.option("klass", "--class", "-c", default="virtual", type=DomainClass())
@click.option("--rclass", "-r", default="30",
              type=click.Choice(["00", "01", "10", "20", "29", "30", "40", "50"]))
@click.pass_context
def domain_add(ctx, domain_name, active, klass, rclass):
    """Add a new doman."""

    # test if already there
    domain = model.Domain.find(domain_name)

    if domain:
        click.echo("Domain already exists: {}".format(domain_name))

    else:
        domain = model.Domain(name=domain_name, active=active, klass=klass, rclass=rclass)
        model.DBSession.add(domain)

        # add default addresses
        postmaster = model.Address(localpart='postmaster', domain=domain)
        model.DBSession.add(postmaster)

        abuse = model.Address(localpart='abuse', domain=domain)
        model.DBSession.add(abuse)

        model.DBSession.commit()

        click.echo("Domain added: {}".format(domain))

    return domain


@domain.command(name="rm")
@click.argument("domain_name")
@click.pass_context
def domain_remove(ctx, domain_name):
    """Remove a domain."""

    domain = model.Domain.find(domain_name)

    if domain is None:
        click.echo("Domain not found: {}".format(domain_name))

    else:
        if not domain.addresses and not domain.transports:

            model.DBSession.delete(domain)
            model.DBSession.commit()

            click.echo("Domain removed: {}".format(domain_name))

        else:

            click.echo("There are addresses or transports left - remove them first explicitelly!")
            for address in domain.addresses:
                click.echo("Address: {}".format(address))

            for transport in domain.transports:
                click.echo("Transport: {}".format(transport))


@cli.group()
@click.pass_context
def address(ctx):
    """Manage Address table."""

    # implicitelly init db if not existing
    if not os.path.isfile(ctx.obj['DB']):
        ctx.invoke(init)



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

    # domain lookup and default add
    domain = model.Domain.find(domain_name)
    if not domain:
        domain = ctx.invoke(domain_add, domain_name=domain_name)

    address = model.Address.find(address_name)

    if address:
        click.echo("Address already exists: {}".format(address))

    else:
        address = model.Address(localpart=localpart, domain=domain, active=active, rclass=rclass)

        model.DBSession.add(address)
        model.DBSession.commit()

        click.echo("Address added: {}".format(address))

    return address


@address.command(name="rm")
@click.argument("address_name")
@click.pass_context
def address_remove(ctx, address_name):
    """Remove an address."""

    localpart, domain_name = address_name.split("@", 1)

    address = model.Address.find(address_name)

    if address is None:
        click.echo("Address not found: {}".format(address_name))

    else:

        if not address.sources and not address.targets:
            model.DBSession.delete(address)
            model.DBSession.commit()

            click.echo("Address removed: {}".format(address_name))

        else:
            click.echo("There are still aliases around, which relate to this address -"
                       " please remove them first!")

            for as_source in address.sources:
                click.echo("Source for: {}".format(as_source))

            for as_target in address.targets:
                click.echo("Target for: {}".format(as_target))


@cli.group()
@click.pass_context
def alias(ctx):
    """Manage Alias table."""

    # implicitelly init db if not existing
    if not os.path.isfile(ctx.obj['DB']):
        ctx.invoke(init)


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

    source = model.Address.find(source_address)
    if not source:
        source = ctx.invoke(address_add, address_name=source_address)

    target = model.Address.find(target_address)
    if not target:
        target = ctx.invoke(address_add, address_name=target_address)

    try:
        alias = model.Alias.query\
            .filter(model.Alias.address == source,
                    model.Alias.target == target).one()

        click.echo("Alias already exists: {}".format(alias))

    except NoResultFound:
        alias = model.Alias(address=source, target=target, active=active)

        model.DBSession.add(alias)
        model.DBSession.commit()

        click.echo("Alias added: {}".format(alias))


@alias.command(name="rm")
@click.argument("source_address")
@click.argument("target_address")
@click.pass_context
def alias_remove(ctx, source_address, target_address):
    """Remove an alias."""

    source = model.Address.find(source_address)
    target = model.Address.find(target_address)

    try:
        alias = model.Alias.query\
            .filter(model.Alias.address == source,
                    model.Alias.target == target).one()

    except NoResultFound:
        click.echo("There is not such alias: {} -> {} ".format(source_address, target_address))

    else:
        model.DBSession.delete(alias)
        model.DBSession.commit()

        click.echo("Alias removed: {} -> {}".format(source_address, target_address))


@cli.group()
@click.pass_context
def user(ctx):
    """Manage VMailbox table."""

    # implicitelly init db if not existing
    if not os.path.isfile(ctx.obj['DB']):
        ctx.invoke(init)


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


@user.command(name="rm")
@click.argument("address_name")
@click.pass_context
def user_remove(ctx, address_name):
    localpart, domain_name = address_name.split("@", 1)

    try:
        user = model.VMailbox.query\
            .join(model.Address, model.Domain)\
            .filter(model.Address.localpart == localpart)\
            .filter(model.Domain.name == domain_name)\
            .one()

        model.DBSession.delete(user)
        model.DBSession.commit()

        click.echo("User removed: {}".format(address_name))

    except NoResultFound:
        click.echo("User not found: {}".format(address_name))
