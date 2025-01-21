// https://chromium.googlesource.com/v8/v8/+/branch-heads/11.9/samples/hello-world.cc

#include <pybind11/pybind11.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libplatform/libplatform.h"
#include "v8-context.h"
#include "v8-initialization.h"
#include "v8-isolate.h"
#include "v8-local-handle.h"
#include "v8-primitive.h"
#include "v8-script.h"

int
v8_init() {
    v8::V8::InitializeICUDefaultLocation(".");
    v8::V8::InitializeExternalStartupData(".");
    std::unique_ptr<v8::Platform> platform = v8::platform::NewDefaultPlatform();
    v8::V8::InitializePlatform(platform.get());
    v8::V8::Initialize();
    return 0;
}

int
v8_shutdown() {
    v8::V8::Dispose();
    v8::V8::DisposePlatform();
    return 0;
}

namespace py = pybind11;

PYBIND11_MODULE(_core, m) {
    m.doc() = "faas";
    m.def("v8_init", &v8_init, R"pbdoc(
initialize v8
    )pbdoc");
    m.def("v8_shutdown", &v8_shutdown, R"pbdoc(
shutdown v8
    )pbdoc");
}
