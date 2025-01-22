// https://chromium.googlesource.com/v8/v8/+/branch-heads/11.9/samples/hello-world.cc

#include <pybind11/pybind11.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "libplatform/libplatform.h"
#include "v8-context.h"
#include "v8-exception.h"
#include "v8-initialization.h"
#include "v8-isolate.h"
#include "v8-local-handle.h"
#include "v8-primitive.h"
#include "v8-script.h"
#include "v8-snapshot.h"

namespace py = pybind11;

struct V8System {
    std::unique_ptr<v8::Platform> platform;

    V8System() {
        platform = v8::platform::NewDefaultPlatform();
        v8::V8::InitializePlatform(platform.get());
        v8::V8::Initialize();
    }

    static std::string run(const std::string& src) {
        // create isolate and make it the current isolate
        v8::Isolate::CreateParams create_params;
        create_params.array_buffer_allocator =
            v8::ArrayBuffer::Allocator::NewDefaultAllocator();
        v8::Isolate* isolate = v8::Isolate::New(create_params);
        std::string output;
        {
            v8::Isolate::Scope isolate_scope(isolate);
            v8::HandleScope handle_scope(isolate);
            // create context
            v8::Local<v8::Context> context = v8::Context::New(isolate);
            // enter the context for compiling and running the hello world
            // script.
            v8::Context::Scope context_scope(context);
            {
                v8::TryCatch try_catch(isolate);
                v8::Local<v8::String> source =
                    v8::String::NewFromUtf8(isolate, src.c_str(),
                                            v8::NewStringType::kNormal)
                        .ToLocalChecked();
                auto maybe_script = v8::Script::Compile(context, source);
                if (maybe_script.IsEmpty()) {
                    v8::String::Utf8Value err(isolate, try_catch.Exception());
                    throw std::runtime_error(*err);
                }
                v8::Local<v8::Script> script = maybe_script.ToLocalChecked();
                v8::Local<v8::Value> result =
                    script->Run(context).ToLocalChecked();
                v8::String::Utf8Value utf8(isolate, result);
                output = *utf8 ? *utf8 : "undefined";
            }
        }
        isolate->Dispose();
        delete create_params.array_buffer_allocator;
        return output;
    }

    ~V8System() {
        v8::V8::Dispose();
        v8::V8::DisposePlatform();
    }
};

PYBIND11_MODULE(_core, m) {   // NOLINT(misc-use-anonymous-namespace)
    m.doc() = "faas";
    py::class_<V8System>(m, "V8System")
        .def(py::init())
        .def_static("run", &V8System::run, R"pbdoc(run script)pbdoc");
}
