Mission pack game libraries
===========================

Besides `baseq2`, this tree carries three more game libraries:

| directory    | game                              | imported from                          |
|--------------|-----------------------------------|----------------------------------------|
| `src/ctf`    | Threewave Capture The Flag 1.52   | `ctf/` in id's `quake2-3.21` release   |
| `src/xatrix` | The Reckoning (Xatrix)            | `xatrixsrc320` (id/Xatrix, 3.20)       |
| `src/rogue`  | Ground Zero (Rogue)               | `roguesrc320` (id/Rogue, 3.20)         |

They are built as `game<cpu>` libraries installed into `ctf/`, `xatrix/` and
`rogue/` respectively, so a client started with `+set game xatrix` picks the
right one up.  Which ones get built is controlled by the `mission-packs`
meson option:

    meson setup builddir -Dmission-packs=ctf,rogue

How they were produced
----------------------

The mission packs are not a fresh port: every commit q2pro has ever made to
the `baseq2` game source was replayed onto them, so they carry the same
modernisation and the same bug fixes.

1. The official sources were normalised into the exact style q2pro's own
   `Imported baseq2 game source.` commit produced (tabs to spaces, CRLF to LF,
   braced frame tables, `Com_sprintf` to `Q_snprintf`, and so on).  The
   normaliser was validated by reproducing that commit from id's `quake2-3.21`
   `game/` directory.

2. A synthetic branch was created whose root is the normalised 3.20/3.21
   `baseq2` source (the two are identical apart from the licence header), with
   q2pro's 188 game-source commits stacked on top, and a sibling branch holding
   each mission pack's divergence from that same root.

3. Each of the 188 commits was then rebased onto each mission pack, so git's
   three-way merge did the mechanical work and every genuine conflict was
   resolved by hand against the commit's intent.

Commits that are mechanical rather than semantic - the astyle pass, the
`qboolean`/`stdbool` switch, the frame-number conversions, `rand()` to
`Q_rand()`, the float suffixes, the const-ification passes - were replayed by
re-running the *transformation*, not by applying the diff.  That matters
because a diff can only touch files baseq2 has; running the transformation also
reaches `g_ctf.c`, `m_widow.c`, `m_gekk.c` and the rest of the mission packs'
own code.

Deviations worth knowing about
------------------------------

* `GAMEVERSION` stays `"baseq2"` in all three, exactly as the original sources
  had it; it only feeds the `gamename` serverinfo cvar.
* Threewave CTF has no baseq2 `spectator` flag - observers are `CTF_NOTEAM`
  players - so the spectator descriptors point at the fields Threewave uses.
* Ground Zero's `SVF_DAMAGEABLE` was `0x8`, which now collides with the
  engine's `SVF_PLAYER`; it moved to a bit the engine does not use.
* `m_move2.c` ships in the Ground Zero release but is an unused copy of
  `m_move.c`; Rogue's own Makefile does not build it and neither do we.
* `genptr.py` in each mission pack learned to skip inactive `#ifdef` blocks and
  block comments, so it stops emitting savegame pointers for functions that are
  compiled out.

Savegame state
--------------

Every descriptor the original mission packs had is represented.  A few fields
the original authors never saved were added, because the equivalent baseq2
fields are saved: the Reckoning's QuadFire timer and `max_magslug`/`max_trap`
ammo caps, and Ground Zero's Double/IR/Nuke/Tracker powerup timers.

Getting there took correcting the replay, for the reasons in the next section.

Contracts the replay could not check
-----------------------------------

Five kinds of data contract survive only as *text*, so neither the compiler nor
git's three-way merge can tell when a replayed commit breaks one.  All five were
broken here, and all five are corrected in the import above.

*Map entity keys.*  A `.bsp` names entity fields as literal strings, matched at
runtime against the key column of `spawn_fields[]`/`temp_fields[]`.  q2pro's
`Convert monster timers to frame numbers.` renames `monsterinfo_t.pausetime` to
`pause_framenum` - and `spawn_temp_t` has a member of the same name that is
*not* internal: it is the target of the `"pausetime"` row, i.e. key text that
appears in shipped maps.  Replayed tree-wide, the rename silently broke every
map that sets `pausetime` on a `func_timer`.  The key matched no row, so
`ED_ParseEdict` reported `pausetime is not a field` and `SP_func_timer` started
with no initial pause - precisely what the key exists to provide, staggering
banks of timers that would otherwise fire in lockstep.  Ground Zero compounded
it by retyping the member `int` while its row still said `F_FLOAT`, so even the
new spelling would have written a float bit pattern into an int.  Reverted in
`spawn_temp_t` only, so q2pro's genuine `monsterinfo_t` rename stands and the
`SP_func_timer` read site is byte-identical to baseq2's.  The QUAKED
documentation block is part of the same contract and was corrected with it.

