cmake_minimum_required(VERSION 3.15)
project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 20)

# stuff for v8
add_definitions(-DV8_ENABLE_SANDBOX)
add_definitions(-DV8_COMPRESS_POINTERS)

set(V8_DIR "/opt/homebrew/opt/v8")
include_directories(${V8_DIR}/include)


# stuff for pybind11
set(pybind11_DIR ${CMAKE_CURRENT_SOURCE_DIR}/.venv/lib/python3.12/site-packages/pybind11/share/cmake/pybind11)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_core MODULE src/main.cpp)

# Link libraries
target_link_libraries(_core
    PRIVATE
        ${V8_DIR}/lib/libv8.dylib
        ${V8_DIR}/lib/libv8_libplatform.dylib
)

install(TARGETS _core LIBRARY DESTINATION _core DESTINATION ${SKBUILD_PROJECT_NAME})

