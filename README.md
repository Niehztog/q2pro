Mission packs branch
====================

This branch (`feature/mission-packs`) adds three more game libraries alongside
`baseq2`: **Threewave Capture The Flag**, **The Reckoning** (Xatrix) and
**Ground Zero** (Rogue).

They are not fresh ports. Each was imported from its last official source
release and then had *every* commit Q2PRO has ever made to the `baseq2` game
source replayed on top of it, so all three carry the same modernised game API,
savegame system, frame-number timers and accumulated bug fixes as `baseq2` —
and build clean with `-Werror` next to it.

* [doc/mission-packs.md](doc/mission-packs.md) — what was imported from where,
  how the replay was performed, and the deviations worth knowing about.

Build them with the `mission-packs` meson option (all three are on by default):

    meson setup builddir -Dmission-packs=ctf,xatrix,rogue

---

Q2PRO
=====

Q2PRO is an enhanced Quake 2 client and server for Windows and Linux. Supported
features include:

* unified OpenGL renderer with support for wide range of OpenGL versions
* enhanced console command completion
* persistent and searchable console command history
* rendering / physics / packet rate separation
* ZIP packfiles (.pkz)
* JPEG/PNG textures
* MD3 and MD5 (re-release) models
* Ogg Vorbis music and Ogg Theora cinematics
* fast and secure HTTP downloads
* multichannel sound using OpenAL
* stereo WAV files support
* forward and backward seeking in demos
* recording from demos
* server side multiview demos
* live game broadcasting capabilities
* network protocol extensions for larger maps
* won't crash if game data is corrupted

For building Q2PRO, consult the INSTALL.md file.

Q2PRO doesn't have releases. It is always recommended to use the git master
version.

For information on using and configuring Q2PRO, refer to client and server
manuals available in doc/ subdirectory.
