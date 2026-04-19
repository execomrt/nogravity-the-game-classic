# No Gravity

This repository contains the classic `No Gravity` game source code together with a modern `CMake` build setup.

`No Gravity` is a fast-paced 3D space combat game originally developed by realtech VR. The game combines arcade shooting, mission-based progression, escort and attack objectives, and wingman command mechanics in a first-person spaceflight format.

## Project overview

This codebase includes:

- the core game code in `source/src`
- the `rlx32` engine code in `source/rlx32`
- a `CMake` configuration for modern Visual Studio builds
- optional renderer targets for OpenGL, software rendering, Direct3D, and Glide

The current build setup is aimed at the original Windows release style and places runtime output in `Bin/`.

## Game summary

In `No Gravity`, the player pilots a combat spacecraft through a campaign of mission-driven space battles. Objectives include:

- destroying enemy fighters and installations
- escorting friendly ships
- defending strategic targets
- clearing hazards such as mine fields
- advancing through navigation points and warp gates

The game is known for its futuristic presentation, cockpit-based action, and light squad-command system.

## Requirements

For the current `CMake` build:

- Windows
- `CMake` 3.25 or newer
- Visual Studio 2019 or 2022 with C/C++ tools
- internet access during configure time if dependencies are not already installed

The build downloads or uses these libraries:

- `zlib`
- `libpng`
- `libogg`
- `libvorbis`

## Building

From the repository root:

1. Configure:

   `cmake --preset vs2022-x86`

2. Build:

   `cmake --build --preset vs2022-x86-release`

Build output is written to `Bin/`.

## Renderer options

The main `CMake` options are:

- `USE_OPENGL` - enabled by default
- `USE_SOFT` - optional software renderer
- `USE_D3D` - optional DirectDraw/Direct3D renderer
- `USE_GLIDE` - optional Glide renderer

Example:

`cmake --preset vs2022-x86 -DUSE_OPENGL=ON -DUSE_D3D=OFF -DUSE_SOFT=OFF`

Note: the current MSVC configuration is set up to match the original 32-bit Windows target.

## Running

The executable is produced as `Bin/nogravity.exe`.

To run the game successfully, the required game data must be available alongside the executable or in the expected runtime location. Historical packaging for this project references the main data archive as `NOGRAVITY.RMX`, but that file is not included in this repository.

If you enable renderer DLLs, keep them in `Bin/` next to `nogravity.exe`.

## Repository layout

- `CMakeLists.txt` - main build script
- `CMakePresets.json` - preset definitions for Visual Studio builds
- `source/src` - game-specific code
- `source/rlx32` - engine and platform code
- `Bin` - runtime output directory
- `out/build` - generated build directories

## License

This repository is distributed under the `GNU General Public License v3.0`. See `LICENSE` for details.

## Notes

This README describes the source project and build setup in this repository. For historical background on the original game, see the public information available about `No Gravity` and its original release by realtech VR.
