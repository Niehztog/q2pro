# Threewave Capture The Flag game library.
# Ported from the last official ctf source release, with q2pro's
# baseq2 history replayed on top.  See doc/mission-packs.md.

ctf_src = files(
  'g_ai.c',
  'g_chase.c',
  'g_cmds.c',
  'g_combat.c',
  'g_ctf.c',
  'g_func.c',
  'g_items.c',
  'g_main.c',
  'g_misc.c',
  'g_monster.c',
  'g_phys.c',
  'g_ptrs.c',
  'g_save.c',
  'g_spawn.c',
  'g_svcmds.c',
  'g_target.c',
  'g_trigger.c',
  'g_utils.c',
  'g_weapon.c',
  'm_move.c',
  'p_client.c',
  'p_hud.c',
  'p_menu.c',
  'p_trail.c',
  'p_view.c',
  'p_weapon.c',
)

shared_library('game' + cpu, ctf_src + game_shared_src,
  name_prefix:           '',
  dependencies:          game_deps,
  include_directories:   engine_inc,
  gnu_symbol_visibility: 'hidden',
  link_args:             dll_link_args,
  install:               system_wide,
  install_dir:           libdir / 'ctf',
  override_options:      get_option('game-build-options'),
)