*Savegame descriptors.*  id's `WriteEdict`/`WriteClient` copied whole structs
and `fwrote` them, so every member a mission pack added persisted implicitly.
q2pro's portable savegame replaces that with a per-member descriptor whitelist,
which turns "preserved by default" into "preserved only if listed" - and the
replay carried baseq2's tables without adding the packs' own rows.  Nothing
warns: the members still exist, the tables still compile, and a missing row just
means the value reads back as whatever a fresh edict has.  Ground Zero lost the
most, including two of its signature mechanics - `gravityVector` and the whole
`blindfire` set.  A row that is present can be wrong rather than missing, too:
four of Ground Zero's `monsterinfo_t` frame counters were declared with the
float macro against `int` members, so a counter like 3600 did not survive a
round trip.  `attack_finished` keeps the float macro, because Ground Zero really
did leave that member `float`.

*Statusbar stat slots.*  The third contract of the same shape, and the one that
needed the most care.  A statusbar program is a string of tokens like `if 18`,
`pic 17`, `num 2 19`; the numbers are stat slots, and they are matched against
nothing at compile time.  Threewave CTF defines its own `STAT_CTF_*` names for
slots 17 to 30, so when the replay brought in q2pro's second powerup timer
(`STAT_TIMER2_ICON`/`STAT_TIMER2`, slots 18 and 19) and its spectator indicator
(`STAT_SPECTATOR`, slot 17), two subsystems began writing the same three slots
under different names - which no compiler can see, precisely because the names
differ.  `ctf_statusbar` draws 17 and 19 with `pic`, so a chasecam viewer got
image index 1 where the team's flag icon belongs, and the pent timer never
appeared at all because that bar has no element to draw it.

The two meanings turn out to be mutually exclusive by game mode, and the bar
already knew it: `SP_worldspawn` sends `ctf_statusbar` when `ctf` is set and
`single_statusbar` + `dm_statusbar` when it is not.  So the writes are gated the
same way instead of new slots being found - which is just as well, because CTF
has only slot 31 free under the unextended protocol's 32 and the timer needs
two.  Under `ctf`, the pent shares timer 1 exactly as baseq2 did before q2pro
split the two; outside it, q2pro's dual timer and spectator indicator work
normally.  `SetCTFStats` owns 17 to 30 and now refuses to run outside CTF with
a guard clause of its own, rather than depending on its caller, or on CTF's
state happening to be zero when `ctf` is off.

Picking a "free" slot from the list of `#define`s is not enough, and that
mistake was made once in this work before being caught: a bar can reference a
slot by bare number with no macro name at all, which is invisible to any
name-based collision check.  The test that holds is set intersection against
the *pristine* statusbar - the slots it reads against the slots the replayed
code newly claims.

*Timer units.*  The fourth contract, and the one with the widest blast radius.
q2pro's `Convert ... to frame numbers.` commits retype every timer from a float
count of seconds to an `int` count of frames, so a field's *type* no longer says
what its *unit* is: `int nextthink` and `int timestamp` hold frames, `float
level.time` holds seconds, and mixing them compiles silently and runs wrong by a
factor of ten.  A mechanical replay can convert a write without its matching
read, or reach a file its diff never touched, and nothing complains.  Both
directions were live here:

  * `src/rogue/g_phys.c`'s `SV_RunThink` was never converted at all - it kept
    `float thinktime` and compared `ent->nextthink` against `level.time`, so
    *every* think in Ground Zero fired ten times late.  Measured: a door reached
    its top on frame 190 instead of frame 10.
  * Xatrix had 43 `nextthink = level.time + N` sites in ten files that the
    conversion never reached.  Under a correct `SV_RunThink` those fire
    immediately, so the two defects had been hiding each other.
  * Half-converted pairs: `monsterinfo.trail_framenum` written as
    `level.framenum` at eight sites and read against `level.time` at five;
    `last_move_framenum` written with its `* BASE_FRAMERATE` dropped and read
    against `level.time`; `edict_t.timestamp` in Xatrix's trap; and Xatrix's
    intermittent `trigger_push`, whose `delay` was fed from `nextthink` (frames)
    plus `wait` (seconds) and then compared against `level.time`.
  * Scale factors lost or doubled on an otherwise-converted site: the
    intermission wait became 0.5s, the drowning gasp threshold 1.1s, and a
    stray `/ FRAMETIME` made the quad-drop timeout ten times too long.

