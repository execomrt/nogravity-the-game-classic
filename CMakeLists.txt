cmake_minimum_required(VERSION 3.20)
project(NoGravity C CXX)
set(ROOT_DIR    ${CMAKE_CURRENT_SOURCE_DIR})
set(RLX32_DIR   ${ROOT_DIR}/source/rlx32)
set(SRC_DIR     ${ROOT_DIR}/source/src)
set(SDK_DIR     ${ROOT_DIR}/SDK)
set(BIN_DIR     ${ROOT_DIR}/Bin)
# Put all runtime outputs (exe / dll) in Bin/ to match the original projects
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${BIN_DIR})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${BIN_DIR})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${BIN_DIR})
# Force 32-bit (the original projects all targeted MachineX86 / Win32)
if(MSVC)
    set(CMAKE_GENERATOR_PLATFORM Win32 CACHE STRING "" FORCE)
endif()
# ---------------------------------------------------------------------------
# Common compiler options (mirrors the vcxproj warning level / char-set)
# ---------------------------------------------------------------------------
if(MSVC)
    add_compile_options(/W3 /MP)
    add_compile_definitions(_MBCS)
endif()
# ---------------------------------------------------------------------------
# Renderer options
# ---------------------------------------------------------------------------
option(USE_OPENGL "Build the OpenGL renderer (ng_opengl.dll)"                                      ON)
option(USE_SOFT   "Build the software (reference) renderer (ng_soft.dll)"                          OFF)
option(USE_D3D    "Build the DirectDraw/Direct3D renderer (ng_d3d.dll)"                            OFF)
option(USE_GLIDE  "Build the Glide2 renderer – requires Glide2 SDK in SDK/glide2/ (ng_glide.dll)" OFF)
message(STATUS "Renderer options:")
message(STATUS "  USE_OPENGL = ${USE_OPENGL}")
message(STATUS "  USE_SOFT   = ${USE_SOFT}")
message(STATUS "  USE_D3D    = ${USE_D3D}")
message(STATUS "  USE_GLIDE  = ${USE_GLIDE}")
# ---------------------------------------------------------------------------
# Dependencies via FetchContent
#   Each dependency first tries find_package so a locally installed version
#   is preferred; FetchContent is the fallback.
# ---------------------------------------------------------------------------
include(FetchContent)
# Silence FetchContent's verbose "-- Populating ..." lines in normal builds
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
    # Some projects expect the canonical imported target name.
    if(TARGET zlibstatic AND NOT TARGET ZLIB::ZLIB)
        add_library(ZLIB::ZLIB ALIAS zlibstatic)
    elseif(TARGET zlib AND NOT TARGET ZLIB::ZLIB)
        add_library(ZLIB::ZLIB ALIAS zlib)
    endif()
    # Ensure both zlib.h and generated zconf.h are visible.
    if(TARGET zlibstatic)
        target_include_directories(zlibstatic PUBLIC
            $<BUILD_INTERFACE:${zlib_SOURCE_DIR}>
            $<BUILD_INTERFACE:${zlib_BINARY_DIR}>
        )
    endif()
    if(TARGET zlib)
        target_include_directories(zlib PUBLIC
            $<BUILD_INTERFACE:${zlib_SOURCE_DIR}>
            $<BUILD_INTERFACE:${zlib_BINARY_DIR}>
        )
    endif()
endif()
# ---- libpng ----------------------------------------------------------------
find_package(PNG QUIET)
if(NOT PNG_FOUND)
    message(STATUS "libpng not found – fetching v1.6.43")
    set(PNG_SHARED OFF CACHE BOOL "" FORCE)
    set(PNG_STATIC ON  CACHE BOOL "" FORCE)
    set(PNG_TESTS  OFF CACHE BOOL "" FORCE)
    set(PNG_TOOLS  OFF CACHE BOOL "" FORCE)

    # Prevent libpng's install(EXPORT ...) machinery from firing when used
    # only as an in-tree fetched dependency.
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
endif()

