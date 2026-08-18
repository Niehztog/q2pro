#!/usr/bin/env python3
"""Enforce the pm_time unit contract at build time.

`pmove_state_t.pm_time` does not have a fixed unit.  Under the original
protocol it is a byte whose unit is 8ms; once protocol extensions are
negotiated it is a uint16_t whose unit is 1ms.  See `pmove_state_old_t`
and `pmove_state_new_t` in inc/shared/shared.h.

Game code therefore may not write a millisecond duration into the field
directly.  It has to divide by the unit first, which is what the game
libraries' PM_TIME_SHIFT (game.csr.extended ? 0 : 3) and the engine
pmove's PMOVE_TIME_SHIFT exist for.  A write that skips the shift is not
a compile error and is not wrong under the unextended protocol -- it is
the spelling every pre-extension source used -- so it survives a merge,
a rebase and a replay untouched, and then holds the player for an eighth
of the intended time the moment a client negotiates extensions.

Nothing about the field's type says which unit a given site is in, so
this contract can only be checked as text.  That is the same shape as
the four contracts in doc/mission-packs.md, and it broke the same way:
q2pro's `Support more protocol extensions.` introduced PM_TIME_SHIFT in
baseq2, the mission-pack replay carried that commit as a diff, and a
diff only reaches files baseq2 also has -- so g_misc.c and p_client.c
were converted in all three packs while Threewave's own g_ctf.c and
Ground Zero's own g_newtrig.c kept the pre-extension spelling.

A write to pm_time passes only if it is one of these:

  0     assigning literal zero cancels an outstanding hold.  It is the
        same value in both units, so it needs no conversion.
  shift the right-hand side names PM_TIME_SHIFT or PMOVE_TIME_SHIFT, so
        whatever duration it builds went through the unit conversion.
  copy  the right-hand side names pm_time, so it moves a value that is
        already in protocol units rather than making a new duration.
  wire  the right-hand side is an MSG_Read*() call, so the value arrives
        from the network already in protocol units.
  adjust a compound assignment with no numeric literal on the right, so
        it adjusts an existing hold rather than constructing one.

Anything else is rejected, including a bare variable: a site that cannot
show where its unit came from is exactly the site this check is for.

Out of scope: src/server/mvd.c, which does write the field, but through
PPS_INUSE() -- protocol.h deliberately repurposes the byte as an in-use
flag in MVD packet player states.  Those writes are booleans, not
durations, and the field there never reaches a pmove.

Usage:
    pm_time_check.py --self-test          run the control, below
    pm_time_check.py PATH...              scan files and directories
"""

import os
import re
import sys

# An assignment to pm_time.  The lookbehind keeps `foo_pm_time` out, and
# the (?!=) keeps `==` out; `!=`, `<=` and `>=` never reach the operator
# group because their first character is not in it.
ASSIGN_RE = re.compile(
    r'(?<![A-Za-z0-9_])pm_time\s*(?P<op>[-+*/|&^]?=)(?!=)\s*(?P<rest>.*)$')

SHIFT_RE = re.compile(r'(?<![A-Za-z0-9_])(PM_TIME_SHIFT|PMOVE_TIME_SHIFT)\b')
COPY_RE = re.compile(r'(?<![A-Za-z0-9_])pm_time\b')
WIRE_RE = re.compile(r'\bMSG_Read[A-Za-z]*\s*\(')
# A decimal, hex or octal integer constant, with C's suffixes.
NUMBER_RE = re.compile(r'(?<![A-Za-z0-9_.])(?:0[xX][0-9a-fA-F]+|\d+)[uUlL]*\b')

SCAN_ROOTS = [
    'src/game', 'src/ctf', 'src/xatrix', 'src/rogue',
    'src/common/pmove', 'src/common/msg.c',
]


def classify(rhs, op):
    """Return None if this right-hand side is allowed, else why it is not."""
    if SHIFT_RE.search(rhs):
        return None
    if COPY_RE.search(rhs):
        return None
    if WIRE_RE.search(rhs):
        return None

    literals = NUMBER_RE.findall(rhs)
    stripped = rhs.strip()

    if op == '=' and stripped == '0':
        return None
    if op != '=' and not literals:
        return None

    if not literals:
        return ('writes `%s`, whose unit cannot be seen here; a duration '
                'must be built with PM_TIME_SHIFT' % stripped)

    # Work out what the site meant, so the diagnostic can say it.  A bare
    # literal N is a pre-extension author writing N protocol units; an
    # `N >> 3` is one writing N milliseconds with the shift hardcoded.
    hardcoded = re.match(r'^(\d+)\s*>>\s*3$', stripped)
    if hardcoded:
        want = int(hardcoded.group(1))
        return ('writes `%s`: %dms with the shift hardcoded, so an '
                'extended server holds for %dms, an eighth of it. '
                'Write `%d >> PM_TIME_SHIFT`.'
                % (stripped, want, want >> 3, want))
    bare = re.match(r'^(\d+)$', stripped)
    if bare:
        units = int(bare.group(1))
        return ('writes `%s`: %d protocol units, so a plain server holds '
                'for %dms and an extended one for %dms, an eighth of it. '
                'Write `%d >> PM_TIME_SHIFT`.'
                % (stripped, units, units * 8, units, units * 8))
    return ('writes `%s`, which builds a duration without PM_TIME_SHIFT'
            % stripped)


