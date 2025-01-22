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
#include "v8-snapshot.h"

namespace py = pybind11;

struct API {
    static void Init() {
        v8::V8::InitializeICUDefaultLocation(".");
        v8::V8::InitializeExternalStartupData(".");
        std::unique_ptr<v8::Platform> platform =
            v8::platform::NewDefaultPlatform();
        v8::V8::InitializePlatform(platform.get());
        v8::V8::Initialize();
    }

    static std::vector<uint8_t> Compile(const std::string& src) {
        v8::SnapshotCreator snapshot_creator = v8::SnapshotCreator();
        v8::StartupData snapshot_blob = snapshot_creator.CreateBlob(
            v8::SnapshotCreator::FunctionCodeHandling::kKeep);
        v8::Isolate::CreateParams create_params;
        create_params.snapshot_blob = &snapshot_blob;
        create_params.array_buffer_allocator =
            v8::ArrayBuffer::Allocator::NewDefaultAllocator();
        // isolate is an instance of v8::Isolate - own heap, context, etc.
        v8::Isolate* isolate = v8::Isolate::New(create_params);
        {
            v8::Isolate::Scope isolate_scope(isolate);
            v8::HandleScope handle_scope(isolate);
            // context is an instance of v8::Context - global object, etc.
            v8::Local<v8::Context> context = v8::Context::New(isolate);
            // compile the source code to bytecode
            v8::Local<v8::String> source =
                v8::String::NewFromUtf8(isolate, src.c_str(),
                                        v8::NewStringType::kNormal)
                    .ToLocalChecked();
            v8::ScriptOrigin script_origin(
                v8::String::NewFromUtf8(isolate, "source").ToLocalChecked());
            v8::ScriptCompiler::Source script_source(source, script_origin);
            v8::ScriptCompiler::Compile(context, &script_source)
                .ToLocalChecked();
            int length = script_source.GetCachedData()->length;
            auto* cache_data = new uint8_t[length];
            memcpy(cache_data, script_source.GetCachedData()->data, length);
            return std::vector<uint8_t>(cache_data, cache_data + length);
        }
        isolate->Dispose();
        delete create_params.array_buffer_allocator;
    }

    static void Shutdown() {
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
        .def("compile", &API::Compile, R"pbdoc(compile v8 script)pbdoc")
        .def("init", &API::Init, R"pbdoc(initialize v8)pbdoc")
        .def("shutdown", &API::Shutdown, R"pbdoc(shutdown v8)pbdoc");
}
