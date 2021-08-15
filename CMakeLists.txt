project(Knapsack)
cmake_minimum_required(VERSION 3.0)

add_executable(knapsack knapsack.cpp)

find_package(Boost REQUIRED COMPONENTS)
target_link_libraries(knapsack PRIVATE Boost::boost)
