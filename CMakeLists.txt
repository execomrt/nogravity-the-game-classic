cmake_minimum_required(VERSION 3.20)
project(NoGravity C CXX)

set(ROOT_DIR    ${CMAKE_CURRENT_SOURCE_DIR})
set(RLX32_DIR   ${ROOT_DIR}/source/rlx32)
set(SRC_DIR     ${ROOT_DIR}/source/src)
set(SDK_DIR     ${ROOT_DIR}/SDK)
set(BIN_DIR     ${ROOT_DIR}/Bin)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${BIN_DIR})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${BIN_DIR})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${BIN_DIR})

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------
if(WIN32)
    set(PLATFORM_WINDOWS TRUE)
elseif(APPLE)
    set(PLATFORM_MACOS TRUE)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(PLATFORM_LINUX TRUE)
elseif(CMAKE_SYSTEM_NAME STREQUAL "AmigaOS" OR CMAKE_SYSTEM_NAME STREQUAL "MorphOS" OR CMAKE_SYSTEM_NAME STREQUAL "AROS")
    set(PLATFORM_AMIGA TRUE)
else()
    message(WARNING "Unknown platform '${CMAKE_SYSTEM_NAME}' – treating as Linux-like")
    set(PLATFORM_LINUX TRUE)
endif()

message(STATUS "Building for platform: ${CMAKE_SYSTEM_NAME}")

# ---------------------------------------------------------------------------
# Force 32-bit on MSVC (original projects all targeted MachineX86 / Win32)
# ---------------------------------------------------------------------------
if(MSVC)
    set(CMAKE_GENERATOR_PLATFORM Win32 CACHE STRING "" FORCE)
endif()

# ---------------------------------------------------------------------------
# Common compiler options
# ---------------------------------------------------------------------------
if(MSVC)
    add_compile_options(/W3 /MP)
    add_compile_definitions(_MBCS _CRT_SECURE_NO_WARNINGS NOMINMAX)
else()
    # GCC/Clang: match original warning level roughly, enable position-
    # independent code for shared libs, and pull in the C99/C++11 baseline.
    add_compile_options(-Wall -Wno-unused-result)
    set(CMAKE_C_STANDARD   99)
    set(CMAKE_CXX_STANDARD 11)
endif()

# ---------------------------------------------------------------------------
# Renderer options
# ---------------------------------------------------------------------------
option(USE_OPENGL "Build/link the OpenGL renderer"                                                  ON)
option(USE_SOFT   "Build the software (reference) renderer (Windows DLL only)"                     OFF)
option(USE_D3D    "Build the DirectDraw/Direct3D renderer (Windows only)"                          OFF)
option(USE_GLIDE  "Build the Glide2 renderer (Windows only) – requires SDK/glide2/"               OFF)

# Sound backend (non-Windows only)
set(SOUND_BACKEND "sdl_mixer" CACHE STRING "Sound backend on Linux/macOS/Amiga: sdl_mixer or openal")
set_property(CACHE SOUND_BACKEND PROPERTY STRINGS sdl_mixer openal none)

message(STATUS "Renderer options: USE_OPENGL=${USE_OPENGL}  USE_SOFT=${USE_SOFT}  USE_D3D=${USE_D3D}  USE_GLIDE=${USE_GLIDE}")
message(STATUS "Sound backend   : ${SOUND_BACKEND}  (non-Windows only)")

# Guard: D3D / Glide are Windows-only
if((USE_D3D OR USE_GLIDE) AND NOT PLATFORM_WINDOWS)
    message(WARNING "USE_D3D / USE_GLIDE are Windows-only and will be ignored on this platform.")
    set(USE_D3D   OFF)
    set(USE_GLIDE OFF)
endif()

# ---------------------------------------------------------------------------
# Dependencies via FetchContent  (prefer locally installed versions first)
# ---------------------------------------------------------------------------
include(FetchContent)
set(FETCHCONTENT_QUIET ON)

