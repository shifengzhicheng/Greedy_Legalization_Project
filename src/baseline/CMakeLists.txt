cmake_minimum_required(VERSION 3.20)
project(greedy_legalization_baseline LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT DEFINED Python3_EXECUTABLE AND DEFINED ENV{CONDA_PREFIX})
  set(Python3_EXECUTABLE "$ENV{CONDA_PREFIX}/bin/python" CACHE FILEPATH "Python interpreter for baseline build")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
execute_process(
  COMMAND "${Python3_EXECUTABLE}" -c "import json, sysconfig, torch; print(json.dumps({'torch_version': torch.__version__, 'cmake_prefix_path': torch.utils.cmake_prefix_path, 'ext_suffix': sysconfig.get_config_var('EXT_SUFFIX') or ''}))"
  OUTPUT_VARIABLE TORCH_INFO_JSON
  RESULT_VARIABLE TORCH_INFO_STATUS
  OUTPUT_STRIP_TRAILING_WHITESPACE
)
if(NOT TORCH_INFO_STATUS EQUAL 0)
  message(FATAL_ERROR "Failed to query torch build settings with Python '${Python3_EXECUTABLE}'. If torch is installed in another interpreter, rerun CMake with -DPython3_EXECUTABLE=$(which python).")
endif()
string(JSON TORCH_VERSION GET "${TORCH_INFO_JSON}" torch_version)
string(JSON TORCH_CMAKE_PREFIX GET "${TORCH_INFO_JSON}" cmake_prefix_path)
string(JSON PY_EXT_SUFFIX GET "${TORCH_INFO_JSON}" ext_suffix)
string(REPLACE "." ";" TORCH_VERSION_PARTS "${TORCH_VERSION}")
list(GET TORCH_VERSION_PARTS 0 TORCH_VERSION_MAJOR)
list(GET TORCH_VERSION_PARTS 1 TORCH_VERSION_MINOR)

list(APPEND CMAKE_PREFIX_PATH "${TORCH_CMAKE_PREFIX}")
find_package(Torch REQUIRED)
find_package(OpenMP REQUIRED)

set(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../..")
set(BUILD_OUT_ROOT "${REPO_ROOT}/build/baseline_ops")
set(OPS_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/ops")
set(COMMON_INCLUDE_DIRS
  "${OPS_ROOT}"
  ${TORCH_INCLUDE_DIRS}
)
set(COMMON_COMPILE_DEFINITIONS
  TORCH_VERSION_MAJOR=${TORCH_VERSION_MAJOR}
  TORCH_VERSION_MINOR=${TORCH_VERSION_MINOR}
)
set(COMMON_COMPILE_OPTIONS -O3)

file(MAKE_DIRECTORY "${BUILD_OUT_ROOT}/greedy_legalize")
file(MAKE_DIRECTORY "${BUILD_OUT_ROOT}/abacus_legalize")

add_library(greedy_legalize_cpp MODULE
  "${OPS_ROOT}/greedy_legalize/src/greedy_legalize.cpp"
  "${OPS_ROOT}/greedy_legalize/src/greedy_legalize_cpu.cpp"
  "${OPS_ROOT}/greedy_legalize/src/legalize_bin_cpu.cpp"
  "${OPS_ROOT}/greedy_legalize/src/merge_bin_cpu.cpp"
  "${OPS_ROOT}/utility/src/msg.cpp"
)
target_include_directories(greedy_legalize_cpp PRIVATE ${COMMON_INCLUDE_DIRS})
target_compile_definitions(greedy_legalize_cpp PRIVATE ${COMMON_COMPILE_DEFINITIONS})
target_compile_options(greedy_legalize_cpp PRIVATE ${COMMON_COMPILE_OPTIONS})
target_link_libraries(greedy_legalize_cpp PRIVATE ${TORCH_LIBRARIES} OpenMP::OpenMP_CXX Python3::Module)
set_target_properties(greedy_legalize_cpp PROPERTIES
  PREFIX ""
  SUFFIX "${PY_EXT_SUFFIX}"
  LIBRARY_OUTPUT_DIRECTORY "${BUILD_OUT_ROOT}/greedy_legalize"
)

add_library(abacus_legalize_cpp MODULE
  "${OPS_ROOT}/abacus_legalize/src/abacus_legalize.cpp"
  "${OPS_ROOT}/utility/src/msg.cpp"
)
target_include_directories(abacus_legalize_cpp PRIVATE ${COMMON_INCLUDE_DIRS})
target_compile_definitions(abacus_legalize_cpp PRIVATE ${COMMON_COMPILE_DEFINITIONS})
target_compile_options(abacus_legalize_cpp PRIVATE ${COMMON_COMPILE_OPTIONS})
target_link_libraries(abacus_legalize_cpp PRIVATE ${TORCH_LIBRARIES} OpenMP::OpenMP_CXX Python3::Module)
set_target_properties(abacus_legalize_cpp PROPERTIES
  PREFIX ""
  SUFFIX "${PY_EXT_SUFFIX}"
  LIBRARY_OUTPUT_DIRECTORY "${BUILD_OUT_ROOT}/abacus_legalize"
)
