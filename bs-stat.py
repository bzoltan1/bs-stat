#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright © 2022 SUSE LLC
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; version 2.1.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Zoltán Balogh <zbalogh@suse.com>


from pathlib import Path
from osctiny import Osc
from lxml import objectify, etree
import sys
import ldap3
import re
from functools import cache
from os import environ as env
from shelved_cache import PersistentCache
import cachetools


from dotenv import load_dotenv
load_dotenv()


server_uri = env['LDAP_SERVER_URI']
search_base = env['SEARCH_BASE']
attrs = ['*']
server = ldap3.Server(server_uri)
project = env['PROJECT']

osc = Osc(
    url=env['API_URL'],
    username=env['OBS_USERNAME'],
    password=None,
    ssh_key_file=Path(env['SSH_KEY_FILE'])
)

project_cache_file = project.replace(':', '_')

package_cache = PersistentCache(
    cachetools.LRUCache, '%s.pkg.cache' % project_cache_file, maxsize=20000)
users_cache = PersistentCache(
    cachetools.LRUCache, '%s.usr.cache' % project_cache_file, maxsize=512)


@cache
def remove_umlaut(string):
    replacements = {
        'ü': b'ue',
        'Ü': b'Ue',
        'ä': b'ae',
        'Ä': b'Ae',
        'ö': b'oe',
        'Ö': b'Oe',
        'ß': b'ss',
    }
    string = string.encode()
    for k, v in replacements.items():
        string = string.replace(k.encode(), v)
    return string.decode('utf-8')


@cachetools.cached(users_cache)
def get_user(name):
    return osc.users.get(name)


@cachetools.cached(users_cache)
def get_manager(name, email):
    if "suse.com" in email:
        filter_string = "(mail=%s)" % email
    else:
        filter_string = "(name=%s)" % remove_umlaut(name)
    with ldap3.Connection(server, auto_bind=True, check_names=False) as conn:
        try:
            r = conn.search(
                search_base, filter_string, attributes=attrs)
            if r and 'manager' in conn.entries[0]:
                z = re.match(
                    "cn=([^,]*),", str(conn.entries[0]['manager']))
                return z.group(1)
            else:
                return ""
        except Exception:
            return ""


@cachetools.cached(package_cache)
def get_pkg_info(pkg_name):
    owner = osc.search.search(
        "owner", xpath=None, package="%s" % pkg_name)
    roles = {}
    for e in owner:
        owner = e.find('owner')
        if owner is None:
            break
        group = e.owner.find('group')
        if group is not None:
            roles[e.owner.group.attrib['role']
                  ] = e.owner.group.attrib['name']
        person = e.owner.find('person')
        if person is not None:
            maintainer = get_user(e.owner.person.attrib['name'])
            role = e.owner.person.attrib['role']
            for m in maintainer:
                login = m.login.text
                email = m.email.text
                name = m.realname.text
                manager = get_manager(name, email)
            roles[role] = "login: %s  - email: %s  - name: %s -  manager: %s" % (
                login, email, name, manager)
    return str(roles)


def extract_pkg_info(project):
    packages_collection = osc.search.search(
        "package/id", xpath="@project=\'%s\'" % project)
    for e in packages_collection.package:
        package_name = e.attrib['name']
        print(package_name, get_pkg_info(package_name))


extract_pkg_info(project)
