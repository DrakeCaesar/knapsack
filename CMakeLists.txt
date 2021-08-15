project(Knapsack)
cmake_minimum_required(VERSION 3.0)

add_executable(knapsack knapsack.cpp)

set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,-z,stack-size=1000000")
find_package(Boost REQUIRED COMPONENTS)
target_link_libraries(knapsack PRIVATE Boost::boost)