# --- libogg and libvorbis ------------------------------------------------------
FetchContent_Declare(
    ogg
    GIT_REPOSITORY https://github.com/xiph/ogg.git
    GIT_TAG v1.3.6
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(ogg)
FetchContent_Declare(
    vorbis
    GIT_REPOSITORY https://github.com/xiph/vorbis.git
    GIT_TAG 2eac96b03ff67953354cb0a649c08aa3a23267ef
)
FetchContent_MakeAvailable(vorbis)
# ---------------------------------------------------------------------------
# ng_game  –  static library  (ng_game.vcxproj)
# ---------------------------------------------------------------------------
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
    WIN32
    _LIB
    _CRT_SECURE_NO_WARNING
    $<$<CONFIG:Debug>:_DEBUG>
    $<$<CONFIG:Release>:NDEBUG>
)
# ---------------------------------------------------------------------------
# ng_d3d  –  DLL  (ng_d3d.vcxproj)
# ---------------------------------------------------------------------------
if(USE_D3D)
    add_library(ng_d3d SHARED
        ${RLX32_DIR}/src/renderers/dx6/d3ddrv.cpp
        ${RLX32_DIR}/src/win32/dxerr.c
        ${RLX32_DIR}/src/win32/gx_dx6.cpp
    )
    if(EXISTS ${SRC_DIR}/Win32/renderer.def)
        set_target_properties(ng_d3d PROPERTIES LINK_FLAGS
            "/DEF:\"${SRC_DIR}/Win32/renderer.def\"")
    endif()
    target_include_directories(ng_d3d PRIVATE
        ${RLX32_DIR}/include
        ${SRC_DIR}
    )
    target_compile_definitions(ng_d3d PRIVATE
        WIN32
        _WINDOWS
        _CRT_SECURE_NO_WARNINGS
        _CRT_SECURE_NO_WARNINGS
        DIRECTINPUT_VERSION=0x0500
        DIRECTDRAW_VERSION=0x0600
        DIRECTSOUND_VERSION=0x0600
        $<$<CONFIG:Debug>:_DEBUG>
        $<$<CONFIG:Release>:NDEBUG>
    )
    target_link_libraries(ng_d3d PRIVATE ddraw dxguid)
endif() # USE_D3D
# ---------------------------------------------------------------------------
# ng_opengl  –  DLL  (ng_opengl.vcxproj)
# ---------------------------------------------------------------------------
if(USE_OPENGL)
    add_library(ng_opengl SHARED
        ${RLX32_DIR}/src/renderers/opengl/gl_gx.cpp
        ${RLX32_DIR}/src/renderers/opengl/gl_v3x.cpp
        ${RLX32_DIR}/src/renderers/opengl/win32/w32_gl.cpp
        ${RLX32_DIR}/src/renderers/opengl/win32/wglext.cpp
    )
    if(EXISTS ${SRC_DIR}/Win32/renderer.def)
        set_target_properties(ng_opengl PROPERTIES LINK_FLAGS
            "/DEF:\"${SRC_DIR}/Win32/renderer.def\"")
    endif()
    target_include_directories(ng_opengl PRIVATE
        ${RLX32_DIR}/include
        ${SRC_DIR}
    )
    target_compile_definitions(ng_opengl PRIVATE
        WIN32
        _WINDOWS
        _CRT_SECURE_NO_WARNINGS
        $<$<CONFIG:Debug>:_DEBUG>
        $<$<CONFIG:Release>:NDEBUG>
    )
    target_link_libraries(ng_opengl PRIVATE opengl32)
