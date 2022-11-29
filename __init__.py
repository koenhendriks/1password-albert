# -*- coding: utf-8 -*-

"""1Password extension for Albert Launcher.

This extension allows you to search through your 1password account
and copy either the password (default), or the 2fa code (totp).

Authentication is done through a session token using 1password-cli. 
Prefix any query with 'op' to start using the extension. If there
is no current session you will be asked to login using the 1password-cli

Synopsis: op <query>"""

from albert import *
import os
import subprocess
import json
from time import sleep

__title__ = "1Password"
__version__ = "0.1.0"
__triggers__ = "op "
__authors__ = "Koen Hendriks, Thom Bakker"
__exec_deps__ = ["op", "xclip"]
__py_deps__ = ["os", "subprocess", "json", "sleep"]

iconPath = os.path.dirname(__file__) + "/1password-icon.svg"
tokenFile = os.path.dirname(__file__) + "/.sessionToken"

session_token = ""
op_items = []
should_reload = False


# Simple method to get the last word from a string
def last_word(string):
    lis = list(string.split(" "))
    length = len(lis)
    return lis[length - 1]


# Load a session token from file if it's available.
def initialize():
    global session_token
    global op_items
    global should_reload

    should_reload = False
    session_token = open(tokenFile, 'r').read()

    debug("[op] Read token [" + session_token + "] from " + tokenFile + " ")

    if logged_in():
        debug("[op] Loading initial 1password items")
        json_list = subprocess.run(
            ['op', 'item', 'list', '--format', 'json', '--session', session_token],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        ).stdout.decode("utf-8")

        op_items = json.loads(json_list)

    pass


# Check if 1password-cli can be accessed with current session token.
# Because there is a bug in the 'op whois' command we retrieve the list
# with a custom tag that barely cost us resources.
#
# @see https://1password.community/discussion/comment/665666
def logged_in():
    global should_reload
    global session_token

    # after a login we need to reinitialize the extension for the new session token.
    if should_reload:
        initialize()

    status = subprocess.run(
        ['op', 'item', 'list', '--tags', 'checkCLILogin', '--session', session_token],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    ).stdout.decode("utf-8")

    debug("[op] Logged in cli response: " + status)

    if "You are not currently signed in" in status:
        return False
    else:
        return True


# Get 1Password items. Will filter result on title in 1Password by given filter.
def get_items(op_item_filter):
    global session_token
    global op_items
    items = []

    backup_id = 1337

    for opItem in op_items:
        if op_item_filter.lower() not in opItem.get('title', '').lower():
            continue

        backup_id += 1

        item = Item()
        item.id = opItem.get('id', str(backup_id))
        item.icon = iconPath
        item.text = opItem.get('title', 'error on 1Password item title')
        item.subtext = 'Category: ' + opItem.get('category', 'error on 1password item category')

        item.actions = [
            ProcAction(
                "Copy password",
                [
                    "sh",
                    "-c",
                    f"op item get " + item.id + " --fields password --session " + session_token + " |  tr -d '\\n' | xclip -selection clipboard -in",
                ],
            ),
            ProcAction(
                "Copy TOTP code",
                [
                    "sh",
                    "-c",
                    f"op item get " + item.id + " --session " + session_token + " --fields 'one-time password' --format json | jq -r .totp |  tr -d '\\n' | xclip -selection clipboard -in",
                ],
            )
        ]

        items.append(item)

    return items


def handleQuery(query):
    global should_reload

    if not query.isTriggered:
        return

    if not logged_in():
        should_reload = True
        return Item(id=__title__,
                    icon=iconPath,
                    text="Press enter to login using 1Password CLI",
                    actions=[
                        TermAction(text='Login to 1Password on CLI',
                                   script="op signin --raw > " + tokenFile,
                                   behavior=TermAction.CloseBehavior.CloseOnExit,
                                   cwd='~')
                    ])

    return get_items(op_item_filter=query.string)
