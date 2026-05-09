cmake_minimum_required(VERSION 3.15)
project(edfm_python_bindings)

# 解决pybind11兼容性警告
cmake_policy(SET CMP0148 OLD)
set(PYBIND11_FINDPYTHON ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 加载IPO支持模块（解决check_ipo_supported不认识的核心错误）
include(CheckIPOSupported)

# Eigen配置
set(EIGEN3_INCLUDE_DIR "D:/eigen-3.4.0")
include_directories(${EIGEN3_INCLUDE_DIR})

# pybind11配置
set(pybind11_DIR "C:/Users/OpenCV_Demo/miniconda3/Lib/site-packages/pybind11/share/cmake/pybind11")
find_package(pybind11 REQUIRED)

# 1. 基础EDFM模块
pybind11_add_module(edfm_core
    src/lgr/edfm_3d_blackoil_lgr.cpp
)

# 2. 角点网格EDFM模块
pybind11_add_module(edfm_core_corner
    src/basic/UPGRATED_rearrangement_Corner_Point_Grid_edfm_3d_water_oil_ILUT+BiCGSTAB.cpp
)

# 3. 角点网格+LGR模块（集成真实气体PVT）
pybind11_add_module(edfm_core_corner_lgr
    src/lgr/PVT_LGR_gas_pvt_migrated.cpp
)

# 所有模块的头文件与链接配置
target_include_directories(edfm_core PRIVATE ${EIGEN3_INCLUDE_DIR})
target_link_libraries(edfm_core PRIVATE pybind11::module)

target_include_directories(edfm_core_corner PRIVATE ${EIGEN3_INCLUDE_DIR})
target_link_libraries(edfm_core_corner PRIVATE pybind11::module)

target_include_directories(edfm_core_corner_lgr PRIVATE ${EIGEN3_INCLUDE_DIR})
target_link_libraries(edfm_core_corner_lgr PRIVATE pybind11::module)
target_compile_definitions(edfm_core_corner_lgr PRIVATE EDFM_CORE_CORNER_LGR_PYBIND)

# MSVC编译优化配置
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
        target_compile_options(${target_name} PRIVATE /utf-8
            $<$<CONFIG:Release>:/GL /Oi /Ot /Gy /Gw /arch:AVX2 /fp:precise>
        )
        target_link_options(${target_name} PRIVATE
            $<$<CONFIG:Release>:/LTCG /OPT:REF /OPT:ICF>
        )
    endforeach()
endif()