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

struct V8System {
    std::unique_ptr<v8::Platform> platform;

    V8System() {
        // TODO(thejchap) - what does this do
        v8::V8::InitializeICUDefaultLocation(".");
        v8::V8::InitializeExternalStartupData(".");

        // initialize v8
        platform = v8::platform::NewDefaultPlatform();
        v8::V8::InitializePlatform(platform.get());
        v8::V8::Initialize();
    }

    static std::vector<uint8_t> compile(const std::string& src) {
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

    ~V8System() {
        // destructor - clean up v8
        v8::V8::Dispose();
        v8::V8::DisposePlatform();
    }
};

namespace py = pybind11;

PYBIND11_MODULE(_core, m) {   // NOLINT(misc-use-anonymous-namespace)
    m.doc() = "faas";
    py::class_<V8System>(m, "V8System")
        .def(py::init())
        .def("compile", &V8System::compile, R"pbdoc(compile v8 script)pbdoc");
}
