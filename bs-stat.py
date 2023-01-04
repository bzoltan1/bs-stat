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
import ldap3
import re
from functools import cache
from os import environ as env
from shelved_cache import PersistentCache
import cachetools
from dotenv import load_dotenv
load_dotenv()

person_detail = env['PERSON_DETAIL'].lower() in ('true', '1', 't')

if person_detail:
    server_uri = env['LDAP_SERVER_URI']
    search_base = env['SEARCH_BASE']
    attrs = ['*']
    server = ldap3.Server(server_uri)

project = env['PROJECT']


if 'OBS_PASSWORD' in env:
    osc = Osc(
        url=env['API_URL'],
        username=env['OBS_USERNAME'],
        password=env['OBS_PASSWORD'],
        ssh_key_file=None
    )
else:
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
            r = conn.search(search_base,
                            filter_string,
                            attributes=attrs)
            if not r:
                filter_string = "(name=%s)" % remove_umlaut(name)
                r = conn.search(search_base, filter_string, attributes=attrs)
            if r and 'manager' in conn.entries[0]:
                z = re.match("cn=([^,]*),", str(conn.entries[0]['manager']))
                return z.group(1)
            else:
                return ""
        except Exception:
            return ""


@cachetools.cached(package_cache)
def get_pkg_info(pkg_name):
    osc_search_result = osc.search.search("owner",
                                          xpath=None,
                                          package="%s" % pkg_name)
    roles = []
    for e in osc_search_result:
        owners = e.findall('owner')
        if owners is None:
            break
        for owner in owners:
            if owner.attrib.get('package') is None:
                group = owner.find('group')
                if group is not None:
                    roles.append("%s - " % owner.group.attrib['role'] +
                                 "group: %s" % owner.group.attrib['name'])
                continue
            persons = owner.findall('person')
            if persons is not None:
                for person in persons:
                    user = get_user(person.attrib['name'])
                    role = person.attrib['role']
                    for m in user:
                        login = m.login.text
                        email = m.email.text
                        name = m.realname.text
                        if person_detail:
                            manager = get_manager(name, email)
                            st_manager = " -  1st: " +\
                                         "%s" % manager

                            nd_manager = " -  2nd: " +\
                                         "%s" % get_manager(manager, "")
                        else:
                            st_manager = ""
                            nd_manager = ""
                    roles.append("%s - " % role +
                                 "login: %s  - " % login +
                                 "email: %s  - " % email +
                                 "name: %s" % name +
                                 "%s%s" % (st_manager, nd_manager))
            group = owner.find('group')
            if group is not None:
                roles.append("%s - " % owner.group.attrib['role'] +
                             "group: %s" % owner.group.attrib['name'])
    return str(roles)


def extract_pkg_info(project):
    packages_collection = osc.search.search(
        "package/id", xpath="@project=\'%s\'" % project)

    if packages_collection.find('package') is not None:
        for e in packages_collection.package:
            package_name = e.attrib['name']
            print(package_name, get_pkg_info(package_name))


extract_pkg_info(project)
