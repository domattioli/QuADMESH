cmake_minimum_required(VERSION 3.16)
project(quadmesh_cpp VERSION 0.1.0 LANGUAGES CXX)

# Release is the default build type. The build never fetches anything:
# Eigen and Catch2 are vendored under third_party/.
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Floating-point rules (SOS R2): no fast-math, no FMA contraction.
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  set(QUADMESH_FP_FLAGS -ffp-contract=off -fno-fast-math)
elseif(MSVC)
  set(QUADMESH_FP_FLAGS /fp:precise)
endif()

set(QUADMESH_EIGEN_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/eigen)
set(QUADMESH_CATCH2_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party/catch2)

# Library: every .cpp under src/ except the CLI entry point.
file(GLOB_RECURSE QUADMESH_LIB_SOURCES CONFIGURE_DEPENDS
  ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)
list(FILTER QUADMESH_LIB_SOURCES EXCLUDE REGEX ".*/src/cli/main\\.cpp$")
file(GLOB_RECURSE QUADMESH_HEADERS CONFIGURE_DEPENDS
  ${CMAKE_CURRENT_SOURCE_DIR}/include/quadmesh/*.hpp)

# The target is named quadmesh_lib so it does not clash with the quadmesh
# executable; the archive is still libquadmesh.a.
add_library(quadmesh_lib STATIC ${QUADMESH_LIB_SOURCES} ${QUADMESH_HEADERS})
set_target_properties(quadmesh_lib PROPERTIES OUTPUT_NAME quadmesh LINKER_LANGUAGE CXX)
target_include_directories(quadmesh_lib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_include_directories(quadmesh_lib SYSTEM PUBLIC ${QUADMESH_EIGEN_DIR})
target_compile_options(quadmesh_lib PUBLIC ${QUADMESH_FP_FLAGS})

add_executable(quadmesh ${CMAKE_CURRENT_SOURCE_DIR}/src/cli/main.cpp)
target_link_libraries(quadmesh PRIVATE quadmesh_lib)

# Tests: Catch2 v3 amalgamated build, compiled into the test binary.
file(GLOB_RECURSE QUADMESH_TEST_SOURCES CONFIGURE_DEPENDS
  ${CMAKE_CURRENT_SOURCE_DIR}/tests/*.cpp)
add_executable(quadmesh_tests ${QUADMESH_TEST_SOURCES}
  ${QUADMESH_CATCH2_DIR}/catch_amalgamated.cpp)
target_include_directories(quadmesh_tests SYSTEM PRIVATE ${QUADMESH_CATCH2_DIR})
target_link_libraries(quadmesh_tests PRIVATE quadmesh_lib)
# Oracle data (ref_tables.py output) and round-trip output locations.
# Override at run time with QUADMESH_GT_DIR / QUADMESH_ROUNDTRIP_DIR.
set(QUADMESH_GT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../.scratch/cpp-port/ground_truth
  CACHE PATH "Ground-truth directory with meshes/ and ref/")
set(QUADMESH_ROUNDTRIP_DIR ${CMAKE_CURRENT_BINARY_DIR}/roundtrip)
target_compile_definitions(quadmesh_tests PRIVATE
  QUADMESH_GT_DIR_DEFAULT="${QUADMESH_GT_DIR}"
  QUADMESH_ROUNDTRIP_DIR_DEFAULT="${QUADMESH_ROUNDTRIP_DIR}")

# Developer tools under tools/. The diff core (diff_lib.cpp) is a small static
# library shared by diff_tool and the tests; tools are never part of the
# quadmesh library.
add_library(quadmesh_difflib STATIC ${CMAKE_CURRENT_SOURCE_DIR}/tools/diff_lib.cpp)
target_include_directories(quadmesh_difflib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/tools)
target_link_libraries(quadmesh_difflib PUBLIC quadmesh_lib)
add_executable(diff_tool ${CMAKE_CURRENT_SOURCE_DIR}/tools/diff_tool.cpp)
target_link_libraries(diff_tool PRIVATE quadmesh_difflib)
add_executable(dump_driver ${CMAKE_CURRENT_SOURCE_DIR}/tools/dump_driver.cpp)
target_link_libraries(dump_driver PRIVATE quadmesh_lib)
target_link_libraries(quadmesh_tests PRIVATE quadmesh_difflib)

enable_testing()
add_test(NAME quadmesh_tests COMMAND quadmesh_tests)
set_tests_properties(quadmesh_tests PROPERTIES FIXTURES_SETUP fort14_roundtrip_out)

# T017 Python half: the CHILmesh reader loads the C++ writer's output. Needs
# the repo virtualenv (or -DQUADMESH_PYTHON=...); skipped when it is absent.
set(QUADMESH_PYTHON ${CMAKE_CURRENT_SOURCE_DIR}/../.venv/bin/python
  CACHE FILEPATH "Python with chilmesh installed, for oracle checks")
if(EXISTS ${QUADMESH_PYTHON})
  add_test(NAME fort14_python_roundtrip
    COMMAND ${QUADMESH_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/tests/fort14_roundtrip_check.py
      ${QUADMESH_GT_DIR} ${QUADMESH_ROUNDTRIP_DIR})
  set_tests_properties(fort14_python_roundtrip PROPERTIES
    FIXTURES_REQUIRED fort14_roundtrip_out
    ENVIRONMENT "CHILMESH_BACKEND=python;MPLCONFIGDIR=${CMAKE_CURRENT_BINARY_DIR}/mplconfig")
endif()
