# protocol/CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(ukk_protocol VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compiler flags for low-latency
add_compile_options(-O3 -march=native -Wall -Wextra -Wpedantic)

find_package(msgpack-cxx REQUIRED)

add_library(ukk_protocol INTERFACE)
target_include_directories(ukk_protocol INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_link_libraries(ukk_protocol INTERFACE msgpack-cxx)

# Tests
enable_testing()
add_subdirectory(tests)