endif() # USE_OPENGL
# ---------------------------------------------------------------------------
# ng_soft  –  DLL  (ng_soft.vcxproj)
# ---------------------------------------------------------------------------
if(USE_SOFT)
    add_library(ng_soft SHARED
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
    if(EXISTS ${SRC_DIR}/Win32/renderer.def)
        set_target_properties(ng_soft PROPERTIES LINK_FLAGS
            "/DEF:\"${SRC_DIR}/Win32/renderer.def\"")
    endif()
    target_include_directories(ng_soft PRIVATE
        ${RLX32_DIR}/include
    )
    target_compile_definitions(ng_soft PRIVATE
        WIN32
        _WINDOWS
        _CRT_SECURE_NO_WARNINGS
        $<$<CONFIG:Debug>:_DEBUG>
        $<$<CONFIG:Release>:NDEBUG>
    )
    target_link_libraries(ng_soft PRIVATE ddraw dxguid)
endif() # USE_SOFT
# ---------------------------------------------------------------------------
# ng_glide  –  DLL  (ng_glide.vcxproj)
# ---------------------------------------------------------------------------
if(USE_GLIDE)
    add_library(ng_glide SHARED
        ${RLX32_DIR}/renderers/glide/glide.cpp
    )
    if(EXISTS ${SRC_DIR}/Win32/renderer.def)
        set_target_properties(ng_glide PROPERTIES LINK_FLAGS
            "/DEF:\"${SRC_DIR}/Win32/renderer.def\"")
    endif()
    target_include_directories(ng_glide PRIVATE
        ${RLX32_DIR}/include
        ${SRC_DIR}
        ${SDK_DIR}/glide2
    )
    target_compile_definitions(ng_glide PRIVATE
        WIN32
        _WINDOWS
        _CRT_SECURE_NO_WARNINGS
         _CRT_SECURE_NO_WARNINGS
        $<$<CONFIG:Debug>:_DEBUG>
        $<$<CONFIG:Release>:NDEBUG>
    )
    target_link_directories(ng_glide PRIVATE ${SDK_DIR}/glide2)
    target_link_libraries(ng_glide PRIVATE glide2x)
endif() # USE_GLIDE


# ---------------------------------------------------------------------------
# v3x  –  static library  (ng_game.vcxproj)
# ---------------------------------------------------------------------------
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
target_include_directories(v3x PUBLIC
    ${RLX32_DIR}/include
    ${SRC_DIR}
)
target_compile_definitions(v3x PUBLIC
    WIN32
    _LIB
    _CRT_SECURE_NO_WARNING
    $<$<CONFIG:Debug>:_DEBUG>
    $<$<CONFIG:Release>:NDEBUG>

)
target_link_libraries(v3x PUBLIC
    ZLIB::ZLIB
    PNG::PNG
    Ogg::ogg 
)
# ---------------------------------------------------------------------------
# nogravity  –  Win32 executable  (ng_w32.vcxproj)
# ---------------------------------------------------------------------------
add_executable(nogravity WIN32
  
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
target_include_directories(nogravity PRIVATE
    ${RLX32_DIR}/include
    ${SRC_DIR}
    # Uncomment if using a standalone DirectX SDK:
    # $ENV{DXSDK_DIR}/Include
)
target_compile_definitions(nogravity PRIVATE
    WIN32
    _WINDOWS
    _CRT_SECURE_NO_WARNINGS
    _CRT_SECURE_NO_WARNINGS
    DIRECTINPUT_VERSION=0x0800
    DIRECTDRAW_VERSION=0x0600
    DIRECTSOUND_VERSION=0x0800
    $<$<CONFIG:Debug>:_DEBUG>
    $<$<CONFIG:Release>:NDEBUG>
)
# win32/systools.c and rlx32/src/systools.c share the same base filename;
# give the win32 copy a distinct object name to avoid a linker collision.
set_source_files_properties(
    ${RLX32_DIR}/src/win32/systools.c
    PROPERTIES COMPILE_FLAGS "/Fo$(IntDir)systools_w32.obj"   # MSVC only
)
target_link_libraries(nogravity PRIVATE
    ng_game
    v3x
    ZLIB::ZLIB
    PNG::PNG
    Ogg::ogg
    Vorbis::vorbis
    Vorbis::vorbisfile
    dinput8
    dxguid
    dsound
    comctl32
    winmm
)
set_target_properties(nogravity PROPERTIES OUTPUT_NAME "nogravity")
# ---------------------------------------------------------------------------
# Make the exe depend on whichever renderer DLLs are enabled so they are
# always built and land in Bin/ alongside nogravity.exe.
# ---------------------------------------------------------------------------
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