def scan_text(name, text):
    """Yield (line number, source line, reason) for each bad write."""
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        # Drop a trailing // comment so its text cannot be mistaken for code.
        code = line.split('//')[0]
        m = ASSIGN_RE.search(code)
        if not m:
            continue
        rest = m.group('rest')
        if ';' not in rest:
            findings.append((lineno, line.strip(),
                             'assignment does not end on this line; this '
                             'check reads one statement per line'))
            continue
        reason = classify(rest.split(';')[0], m.group('op'))
        if reason:
            findings.append((lineno, line.strip(), reason))
    return findings


def scan_path(path):
    findings = []
    if os.path.isdir(path):
        for root, dirs, names in sorted(os.walk(path)):
            dirs.sort()
            for name in sorted(names):
                if name.endswith(('.c', '.h')):
                    findings += scan_path(os.path.join(root, name))
        return findings
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for lineno, line, reason in scan_text(path, f.read()):
            findings.append((path, lineno, line, reason))
    return findings


# The control.  Each defect below is the verbatim text of a site this
# check was written for, as it stood before it was fixed; each accepted
# case is the verbatim text of a site that must keep building.  Running
# it as part of the check means a change that stops the check finding
# anything fails the build too, instead of passing quietly.
CONTROL_DEFECTS = [
    # src/ctf/g_ctf.c, CTFTeam_f() -- a spectator joining a team.
    '        ent->client->ps.pmove.pm_time = 14;',
    # src/ctf/g_ctf.c, CTFJoinTeam() -- the same, from the join menu.
    '    ent->client->ps.pmove.pm_time = 14;',
    # src/ctf/g_ctf.c, CTFTeleporterTouch().
    '    other->client->ps.pmove.pm_time = 160 >> 3;     // hold time',
    # src/rogue/g_newtrig.c, trigger_teleport_touch().
    '        other->client->ps.pmove.pm_time = 160 >> 3;     // hold time',
    # Not a site that existed, but the hole a bare variable would leave.
    '    ent->client->ps.pmove.pm_time = hold_msec;',
]

CONTROL_ACCEPTED = [
    '        self->client->ps.pmove.pm_time = 112 >> PM_TIME_SHIFT;',
    '    other->client->ps.pmove.pm_time = 160 >> PM_TIME_SHIFT;  // hold time',
    '                        pm->s.pm_time = 200 >> PMOVE_TIME_SHIFT;',
    '    pm->s.pm_time = 2040 >> PMOVE_TIME_SHIFT;',
    '                pm->s.pm_time = 0;',
    '    out->pmove.pm_time = in->pmove.pm_time;',
    '            to->pmove.pm_time = MSG_ReadWord();',
    '            to->pmove.pm_time = MSG_ReadByte();',
    '        pm->s.pm_time -= msec;',
    # Reads, which are not writes and must never be reported.
    '    if (pm->s.pm_time)',
    '        if (msec >= pm->s.pm_time) {',
    '    if (to->pmove.pm_time != from->pmove.pm_time)',
    '#define PPS_INUSE(ps)       (ps)->pmove.pm_time',
]


def self_test():
    failures = []
    for src in CONTROL_DEFECTS:
        if not scan_text('<control>', src):
            failures.append('not reported, but must be: %s' % src.strip())
    for src in CONTROL_ACCEPTED:
        found = scan_text('<control>', src)
        if found:
            failures.append('reported, but must not be: %s -- %s'
                            % (src.strip(), found[0][2]))
    if failures:
        sys.stderr.write('pm_time_check: the check itself is broken:\n')
        for f in failures:
            sys.stderr.write('  %s\n' % f)
        return 1
    sys.stderr.write('pm_time_check: control passed (%d defects caught, '
                     '%d accepted forms left alone)\n'
                     % (len(CONTROL_DEFECTS), len(CONTROL_ACCEPTED)))
    return 0


def main(argv):
    if '--self-test' in argv:
        return self_test()

    paths = [a for a in argv if not a.startswith('-')]
    if not paths:
        root = os.path.dirname(os.path.abspath(__file__))
        paths = [os.path.join(root, p) for p in SCAN_ROOTS]

    findings = []
    for path in paths:
        findings += scan_path(path)
    if not findings:
        return 0

    sys.stderr.write('pm_time_check: %d write(s) to pm_time build a duration '
                     'without the protocol shift:\n' % len(findings))
    for path, lineno, line, reason in findings:
        sys.stderr.write('%s:%d: error: %s\n' % (path, lineno, reason))
        sys.stderr.write('  %s\n' % line)
    sys.stderr.write('pm_time is 8ms per unit on a plain server and 1ms per '
                     'unit once protocol extensions are negotiated; see '
                     'PM_TIME_SHIFT in the game g_local.h.\n')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
