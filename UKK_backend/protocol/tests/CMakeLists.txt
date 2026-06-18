# protocol/tests/CMakeLists.txt
# Unit tests for UKK Protocol

cmake_minimum_required(VERSION 3.20)

# Find required packages
find_package(GTest REQUIRED)

# Test sources
set(TEST_SOURCES
    test_types.cpp
    test_validation.cpp
    test_serialization.cpp
)

# Create test executable
add_executable(ukk_protocol_tests ${TEST_SOURCES})

target_link_libraries(ukk_protocol_tests
    PRIVATE
        ukk_protocol
        GTest::gtest
        GTest::gtest_main
)

target_compile_features(ukk_protocol_tests PRIVATE cxx_std_20)

# Enable testing
include(GoogleTest)
gtest_discover_tests(ukk_protocol_tests)

# Add test target
add_test(NAME ukk_protocol_tests COMMAND ukk_protocol_tests)
