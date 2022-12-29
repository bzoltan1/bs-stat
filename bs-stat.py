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


server_uri = ''
search_base = ''
attrs = ['*']
server = ldap3.Server(server_uri)
name_list={}

osc = Osc(
    url="",
    username="",
    password=None,
    ssh_key_file=Path("")
)

packages_collection=osc.search.search("package/id", xpath="@project=''")

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
    for k, v in replacements:
        string = string.replace(k.encode(), v)
    string = string.decode('utf-8')
    return string

for e in packages_collection.package:
    package_name = e.attrib['name']
    maintainer=osc.search.search("owner", xpath=None, package="%s" % package_name)
    roles={}
    for e in maintainer:
        owner = e.find('owner')
        if owner is None:
            break
        group = e.owner.find('group')
        if group is not None:
            roles[e.owner.group.attrib['role']] = e.owner.group.attrib['name']
        person = e.owner.find('person')
        if person is not None:
            maintainer=osc.users.get(e.owner.person.attrib['name'])
            for m in maintainer:
                login = m.login.text
                email = m.email.text
                name = m.realname.text
                if name not in name_list:
                    if "suse.com" in email:
                        filter_string = "(mail=%s)" % email
                    else:
                        filter_string = "(name=%s)" % remove_umlaut(name)
                    with ldap3.Connection(server, auto_bind=True, check_names=False) as conn:
                        try:
                            r = conn.search(search_base, filter_string, attributes=attrs)
                            if r and 'manager' in conn.entries[0]:
                                z = re.match("cn=([^,]*),", str(conn.entries[0]['manager']))
                                name_list[name] = z.group(1)
                            else:
                                name_list[name] = ""
                        except Exception:
                           name_list[name] = ""

            roles[e.owner.person.attrib['role']] = "login: %s  - email: %s  - name: %s -  manager: %s" % (login, email, name, name_list[name])

    print("%s %s" % (package_name, roles))

