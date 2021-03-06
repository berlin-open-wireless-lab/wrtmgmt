import json
from .utils import generate_device_uuid_str, id_generator

from .models import (
    DBSession,
    OpenWrt
    )

from openwifi.jobserver.tasks import exec_on_device

from cornice import Service
from cornice.resource import resource, view

from openwifi.authentication import get_node_by_request, RootFactory
from openwifi import node_context

@resource(collection_path='/nodes', path='/nodes/{UUID}', permission='view', factory='openwifi.node_context')
class Nodes(object):

    def __init__(self, request, context):
        self.request = request
        self.context = context

    @view(permission = 'view')
    def collection_get(self):
        from openwifi.authentication import get_nodes
        uuids = []
        for openwrt in get_nodes(self.request):
            uuids.append(str(openwrt.uuid))
        return uuids

    # add new openwifi node
    @view(permission = 'node_add')
    def collection_post(self):
        newNodeData = self.request.json_body
        if 'uuid' in newNodeData.keys() and newNodeData['uuid']:
            uuid = newNodeData['uuid']
        else:
            uuid = generate_device_uuid_str(id_generator())
        ap = OpenWrt(newNodeData['name'], newNodeData['address'], newNodeData['distribution'], newNodeData['version'], uuid, newNodeData['login'], newNodeData['password'], False)
        DBSession.add(ap)
        return str(ap.uuid)

    @view(permission='node_access')
    def get(self):
        openwrt = get_node_by_request(self.request)
        return openwrt.jsonParsable()

    # modify node TODO: add validator
    @view(permission = 'node_access')
    def post(self):
        openwrt = get_node_by_request(self.request)

        if not openwrt:
            return False

        modData = json.loads(self.request.body.decode())

        for key, value in modData.items():
            openwrt.setData(key, value)

        return True

    @view(permission = 'node_access')
    def delete(self):
        openwrt = get_node_by_request(self.request)
        if openwrt:
            DBSession.delete(openwrt)
            return True
        else:
            return False


execService = Service(name='execOnNode',
                      path='/nodes/{UUID}/exec',
                      description='execute command on node',
                      factory='openwifi.node_context',
                      permission='node_access')

@execService.get()
def get_execService(request):
    usage = {'command' : 'command do execute',
             'params' : ['list','of','params']}

    return usage

@execService.post()
def post_execService(request):
    query = json.loads(request.body.decode())
    uuid = request.matchdict['UUID']

    r = exec_on_device.delay(uuid, query['command'], query['params'])
    return request.route_url('execStatus', UUID=r.id)


diffNodeService = Service(name='diffFromNode',
                          path='/nodes/{UUID}/diff',
                          description='get diff list by nodes',
                          factory='openwifi.node_context',
                          permission='node_access')

@diffNodeService.get()
def get_diffNode(request):
    device = get_node_by_request(request)

    if device:
        return device.get_diff_list()

    return []

from openwifi.models import OpenWifiSettings

@resource(collection_path='/settings', path='/settings/{SETTING}', permission='settings', factory=RootFactory)
class Settings(object):

    def __init__(self, request, context=None):
        self.request = request

    def collection_get(self):
        settings = DBSession.query(OpenWifiSettings)

        result = {}
        for setting in settings:
            result[setting.key] = setting.value

        return result

    def collection_post(self):

        data = self.request.json_body
        setting_exists = DBSession.query(OpenWifiSettings).get(data['key'])

        if setting_exists:
            setting_exists.value = data['value']
        else:
            DBSession.add(OpenWifiSettings(**data))

        return True

    def delete(self):
        setting_key = self.request.matchdict['SETTING']
        DBSession.delete(DBSession.query(OpenWifiSettings).get(setting_key))

        return True

    def get(self):
        setting_key = self.request.matchdict['SETTING']
        setting = DBSession.query(OpenWifiSettings).get(setting_key)

        return setting.value

    def post(self):
        setting_key = self.request.matchdict['SETTING']
        setting = DBSession.query(OpenWifiSettings).get(setting_key)
        setting.value = self.request.json_body['value']

        return True
