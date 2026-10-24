cmake_minimum_required(VERSION 3.18)
project(mechy_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(Threads REQUIRED)
# pybind11 comes from the build requirements (pyproject.toml), which ship a
# CMake package config; scikit-build-core puts it on CMAKE_PREFIX_PATH.
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

# Plain C++ library (no Python), usable from C++ tests or other tools.
add_library(mechy_core_lib STATIC src/ball.cpp src/arm.cpp src/motion.cpp)
target_include_directories(mechy_core_lib PUBLIC include)
set_target_properties(mechy_core_lib PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_link_libraries(mechy_core_lib PUBLIC Threads::Threads)
if(MSVC)
  target_compile_options(mechy_core_lib PRIVATE /W4)
else()
  target_compile_options(mechy_core_lib PRIVATE -Wall -Wextra)
endif()

pybind11_add_module(_mechy_core src/bindings.cpp)
target_link_libraries(_mechy_core PRIVATE mechy_core_lib)

install(TARGETS _mechy_core DESTINATION mechy_core)
