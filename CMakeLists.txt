cmake_minimum_required(VERSION 3.15)
project(edfm_python_bindings)

# Keep compatibility with older pybind11/CMake combinations.
cmake_policy(SET CMP0148 OLD)
set(PYBIND11_FINDPYTHON ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(CheckIPOSupported)

set(EIGEN3_INCLUDE_DIR "" CACHE PATH "Path to Eigen3 include directory")
if(NOT EIGEN3_INCLUDE_DIR)
    find_path(EIGEN3_INCLUDE_DIR
        NAMES Eigen/Core
        PATHS
            "D:/vtk/vcpkg/installed/x64-windows/include/eigen3"
            "D:/eigen-3.4.0"
            "D:/mingw64/eigen"
            "D:/eigen-3.3.8"
    )
endif()

if(NOT EIGEN3_INCLUDE_DIR)
    message(FATAL_ERROR "Eigen3 headers not found. Set EIGEN3_INCLUDE_DIR to your Eigen include path.")
endif()

set(pybind11_DIR "" CACHE PATH "Path to pybind11 CMake config directory")
if(NOT pybind11_DIR)
    set(_PYBIND11_CANDIDATE_DIRS
        "D:/pybind11_site/pybind11/share/cmake/pybind11"
        "C:/Users/OpenCV_Demo/miniconda3/Lib/site-packages/pybind11/share/cmake/pybind11"
        "D:/anaconda3/envs/transformers/Lib/site-packages/pybind11/share/cmake/pybind11"
        "D:/Anaconda/envs/oil/Lib/site-packages/pybind11/share/cmake/pybind11"
    )
    foreach(_candidate IN LISTS _PYBIND11_CANDIDATE_DIRS)
        if(EXISTS "${_candidate}")
            set(pybind11_DIR "${_candidate}")
            break()
        endif()
    endforeach()
    unset(_candidate)
    unset(_PYBIND11_CANDIDATE_DIRS)
endif()

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(edfm_core
    src/lgr/edfm_3d_blackoil_lgr.cpp
)

pybind11_add_module(edfm_core_corner
    src/basic/UPGRATED_rearrangement_Corner_Point_Grid_edfm_3d_water_oil_ILUT+BiCGSTAB.cpp
)

pybind11_add_module(edfm_core_corner_lgr
    src/lgr/PVT_LGR_gas_pvt_migrated.cpp
)

foreach(target_name IN ITEMS edfm_core edfm_core_corner edfm_core_corner_lgr)
    target_include_directories(${target_name} PRIVATE ${EIGEN3_INCLUDE_DIR})
    target_link_libraries(${target_name} PRIVATE pybind11::module)
endforeach()

target_compile_definitions(edfm_core_corner_lgr PRIVATE EDFM_CORE_CORNER_LGR_PYBIND)

if(MSVC)
    check_ipo_supported(RESULT msipo_supported OUTPUT msipo_error LANGUAGES CXX)
    if(msipo_supported)
        set_property(TARGET edfm_core PROPERTY INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE)
        set_property(TARGET edfm_core_corner PROPERTY INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE)
        set_property(TARGET edfm_core_corner_lgr PROPERTY INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE)
    else()
        message(WARNING "MSVC IPO/LTO is not supported: ${msipo_error}")
    endif()

    foreach(target_name IN ITEMS edfm_core edfm_core_corner edfm_core_corner_lgr)
        target_compile_options(${target_name} PRIVATE
            /utf-8
            $<$<CONFIG:Release>:/GL /Oi /Ot /Gy /Gw /arch:AVX2 /fp:precise>
        )
        target_link_options(${target_name} PRIVATE
            $<$<CONFIG:Release>:/LTCG /OPT:REF /OPT:ICF>
        )
    endforeach()
endif()
