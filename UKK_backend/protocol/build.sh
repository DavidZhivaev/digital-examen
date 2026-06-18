#!/bin/bash
# protocol/build.sh
# Build script for UKK Protocol library

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
BUILD_TYPE="${BUILD_TYPE:-Release}"
GENERATOR="${GENERATOR:-}"
RUN_TESTS="${RUN_TESTS:-ON}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Options:
    -h, --help          Show this help message
    -c, --clean         Clean build directory before building
    -d, --debug         Build in Debug mode (default: Release)
    -t, --no-tests      Skip running tests
    -g, --generate      Only generate code, don't build
    -G, --generator     CMake generator (e.g., "Ninja")
    -j, --jobs N        Number of parallel jobs (default: auto)

Environment variables:
    BUILD_TYPE          Build type (Debug/Release)
    GENERATOR           CMake generator
    RUN_TESTS           Run tests after build (ON/OFF)

Examples:
    ./build.sh                  # Release build with tests
    ./build.sh --debug          # Debug build with tests
    ./build.sh --clean --debug  # Clean debug build
    ./build.sh --no-tests       # Build without running tests
EOF
}

# Parse arguments
CLEAN=0
GENERATE_ONLY=0
JOBS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -c|--clean)
            CLEAN=1
            shift
            ;;
        -d|--debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        -t|--no-tests)
            RUN_TESTS="OFF"
            shift
            ;;
        -g|--generate)
            GENERATE_ONLY=1
            shift
            ;;
        -G|--generator)
            GENERATOR="$2"
            shift 2
            ;;
        -j|--jobs)
            JOBS="-j $2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check dependencies
check_dependencies() {
    print_step "Checking dependencies..."

    if ! command -v cmake &> /dev/null; then
        print_error "CMake is required but not installed"
        exit 1
    fi

    local cmake_version
    cmake_version=$(cmake --version | head -1 | awk '{print $3}')
    print_step "CMake version: ${cmake_version}"
}

# Generate code
generate_code() {
    print_step "Generating protocol code..."

    local tools_dir="${SCRIPT_DIR}/tools"
    local gen_dir="${SCRIPT_DIR}/generated"

    mkdir -p "${gen_dir}"

    # Build and run code generators if sources exist
    if [[ -f "${tools_dir}/generate_cpp.cpp" ]]; then
        print_step "Building C++ code generator..."
        local gen_cpp_bin="${gen_dir}/generate_cpp"
        g++ -std=c++20 -O2 "${tools_dir}/generate_cpp.cpp" -o "${gen_cpp_bin}" 2>/dev/null || {
            print_warning "Could not compile generate_cpp.cpp (may need msgpack headers)"
        }

        if [[ -x "${gen_cpp_bin}" ]]; then
            print_step "Running C++ code generator..."
            cd "${gen_dir}" && "${gen_cpp_bin}"
            cd "${SCRIPT_DIR}"
        fi
    fi

    if [[ -f "${tools_dir}/generate_schemas.cpp" ]]; then
        print_step "Building schema generator..."
        local gen_schema_bin="${gen_dir}/generate_schemas"
        g++ -std=c++20 -O2 "${tools_dir}/generate_schemas.cpp" -o "${gen_schema_bin}" 2>/dev/null || {
            print_warning "Could not compile generate_schemas.cpp"
        }

        if [[ -x "${gen_schema_bin}" ]]; then
            print_step "Running schema generator..."
            mkdir -p "${SCRIPT_DIR}/schemas"
            "${gen_schema_bin}" "${SCRIPT_DIR}/schemas"
        fi
    fi

    print_step "Code generation complete"
}

# Clean build directory
clean_build() {
    if [[ -d "${BUILD_DIR}" ]]; then
        print_step "Cleaning build directory..."
        rm -rf "${BUILD_DIR}"
    fi
}

# Configure project
configure() {
    print_step "Configuring project (${BUILD_TYPE})..."

    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"

    local cmake_args=(
        -DCMAKE_BUILD_TYPE="${BUILD_TYPE}"
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    )

    if [[ -n "${GENERATOR}" ]]; then
        cmake_args+=(-G "${GENERATOR}")
    fi

    cmake "${cmake_args[@]}" "${SCRIPT_DIR}"
}

# Build project
build() {
    print_step "Building project..."

    cd "${BUILD_DIR}"
    cmake --build . ${JOBS}
}

# Run tests
run_tests() {
    if [[ "${RUN_TESTS}" == "ON" ]]; then
        print_step "Running tests..."
        cd "${BUILD_DIR}"
        ctest --output-on-failure ${JOBS}
    else
        print_warning "Skipping tests (--no-tests specified)"
    fi
}

# Main execution
main() {
    print_step "UKK Protocol Build Script"
    print_step "========================="

    check_dependencies

    if [[ ${CLEAN} -eq 1 ]]; then
        clean_build
    fi

    generate_code

    if [[ ${GENERATE_ONLY} -eq 1 ]]; then
        print_step "Generation complete (--generate specified, skipping build)"
        exit 0
    fi

    configure
    build

    if [[ -f "${BUILD_DIR}/ukk_protocol_tests" ]]; then
        run_tests
    else
        print_warning "Test executable not found, skipping tests"
    fi

    print_step "Build complete!"
    echo ""
    echo "Build artifacts:"
    echo "  - Headers: ${SCRIPT_DIR}/include/"
    echo "  - Generated: ${SCRIPT_DIR}/generated/"
    echo "  - Schemas: ${SCRIPT_DIR}/schemas/"
    if [[ -d "${BUILD_DIR}" ]]; then
        echo "  - Build: ${BUILD_DIR}/"
    fi
}

main