# ---- zlib ------------------------------------------------------------------
find_package(ZLIB QUIET)
if(NOT ZLIB_FOUND)
    message(STATUS "zlib not found – fetching v1.3.1")
    FetchContent_Declare(
        zlib
        GIT_REPOSITORY https://github.com/madler/zlib.git
        GIT_TAG        v1.3.1
        GIT_SHALLOW    TRUE
        OVERRIDE_FIND_PACKAGE
    )
    FetchContent_MakeAvailable(zlib)
    if(TARGET zlibstatic AND NOT TARGET ZLIB::ZLIB)
        add_library(ZLIB::ZLIB ALIAS zlibstatic)
    elseif(TARGET zlib AND NOT TARGET ZLIB::ZLIB)
        add_library(ZLIB::ZLIB ALIAS zlib)
    endif()
    foreach(_t zlibstatic zlib)
        if(TARGET ${_t})
            target_include_directories(${_t} PUBLIC
                $<BUILD_INTERFACE:${zlib_SOURCE_DIR}>
                $<BUILD_INTERFACE:${zlib_BINARY_DIR}>
            )
        endif()
    endforeach()
endif()


# ---- libpng -----------------------------------------------------------------
find_package(PNG QUIET)
if(NOT PNG_FOUND)
    message(STATUS "libpng not found - fetching v1.6.43")
    set(PNG_SHARED OFF CACHE BOOL "" FORCE)
    set(PNG_STATIC ON  CACHE BOOL "" FORCE)
    set(PNG_TESTS  OFF CACHE BOOL "" FORCE)
    set(PNG_TOOLS  OFF CACHE BOOL "" FORCE)

    set(_save_CMAKE_SKIP_INSTALL_RULES ${CMAKE_SKIP_INSTALL_RULES})
    set(CMAKE_SKIP_INSTALL_RULES ON)

    FetchContent_Declare(
        libpng
        GIT_REPOSITORY https://github.com/pnggroup/libpng.git
        GIT_TAG        v1.6.43
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(libpng)

    set(CMAKE_SKIP_INSTALL_RULES ${_save_CMAKE_SKIP_INSTALL_RULES})

    if(TARGET png_static AND NOT TARGET PNG::PNG)
        add_library(PNG::PNG ALIAS png_static)
    elseif(TARGET png AND NOT TARGET PNG::PNG)
        add_library(PNG::PNG ALIAS png)
    endif()

    # keep these for consumers in this project
    set(NG_LIBPNG_FETCHED TRUE)
    set(NG_LIBPNG_SOURCE_DIR "${libpng_SOURCE_DIR}")
    set(NG_LIBPNG_BINARY_DIR "${libpng_BINARY_DIR}")
endif()

# ---- libogg / libvorbis ----------------------------------------------------
FetchContent_Declare(
    ogg
    GIT_REPOSITORY https://github.com/xiph/ogg.git
    GIT_TAG        v1.3.6
    GIT_SHALLOW    TRUE
)
FetchContent_MakeAvailable(ogg)

FetchContent_Declare(
    vorbis
    GIT_REPOSITORY https://github.com/xiph/vorbis.git
    GIT_TAG        2eac96b03ff67953354cb0a649c08aa3a23267ef
)
FetchContent_MakeAvailable(vorbis)

# ---- SDL (Linux / macOS / Amiga – windowing + input + sound mixer) ---------
if(NOT PLATFORM_WINDOWS)
    find_package(SDL QUIET)        # SDL 1.x (matches the original autoconf)
    if(NOT SDL_FOUND)
        find_package(SDL2 QUIET)   # SDL 2.x fallback
        if(SDL2_FOUND)
            message(STATUS "Found SDL2 – using as SDL replacement")
            # Provide a uniform target name used below
            if(NOT TARGET SDL::SDL)
                add_library(SDL::SDL ALIAS SDL2::SDL2)
            endif()
            set(SDL_FOUND TRUE)
            set(SDL_INCLUDE_DIRS ${SDL2_INCLUDE_DIRS})
            set(SDL_LIBRARIES    ${SDL2_LIBRARIES})
        else()
            message(FATAL_ERROR "SDL (1.x or 2.x) is required on ${CMAKE_SYSTEM_NAME}. "
                                "Install libsdl-dev / libsdl2-dev or set SDL_DIR.")
        endif()
    else()
        if(NOT TARGET SDL::SDL)
            add_library(SDL::SDL INTERFACE IMPORTED)
            set_target_properties(SDL::SDL PROPERTIES
                INTERFACE_INCLUDE_DIRECTORIES "${SDL_INCLUDE_DIRS}"
                INTERFACE_LINK_LIBRARIES      "${SDL_LIBRARIES}")
        endif()
    endif()

    # ---- Sound backend -----------------------------------------------------
    if(SOUND_BACKEND STREQUAL "sdl_mixer")
        find_package(SDL_mixer QUIET)
        if(NOT SDL_mixer_FOUND)
            # Many distros ship it without a proper CMake config; try pkg-config
            find_package(PkgConfig QUIET)
            if(PkgConfig_FOUND)
                pkg_check_modules(SDL_MIXER QUIET SDL_mixer SDL2_mixer)
            endif()
        endif()
        if(NOT SDL_mixer_FOUND AND NOT SDL_MIXER_FOUND)
            message(WARNING "SDL_mixer not found – sound will be disabled. "
                            "Install libsdl-mixer-dev or pass -DSOUND_BACKEND=openal/none.")
            set(SOUND_BACKEND "none")
        endif()
    elseif(SOUND_BACKEND STREQUAL "openal")
        find_package(OpenAL REQUIRED)
    endif()
endif()

# ---- OpenGL (all non-Windows platforms when USE_OPENGL is ON) --------------
if(USE_OPENGL AND NOT PLATFORM_WINDOWS)
    if(PLATFORM_MACOS)
        find_package(OpenGL REQUIRED)
        # On macOS the headers live in <OpenGL/gl.h>, not <GL/gl.h>.
        # Add a compile definition so source files can branch on it.
        add_compile_definitions(MACOS_OPENGL)
    else()
        find_package(OpenGL REQUIRED)
    endif()
endif()

# ===========================================================================
# Helper: platform-specific source lists and definitions
# ===========================================================================

# --- Platform sources for the main executable ---
if(PLATFORM_WINDOWS)
    set(PLATFORM_SOURCES
        ${RLX32_DIR}/src/win32/dxerr.c
        ${RLX32_DIR}/src/win32/snd_ds6.cpp
        ${RLX32_DIR}/src/win32/snd_eax.cpp
        ${RLX32_DIR}/src/win32/sysdbg.c
        ${RLX32_DIR}/src/win32/sysjoy.cpp
        ${RLX32_DIR}/src/win32/syskeyb.cpp
        ${RLX32_DIR}/src/win32/sysmouse.cpp
        ${RLX32_DIR}/src/win32/sysnetw.cpp
        ${RLX32_DIR}/src/win32/sysreg.c
        ${RLX32_DIR}/src/win32/sysregw.c
        ${RLX32_DIR}/src/win32/systime.c
        ${RLX32_DIR}/src/win32/systools.c
        ${RLX32_DIR}/src/win32/_stubw32.cpp
        ${RLX32_DIR}/src/_stub.cpp
        ${SRC_DIR}/Win32/preferences.c
        ${SRC_DIR}/Win32/resource.rc
    )
    set(PLATFORM_DEFINITIONS
        WIN32 _WINDOWS _CRT_SECURE_NO_WARNINGS
        DIRECTINPUT_VERSION=0x0800
        DIRECTDRAW_VERSION=0x0800
        DIRECTSOUND_VERSION=0x0800
        DX8
    )
    set(PLATFORM_INCLUDE_DIRS "")
    set(PLATFORM_LINK_LIBS dinput8 dxguid dsound comctl32 winmm)
    set(EXECUTABLE_TYPE WIN32)

elseif(PLATFORM_MACOS)
    set(PLATFORM_SOURCES
        ${RLX32_DIR}/src/linux/systool2.c   # shared with Linux port
        ${RLX32_DIR}/src/linux/systime.c
        ${RLX32_DIR}/src/linux/sysdbg.c
        ${RLX32_DIR}/src/linux/_stublinux.cpp
        ${RLX32_DIR}/src/linux/sysnet.c
        ${RLX32_DIR}/src/linux/sysreg.c
        ${RLX32_DIR}/src/linux/sysjoy.c
        ${RLX32_DIR}/src/linux/syskeyb.c
        ${RLX32_DIR}/src/linux/sysmouse.c
        ${RLX32_DIR}/src/_stub.cpp
        ${SRC_DIR}/Linux/preferences.c
    )
    set(PLATFORM_DEFINITIONS __LINUX__ MACOS)   # source uses __LINUX__ guards
    set(PLATFORM_INCLUDE_DIRS
        ${RLX32_DIR}/src/linux
    )
    set(PLATFORM_LINK_LIBS SDL::SDL "-framework OpenGL" "-framework Cocoa")
    set(EXECUTABLE_TYPE "")

elseif(PLATFORM_LINUX)
    set(PLATFORM_SOURCES
        ${RLX32_DIR}/src/linux/systool2.c
        ${RLX32_DIR}/src/linux/systime.c
        ${RLX32_DIR}/src/linux/snd.c
        ${RLX32_DIR}/src/linux/sysdbg.c
        ${RLX32_DIR}/src/linux/_stublinux.cpp
        ${RLX32_DIR}/src/linux/sysnet.c
        ${RLX32_DIR}/src/linux/sysreg.c
        ${RLX32_DIR}/src/linux/sysjoy.c
        ${RLX32_DIR}/src/linux/syskeyb.c
        ${RLX32_DIR}/src/linux/sysmouse.c
        ${RLX32_DIR}/src/_stub.cpp
        ${SRC_DIR}/Linux/preferences.c
    )
    set(PLATFORM_DEFINITIONS __LINUX__)
    set(PLATFORM_INCLUDE_DIRS
        ${RLX32_DIR}/src/linux
    )
    set(PLATFORM_LINK_LIBS SDL::SDL)
    set(EXECUTABLE_TYPE "")

elseif(PLATFORM_AMIGA)
    set(PLATFORM_SOURCES
        ${RLX32_DIR}/src/linux/systool2.c   # Amiga port reuses linux stubs
        ${RLX32_DIR}/src/linux/systime.c
        ${RLX32_DIR}/src/linux/snd.c
        ${RLX32_DIR}/src/linux/sysdbg.c
        ${RLX32_DIR}/src/linux/_stublinux.cpp
        ${RLX32_DIR}/src/linux/sysnet.c
        ${RLX32_DIR}/src/linux/sysreg.c
        ${RLX32_DIR}/src/linux/sysjoy.c
        ${RLX32_DIR}/src/linux/syskeyb.c
        ${RLX32_DIR}/src/linux/sysmouse.c
        ${RLX32_DIR}/src/_stub.cpp
        ${SRC_DIR}/amiga/preferences.c
    )
    set(PLATFORM_DEFINITIONS __LINUX__ __AMIGA__)
    set(PLATFORM_INCLUDE_DIRS
        ${RLX32_DIR}/src/linux
    )
    set(PLATFORM_LINK_LIBS SDL::SDL)
    set(EXECUTABLE_TYPE "")
endif()

# --- Renderer sources (non-Windows inline build) ---
if(NOT PLATFORM_WINDOWS)
    if(USE_OPENGL)
        set(RENDERER_SOURCES
            ${RLX32_DIR}/src/renderers/opengl/gl_gx.cpp
            ${RLX32_DIR}/src/renderers/opengl/gl_v3x.cpp
            ${RLX32_DIR}/src/renderers/opengl/linux/sdl_gl.cpp
        )
        set(RENDERER_INCLUDE_DIRS
            ${RLX32_DIR}/src/renderers/opengl
            ${RLX32_DIR}/src/renderers/opengl/linux
        )
        set(RENDERER_DEFINITIONS USE_OPENGL)
    else()
        # Software (reference) renderer – same files as the Windows ng_soft DLL
        set(RENDERER_SOURCES
            ${RLX32_DIR}/src/renderers/v3x_ref/z16_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r16_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r08_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/z08_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r16_128.c
            ${RLX32_DIR}/src/renderers/v3x_ref/z32_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r08_128.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r32_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/v3xref.c
            ${RLX32_DIR}/src/renderers/gfx_ref/sp8bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/sp16bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/gr32bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/gx_drv.c
            ${RLX32_DIR}/src/renderers/gfx_ref/gr16bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/gr8bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/sp32bit.c
            ${RLX32_DIR}/src/linux/gx_sdl.cpp
        )
        set(RENDERER_INCLUDE_DIRS "")
        set(RENDERER_DEFINITIONS "")
    endif()
endif()

# --- Sound backend link libraries (non-Windows) ---
if(NOT PLATFORM_WINDOWS)
    if(SOUND_BACKEND STREQUAL "sdl_mixer")
        if(TARGET SDL_mixer::SDL_mixer)
            list(APPEND PLATFORM_LINK_LIBS SDL_mixer::SDL_mixer)
        elseif(SDL_MIXER_FOUND)
            list(APPEND PLATFORM_LINK_LIBS ${SDL_MIXER_LIBRARIES})
        endif()
        list(APPEND PLATFORM_DEFINITIONS SOUND_SDL_MIXER)
    elseif(SOUND_BACKEND STREQUAL "openal")
        list(APPEND PLATFORM_LINK_LIBS OpenAL::OpenAL)
        list(APPEND PLATFORM_DEFINITIONS SOUND_OPENAL)
    endif()
endif()

# ===========================================================================
# ng_game  –  static library
# ===========================================================================
add_library(ng_game STATIC
    ${SRC_DIR}/ccmx.c
    ${SRC_DIR}/console.c
    ${SRC_DIR}/lithium.c
    ${SRC_DIR}/lt_data.c
    ${SRC_DIR}/lt_fx.c
    ${SRC_DIR}/lt_game.c
    ${SRC_DIR}/lt_game2.c
    ${SRC_DIR}/lt_info.c
    ${SRC_DIR}/lt_input.c
    ${SRC_DIR}/lt_menu.c
    ${SRC_DIR}/lt_reso.c
    ${SRC_DIR}/lt_save.c
    ${SRC_DIR}/lt_sound.c
    ${SRC_DIR}/lt_st2.c
    ${SRC_DIR}/lt_start.c
    ${SRC_DIR}/lt_video.c
    ${SRC_DIR}/lt_weap.c
)
target_include_directories(ng_game PUBLIC
    ${RLX32_DIR}/include
    ${SRC_DIR}
)
target_compile_definitions(ng_game PUBLIC
    _LIB
    _CRT_SECURE_NO_WARNING
    $<$<CONFIG:Debug>:_DEBUG>
    $<$<CONFIG:Release>:NDEBUG>
    $<$<BOOL:${PLATFORM_WINDOWS}>:WIN32>
)

# ===========================================================================
# v3x  –  static library
# ===========================================================================
add_library(v3x STATIC
    ${RLX32_DIR}/src/gui_os.c
    ${RLX32_DIR}/src/gx_csp.c
    ${RLX32_DIR}/src/gx_flc.c
    ${RLX32_DIR}/src/gx_form.c
    ${RLX32_DIR}/src/gx_init.c
    ${RLX32_DIR}/src/gx_png.c
    ${RLX32_DIR}/src/gx_rgb.c
    ${RLX32_DIR}/src/gx_tool.c
    ${RLX32_DIR}/src/iss_av.c
    ${RLX32_DIR}/src/iss_cdc.c
    ${RLX32_DIR}/src/iss_db.c
    ${RLX32_DIR}/src/iss_form.c
    ${RLX32_DIR}/src/iss_ogg.c
    ${RLX32_DIR}/src/sysgi.c
    ${RLX32_DIR}/src/sysini.c
    ${RLX32_DIR}/src/syslist.c
    ${RLX32_DIR}/src/sysresmx.c
    ${RLX32_DIR}/src/systools.c
    ${RLX32_DIR}/src/syszlib.c
    ${RLX32_DIR}/src/v3xcoll.c
    ${RLX32_DIR}/src/v3xdata.c
    ${RLX32_DIR}/src/v3xmaps.c
    ${RLX32_DIR}/src/v3xrend.c
    ${RLX32_DIR}/src/v3xscen2.c
    ${RLX32_DIR}/src/v3xscene.c
    ${RLX32_DIR}/src/v3xsoft.c
    ${RLX32_DIR}/src/v3x_1.c
    ${RLX32_DIR}/src/v3x_2.c
    ${RLX32_DIR}/src/v3x_3.c
)
# Linux port also needs gx_alloc.c (present in autoconf source list, absent on Windows)
if(NOT PLATFORM_WINDOWS)
    target_sources(v3x PRIVATE ${RLX32_DIR}/src/gx_alloc.c)
endif()


if(NG_LIBPNG_FETCHED)
    target_include_directories(v3x PRIVATE
        "${NG_LIBPNG_SOURCE_DIR}"
        "${NG_LIBPNG_BINARY_DIR}"
    )
endif()

target_include_directories(v3x PUBLIC
    ${RLX32_DIR}/include
    ${SRC_DIR}
)
target_compile_definitions(v3x PUBLIC
    _LIB
    _CRT_SECURE_NO_WARNING
    $<$<CONFIG:Debug>:_DEBUG>
    $<$<CONFIG:Release>:NDEBUG>
    $<$<BOOL:${PLATFORM_WINDOWS}>:WIN32>
)
target_link_libraries(v3x PUBLIC
    ZLIB::ZLIB
    PNG::PNG
    Ogg::ogg
    Vorbis::vorbis
    Vorbis::vorbisfile
)

# ===========================================================================
# Windows-only renderer DLLs
# ===========================================================================
if(PLATFORM_WINDOWS)

    # ---- ng_d3d ------------------------------------------------------------
    if(USE_D3D)
        add_library(ng_d3d STATIC
            ${RLX32_DIR}/src/renderers/dx6/d3ddrv.cpp
            ${RLX32_DIR}/src/win32/dxerr.c
            ${RLX32_DIR}/src/win32/gx_dx6.cpp
        )
     
        target_include_directories(ng_d3d PRIVATE ${RLX32_DIR}/include ${SRC_DIR})
        target_compile_definitions(ng_d3d PRIVATE
            WIN32 _WINDOWS _CRT_SECURE_NO_WARNINGS
            DIRECTINPUT_VERSION=0x0500
            DIRECTDRAW_VERSION=0x0600
            DIRECTSOUND_VERSION=0x0600
            $<$<CONFIG:Debug>:_DEBUG> $<$<CONFIG:Release>:NDEBUG>
        )
        target_link_libraries(ng_d3d PRIVATE ddraw dxguid)
        list(APPEND PLATFORM_LINK_LIBS ng_d3d)
    endif()

    # ---- ng_opengl (Windows DLL) -------------------------------------------
    if(USE_OPENGL)
        add_library(ng_opengl STATIC
            ${RLX32_DIR}/src/renderers/opengl/gl_gx.cpp
            ${RLX32_DIR}/src/renderers/opengl/gl_v3x.cpp
            ${RLX32_DIR}/src/renderers/opengl/win32/w32_gl.cpp
            ${RLX32_DIR}/src/renderers/opengl/win32/wglext.cpp
        )
     
        target_include_directories(ng_opengl PRIVATE ${RLX32_DIR}/include ${SRC_DIR})
        target_compile_definitions(ng_opengl PRIVATE
            WIN32 _WINDOWS _CRT_SECURE_NO_WARNINGS
            $<$<CONFIG:Debug>:_DEBUG> $<$<CONFIG:Release>:NDEBUG>
        )
        target_link_libraries(ng_opengl PRIVATE opengl32)
        list(APPEND PLATFORM_LINK_LIBS ng_opengl)
    endif()

    # ---- ng_soft -----------------------------------------------------------
    if(USE_SOFT)
        add_library(ng_soft STATIC
            ${RLX32_DIR}/src/renderers/gfx_ref/gr16bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/gr32bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/gr8bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/gx_drv.c
            ${RLX32_DIR}/src/renderers/gfx_ref/sp16bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/sp32bit.c
            ${RLX32_DIR}/src/renderers/gfx_ref/sp8bit.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r08_128.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r08_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r16_128.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r16_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/r32_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/v3xref.c
            ${RLX32_DIR}/src/renderers/v3x_ref/z08_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/z16_256.c
            ${RLX32_DIR}/src/renderers/v3x_ref/z32_256.c
            ${RLX32_DIR}/src/win32/dxerr.c
            ${RLX32_DIR}/src/win32/gx_dx6.cpp
        )
       
        target_include_directories(ng_soft PRIVATE ${RLX32_DIR}/include)
        target_compile_definitions(ng_soft PRIVATE
            WIN32 _WINDOWS _CRT_SECURE_NO_WARNINGS
            $<$<CONFIG:Debug>:_DEBUG> $<$<CONFIG:Release>:NDEBUG>
        )
        target_link_libraries(ng_soft PRIVATE ddraw dxguid)
        list(APPEND PLATFORM_LINK_LIBS ng_soft)
    endif()

    # ---- ng_glide ----------------------------------------------------------
    if(USE_GLIDE)
        add_library(ng_glide STATIC
            ${RLX32_DIR}/renderers/glide/glide.cpp
        )
      
        target_include_directories(ng_glide PRIVATE
            ${RLX32_DIR}/include ${SRC_DIR} ${SDK_DIR}/glide2)
        target_compile_definitions(ng_glide PRIVATE
            WIN32 _WINDOWS _CRT_SECURE_NO_WARNINGS
            $<$<CONFIG:Debug>:_DEBUG> $<$<CONFIG:Release>:NDEBUG>
        )
        target_link_directories(ng_glide PRIVATE ${SDK_DIR}/glide2)
        target_link_libraries(ng_glide PRIVATE glide2x)
    endif()

endif() # PLATFORM_WINDOWS

# ===========================================================================
# nogravity  –  main executable
# ===========================================================================
add_executable(nogravity ${EXECUTABLE_TYPE}
    ${PLATFORM_SOURCES}
)

# Non-Windows: renderer sources are compiled directly into the executable
if(NOT PLATFORM_WINDOWS)
    target_sources(nogravity PRIVATE ${RENDERER_SOURCES})
endif()

target_include_directories(nogravity PRIVATE
    ${RLX32_DIR}/include
    ${SRC_DIR}
    ${PLATFORM_INCLUDE_DIRS}
    ${RENDERER_INCLUDE_DIRS}
)

target_compile_definitions(nogravity PRIVATE
    ${PLATFORM_DEFINITIONS}
    ${RENDERER_DEFINITIONS}
    _CRT_SECURE_NO_WARNINGS
    $<$<CONFIG:Debug>:_DEBUG>
    $<$<CONFIG:Release>:NDEBUG>
)

# On Linux/macOS link OpenGL through the imported target
if(NOT PLATFORM_WINDOWS AND USE_OPENGL)
    list(APPEND PLATFORM_LINK_LIBS OpenGL::GL)
endif()

target_link_libraries(nogravity PRIVATE
    ng_game
    v3x
    ZLIB::ZLIB
    PNG::PNG
    Ogg::ogg
    Vorbis::vorbis
    Vorbis::vorbisfile
    ${PLATFORM_LINK_LIBS}
)

# MSVC: systools.c exists in both rlx32/src/ and rlx32/src/win32/;
# give the win32 copy a distinct object file name to avoid linker collision.
if(PLATFORM_WINDOWS)
    set_source_files_properties(
        ${RLX32_DIR}/src/win32/systools.c
        PROPERTIES COMPILE_FLAGS "/Fo$(IntDir)systools_w32.obj"
    )
endif()

set_target_properties(nogravity PROPERTIES OUTPUT_NAME "nogravity")

# ===========================================================================
# Make the exe depend on whichever Windows renderer DLLs are enabled
# ===========================================================================
if(PLATFORM_WINDOWS)
    set(_renderer_deps "")
    if(USE_D3D)    
        list(APPEND _renderer_deps ng_d3d)    
    endif()
    if(USE_OPENGL)
        list(APPEND _renderer_deps ng_opengl)
    endif()
    if(USE_SOFT) 
        list(APPEND _renderer_deps ng_soft)  
    endif()
    if(USE_GLIDE)
        list(APPEND _renderer_deps ng_glide)  
    endif()
    if(_renderer_deps)
        add_dependencies(nogravity ${_renderer_deps})
    endif()
endif()