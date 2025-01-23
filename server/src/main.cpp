#include <pybind11/pybind11.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "libplatform/libplatform.h"
#include "v8.h"

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
                auto maybe_module = load_module(source, context);
                if (maybe_module.IsEmpty()) {
                    v8::String::Utf8Value err(isolate, try_catch.Exception());
                    throw std::runtime_error(*err);
                }
                v8::Local<v8::Module> mod;
                if (!maybe_module.ToLocal(&mod)) {
                    v8::String::Utf8Value err(isolate, try_catch.Exception());
                    throw std::runtime_error(*err);
                }
                v8::Maybe<bool> result =
                    mod->InstantiateModule(context, nullptr);
                if (result.IsNothing()) {
                    v8::String::Utf8Value err(isolate, try_catch.Exception());
                    throw std::runtime_error(*err);
                }
                if (mod->Evaluate(context).IsEmpty()) {
                    v8::String::Utf8Value err(isolate, try_catch.Exception());
                    throw std::runtime_error(*err);
                }
                auto namespace_object = mod->GetModuleNamespace();
                v8::Local<v8::Value> ret_value;
                if (namespace_object->IsObject()) {
                    auto maybe_default_export =
                        namespace_object.As<v8::Object>()->Get(
                            context, v8::String::NewFromUtf8(isolate, "default")
                                         .ToLocalChecked());
                    if (maybe_default_export.IsEmpty()) {
                        throw std::runtime_error("default export is empty");
                    }
                    auto default_export = maybe_default_export.ToLocalChecked();
                    if (default_export->IsAsyncFunction()) {
                        auto func = default_export.As<v8::Function>();
                        auto maybe_promise =
                            func->Call(context, context->Global(), 0, nullptr);
                        if (maybe_promise.IsEmpty()) {
                            v8::String::Utf8Value err(isolate,
                                                      try_catch.Exception());
                            throw std::runtime_error(
                                "call default export failed to return a "
                                "promise");
                        }
                        auto promise = maybe_promise.ToLocalChecked();
                        if (promise->IsPromise()) {
                            ret_value = promise.As<v8::Promise>()->Result();
                        } else {
                            throw std::runtime_error(
                                "promise did not resolve to a value");
                        }
                    } else {
                        throw std::runtime_error(
                            "default export is not an async function");
                    }
                } else {
                    throw std::runtime_error(
                        "module namespace is not an object");
                }
                output = *v8::String::Utf8Value(isolate, ret_value);
            }
        }
        isolate->Dispose();
        delete create_params.array_buffer_allocator;
        return output;
    }

    static v8::MaybeLocal<v8::Module> load_module(v8::Local<v8::String> code,
                                                  v8::Local<v8::Context> cx) {
        v8::ScriptOrigin origin(
            v8::String::NewFromUtf8(cx->GetIsolate(), "module")
                .ToLocalChecked(),
            0, 0, false, -1, v8::Local<v8::Value>(), false, false, true,
            v8::Local<v8::Data>());
        v8::Context::Scope context_scope(cx);
        v8::ScriptCompiler::Source source(code, origin);
        v8::MaybeLocal<v8::Module> mod;
        mod = v8::ScriptCompiler::CompileModule(cx->GetIsolate(), &source);
        return mod;
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
