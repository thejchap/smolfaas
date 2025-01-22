// https://chromium.googlesource.com/v8/v8/+/branch-heads/11.9/samples/hello-world.cc

#include <pybind11/pybind11.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "libplatform/libplatform.h"
#include "v8-context.h"
#include "v8-initialization.h"
#include "v8-isolate.h"
#include "v8-local-handle.h"
#include "v8-primitive.h"
#include "v8-script.h"

namespace py = pybind11;

struct API {
    void V8Init() {   // NOLINT(readability-convert-member-functions-to-static)
        v8::V8::InitializeICUDefaultLocation(".");
        v8::V8::InitializeExternalStartupData(".");
        std::unique_ptr<v8::Platform> platform =
            v8::platform::NewDefaultPlatform();
        v8::V8::InitializePlatform(platform.get());
        v8::V8::Initialize();
    }

    void
    V8Shutdown() {   // NOLINT(readability-convert-member-functions-to-static)
        // docs say: it should generally not be necessary to dispose v8 before
        // exiting a process, this should happen automatically.
        // so not gonna call this from python for now
        v8::V8::Dispose();
        v8::V8::DisposePlatform();
    }
};

PYBIND11_MODULE(_core, m) {   // NOLINT(misc-use-anonymous-namespace)
    m.doc() = "faas";
    py::class_<API>(m, "V8")
        .def(py::init<>())
        .def("init", &API::V8Init, R"pbdoc(
initialize v8
        )pbdoc")
        .def("shutdown", &API::V8Shutdown, R"pbdoc(
shutdown v8
        )pbdoc");
}
