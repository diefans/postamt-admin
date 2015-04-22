from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker

from pyramid.config import Configurator


def db(request):
    """every request will have a session associated with it. and will
    automatically rollback if there's any exception in dealing with
    the request
    """
    maker = request.registry.dbmaker
    session = maker()

    def cleanup(request):
        if request.exception is not None:
            session.rollback()
        else:
            session.commit()
        session.close()

    request.add_finished_callback(cleanup)

    return session


def config_static(config):
    config.add_static_view('static', path='postamt:client/build/', cache_max_age=3600)


def config_jinja2(config):
    config.include('pyramid_jinja2')
    config.add_jinja2_renderer('.html')
    config.add_jinja2_search_path('templates', name='.html')


def config_db(config, settings):
    # configure database with variables sqlalchemy.*
    engine = engine_from_config(settings, prefix="sqlalchemy.")
    config.registry.dbmaker = sessionmaker(bind=engine)

    # add db session to request
    config.add_request_method(db, reify=True)


def main(global_config, **settings):        # pylint: disable=W0613
    """Create wsgi application."""

    config = Configurator(
        settings=settings,
    )

    #config.include('postamt.security')

    config_static(config)
    config_jinja2(config)

    config_db(config, settings)

    # config.include('kb.renderer') conflicts with cornice
    #renderer.includeme(config)

    config.include("postamt.models")

    config.scan()
    return config.make_wsgi_app()
