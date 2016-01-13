from pyramid.config import Configurator
from sqlalchemy import engine_from_config

import ldap3

from pyramid_ldap3 import (
    get_ldap_connector,
    groupfinder)

from pyramid.security import (
   Allow,
   Authenticated,
   remember,
   forget)

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from .models import (
    DBSession,
    Base,
    )


class RootFactory(object):
    __acl__ = [(Allow, Authenticated, 'view')]
    def __init__(self, request):
        pass


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    config = Configurator(settings=settings, root_factory=RootFactory)

    config.set_authentication_policy(
        AuthTktAuthenticationPolicy(
            'seekr1t', callback=groupfinder))
    config.set_authorization_policy(
        ACLAuthorizationPolicy())

    config.ldap_setup(
        'ldap://localhost',
        bind='cn=admin,dc=OpenWifi,dc=local',
        passwd='fh\\52ENEPb\'G[y8=ne%Z+xEb3')

    config.ldap_set_login_query(
        base_dn='ou=Users,dc=OpenWifi,dc=local',
        filter_tmpl='(uid=%(login)s)',
        #filter_tmpl='(sAMAccountName=%(login)s)',
        scope=ldap3.SEARCH_SCOPE_SINGLE_LEVEL)

    config.ldap_set_groups_query(
        base_dn='CN=Users,DC=OpenWifi,DC=local',
        filter_tmpl='(&(objectCategory=Groups)(member=%(userdn)s))',
        scope=ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
        cache_period=600)

    config.add_route('login', '/login')
    config.add_route('logout', '/logout')

    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')

    config.add_route('openwrt_list', '/openwrt')
    config.add_route('openwrt_detail', '/openwrt/{uuid}')
    config.add_route('openwrt_action', '/openwrt/{uuid}/{action}')
    config.add_route('openwrt_add', '/openwrt_add')
    config.add_route('openwrt_edit_config', '/openwrt_edit_config/{uuid}')

    config.add_route('templates', '/templates')
    config.add_route('templates_add', '/templates_add')
    config.add_route('templates_assign', '/templates_assign/{id}')
    config.add_route('templates_edit', '/templates_edit/{id}')
    config.add_route('templates_delete', '/templates_delete/{id}')
    config.add_route('templates_action', '/templates/{id}/{action}')

    config.add_route('confarchive', '/confarchive')
    config.add_route('archive_edit_config', '/archive_edit_config/{id}')
    config.add_route('archive_apply_config', '/archive_apply_config/{id}')

    config.add_route('sshkeys', '/sshkeys')
    config.add_route('sshkeys_add', '/sshkeys_add')
    config.add_route('sshkeys_assign', '/sshkeys_assign/{id}')
    config.add_route('sshkeys_action', '/sshkeys/{id}/{action}')

    config.add_route('luci', '/luci')
    config.add_route('ubus', '/ubus/{command}')

    config.include('pyramid_rpc.jsonrpc')
    config.add_jsonrpc_endpoint('api', '/api')

    config.scan()
    return config.make_wsgi_app()
