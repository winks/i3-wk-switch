#!/usr/bin/python

"""Emulates xmonad's workspace switching behavior in i3"""

# pylint: disable=no-member

import logging
import sys
from pprint import pformat
import i3
import time
import re


LOG = logging.getLogger()
PAT = re.compile(r'\s*\d+\s*:.+')

def setup_logger(level):
    """Initializes logger with debug level"""
    LOG.setLevel(logging.DEBUG)
    channel = logging.FileHandler("/tmp/i3-wk-switcher.log")
    channel.setLevel(level)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    channel.setFormatter(formatter)
    LOG.addHandler(channel)


def get_focused_workspace():
    """Get workspace that is currently focused"""
    actives = [wk for wk in i3.get_workspaces() if wk['focused']]
    assert len(actives) == 1
    return actives[0]


def get_active_outputs():
    """Returns outputs (monitors) that are active"""
    return [outp for outp in i3.get_outputs() if outp['active']]


def get_workspace(num):
    """Returns workspace with num or None of it does not exist"""
    want_workspace_cands = [wk for wk in i3.get_workspaces()
                            if wk['num'] == num]
    assert len(want_workspace_cands) in [0, 1]

    if len(want_workspace_cands) == 0:
        return None
    else:
        return want_workspace_cands[0]


def switch_workspace(num, name=None):
    """Switches to workspace number"""
    if name is None:
        i3.workspace('number %d' % num)
    else:
        i3.workspace('%d:%s' % (num, name))


def swap_visible_workspaces(wk_a, wk_b):
    """Swaps two workspaces that are visible"""
    switch_workspace(wk_a['num'])
    i3.command('move', 'workspace to output ' + wk_b['output'])
    switch_workspace(wk_b['num'])
    i3.command('move', 'workspace to output ' + wk_a['output'])


def change_workspace(num):
    """
    Switches to workspace num like xmonad.

    Always sets focused output to workspace num. If the workspace is on
    another output, then the workspaces are "shifted" among the outputs.
    """

    if re.match(PAT, num):
        num, name = map(str.strip, num.split(':'))
    else:
        name = None
    num = int(num)
    focused_workspace = get_focused_workspace()
    original_output = focused_workspace['output']

    LOG.debug('Switching to workspace:{} on output:{}, display: {}:'.format(
        num, focused_workspace['output'], pformat(focused_workspace, indent=2)))

    # Check if already on workspace
    if int(focused_workspace['num']) == num:
        LOG.debug('Already on correct workspace')
        return

    # Get workspace we want to switch to
    want_workspace = get_workspace(num)
    if want_workspace is None:
        LOG.debug('Switching to workspace because it does not exist, i3 will create it')
        switch_workspace(num, name)
        return

    LOG.debug('Want workspace:\n' + pformat(want_workspace, indent=2))

    # Save workspace originally showing on want_workspace's output
    other_output = [outp for outp in get_active_outputs()
                    if outp['name'] == want_workspace['output']][0]
    LOG.debug('Other_output=%s', pformat(other_output, indent=2))
    other_workspace = [wk for wk in i3.get_workspaces()
                       if wk['name'] == other_output['current_workspace']][0]
    LOG.debug('Other workspace:\n' + pformat(other_workspace, indent=2))


    # Check if wanted workspace is on focused output
    if focused_workspace['output'] == want_workspace['output']:
        LOG.debug('Wanted workspace already on focused output, '
                  'switching as normal')
        switch_workspace(num, name)
        return

    # Check if wanted workspace is on other output
    if not want_workspace['visible']:
        LOG.debug('Workspace to switch to is hidden')

        # Switch to workspace on other output
        switch_workspace(num, name)

    LOG.debug('Wanted workspace is on other output')

    # Wanted workspace is visible, so swap workspaces
    swap_visible_workspaces(want_workspace, focused_workspace)

    # Focus other_workspace
    switch_workspace(other_workspace['num'], name)

    # Focus on wanted workspace
    time.sleep(.15)
    LOG.debug('Setting focus to {}'.format(original_output))
    i3.command('focus', 'output', original_output)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Usage: %s WORKSPACE_NUM' % sys.argv[0]
        sys.exit(1)

    setup_logger(logging.DEBUG)
    try:
        change_workspace(sys.argv[1])
    except Exception:
        LOG.exception('An error occured')
