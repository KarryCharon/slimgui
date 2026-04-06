set(Python_EXECUTABLE ".venv/Scripts/python.exe")
cmake_minimum_required(VERSION 3.15...3.27)

# Use -Os (size) instead of -O3 (speed) for Release builds — smaller binary
set(CMAKE_CXX_FLAGS_RELEASE "-Os -DNDEBUG" CACHE STRING "" FORCE)

project(slimgui LANGUAGES CXX)

option(SLIMGUI_INCLUDE_DEMO "Include imgui demo window (adds ~475K)" ON)

# Try to import all Python components potentially needed by nanobind
find_package(Python 3.8
  REQUIRED COMPONENTS Interpreter Development.Module
  OPTIONAL_COMPONENTS Development.SABIModule)

# Import nanobind through CMake's find_package mechanism
find_package(nanobind CONFIG REQUIRED)

#add_definitions(-DIMGUI_DISABLE_OBSOLETE_FUNCTIONS=1)
add_definitions(-DIMGUI_DISABLE_OBSOLETE_KEYIO=1)

set(IMGUI_SOURCES
  src/c/imgui/imgui.cpp
  src/c/imgui/imgui_draw.cpp
  src/c/imgui/imgui_tables.cpp
  src/c/imgui/imgui_widgets.cpp
)

if(SLIMGUI_INCLUDE_DEMO)
  list(APPEND IMGUI_SOURCES src/c/imgui/imgui_demo.cpp)
else()
  add_definitions(-DIMGUI_DISABLE_DEMO_WINDOWS=1)
endif()

nanobind_add_module(slimgui_ext
  NB_STATIC
  STABLE_ABI
  NB_DOMAIN slimgui_abi_domain
  LTO

  src/slimgui_ext.cpp
  ${IMGUI_SOURCES}
)

# TODO the below works too, should get rid of the docs mangling in full_build.sh.
# nanobind_add_stub(
#     slimgui_ext_stub
#     MODULE slimgui_ext
#     PYTHON_PATH $<TARGET_FILE_DIR:slimgui_ext>
#     DEPENDS slimgui_ext
#     RECURSIVE
#     OUTPUT_PATH "${CMAKE_SOURCE_DIR}/src/slimgui"
#     OUTPUT 
#         "${CMAKE_SOURCE_DIR}/src/slimgui/slimgui_ext/__init__.pyi"
#         "${CMAKE_SOURCE_DIR}/src/slimgui/slimgui_ext/imgui.pyi"
# )

include_directories(${CMAKE_SOURCE_DIR}/src/c/imgui)

if(APPLE)
  # Used by the default implementation for macOS clipboard access.
  # See https://github.com/ocornut/imgui/pull/2546 for framework linking history.
  find_library(APPLICATIONSERVICES_FRAMEWORK ApplicationServices REQUIRED)
  target_link_libraries(slimgui_ext PRIVATE ${APPLICATIONSERVICES_FRAMEWORK})
endif()

install(TARGETS slimgui_ext LIBRARY DESTINATION slimgui)
install(FILES "${CMAKE_SOURCE_DIR}/src/slimgui/slimgui_ext/__init__.pyi" DESTINATION slimgui/slimgui_ext/)
install(FILES "${CMAKE_SOURCE_DIR}/src/slimgui/slimgui_ext/imgui.pyi" DESTINATION slimgui/slimgui_ext/)