Not every unconverted timer is a defect.  Ground Zero really did leave
`monsterinfo.attack_finished` a float, so its 48 sites are all in seconds and
consistent; Threewave's own `resp.lastidtime` and `client.menutime` are the
same.  What makes a site wrong is *mixing*, not the choice of unit.

Two checks find them.  Cross-unit mixing: for every line mentioning
`level.time`, look for an `int`-declared timer field on the same line - a
`_framenum` fed from or compared against seconds, or the reverse.  Lost scale:
grep for `level.framenum` combined with a floating-point literal and no
`* BASE_FRAMERATE`, since a frame count is an integer and a `5.0f` next to one
is almost always a duration that forgot to be scaled.  Neither is a substitute
for the third check, which is the only one that catches a `SV_RunThink` written
entirely in the wrong unit: **run a level and wait**.  Every static check and
every spawn-time entity census in this tree stayed green with all timing ten
times wrong.  Break on a think and print `level.framenum`; the frame it fires on
must be the frame it was scheduled for.

*Configstring bases.*  The fifth contract, and the one that looks least like
one: `CS_MODELS`, `CS_PLAYERSKINS`, `CS_GENERAL` and the rest are not constants
in q2pro.  `Support more protocol extensions.` gave the engine a second, larger
configstring layout and made the choice a runtime one, so a game library reads
whichever layout `InitGame` selected out of `game.csr` - while the macros of the
same name expand to the *extended* one, because meson defines
`USE_PROTOCOL_EXTENSIONS` unconditionally.  Both spellings compile, and they
agree only when extensions are enabled, which is not the default.  That commit
reached the mission packs as a diff, so it converted every site baseq2 also has
and left Threewave's own: `CS_GENERAL + playernum` in `ClientUserinfoChanged` -
a `//ZOID` hunk inside a *shared* file, which a diff does not reach either - the
same expression in `CTFSetIDView`, and `CONFIG_CTF_MATCH`/`CONFIG_CTF_TEAMINFO`,
spelled `CS_AIRACCEL-1` and `-2`.

How it fails depends on how far out of range the index lands.  `CS_GENERAL` is
13118 extended against a 2080-slot layout, so `PF_configstring` answers the
id-view name string with `ERR_DROP`: a CTF server died in the first client's
`ClientUserinfoChanged`, before anyone finished connecting.  The statusbar pair
is only 30 slots out and so lands *inside* the model range - 57 and 58 instead
of 27 and 28, which on `q2ctf1` is where the gib models live, so the
unbalanced-teams warning overwrote `models/objects/gibs/bone/tris.md2` and the
match timer the arm gib.  `warn_unbalanced` defaults to 1, so that half needs
nothing but a public server going 4-v-2.  The reading half moves with the
writing half: both indices are handed to the client in
`STAT_CTF_MATCH`/`STAT_CTF_TEAMINFO`, and `stat_string` indexes
`cl.configstrings` with them and `Com_Error`s a client on a stat past
`cl.csr.end`.

Nothing but a client can see any of this.  The server boots, the map loads and
every static check stays green; the first symptom needs a real connect - which
is where the timer contract above ends up as well.

The first three classes are found by comparing text rather than symbols: diff the
spawn-key strings pristine-vs-port and port-vs-baseq2, where a rename shows up
as one key lost plus one key added, and diff each struct's member list against
its descriptor table.  Two caveats for anyone repeating it.  `client_respawn_t`
is excluded throughout - q2pro persists none of it anywhere, not even baseq2's
own members, so a pack's `resp` fields being absent follows the engine's design
rather than breaking a contract.  And Threewave CTF still has unlisted members;
it never loads a savegame, so the loss there is latent rather than observable.
