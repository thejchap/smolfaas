#include <libplatform/libplatform.h>
#include <pybind11/pybind11.h>
#include <v8.h>

#include <memory>
#include <stdexcept>
#include <string>

#include "lrucache.h"

namespace py = pybind11;

/**
 * V8System class that encapsulates the v8 runtime
 * stateful/instantiated when the embedding app is started up,
 * torn down on app shutdown
 */
class V8System {
   public:
    /**
     * constructor that initializes v8 and the platform
     */
    V8System() {
        platform_ = v8::platform::NewDefaultPlatform();
        v8::V8::InitializePlatform(platform_.get());
        v8::V8::Initialize();
    }

    /**
     * takes a script source code and compiles it+runs it
     */
    static std::string compile_and_invoke_source(const std::string& src) {
        // create a new isolate
        v8::Isolate::CreateParams create_params;
        create_params.array_buffer_allocator =
            v8::ArrayBuffer::Allocator::NewDefaultAllocator();
        // custom deleter for the isolate - dispose when the unique_ptr goes out
        // of scope
        std::unique_ptr<v8::Isolate, decltype(&dispose_isolate)> isolate(
            v8::Isolate::New(create_params), dispose_isolate);
        v8::Isolate::Scope isolate_scope(isolate.get());
        v8::HandleScope handle_scope(isolate.get());
        v8::Local<v8::Context> context = v8::Context::New(isolate.get());
        v8::Context::Scope context_scope(context);
        v8::TryCatch try_catch(isolate.get());
        auto source = to_v8_string(isolate.get(), src);
        auto maybe_module = load_module(source, context);
        if (maybe_module.IsEmpty()) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        auto module = maybe_module.ToLocalChecked();
        if (!module->InstantiateModule(context, nullptr).FromMaybe(false)) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        if (module->Evaluate(context).IsEmpty()) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        return call_default_export(isolate.get(), context, module);
    }

    /**
     * restore the v8 heap from a snapshot
     * into an isolate and run the module
     */
    static std::string invoke_source_with_snapshot(
        const std::string& source, const std::string& snapshot_bytes) {
        // restore snapshot into create params for isolate
        v8::StartupData snapshot(snapshot_bytes.c_str(), snapshot_bytes.size());
        v8::Isolate::CreateParams create_params;
        create_params.snapshot_blob = &snapshot;
        create_params.array_buffer_allocator =
            v8::ArrayBuffer::Allocator::NewDefaultAllocator();
        // create isolate
        std::unique_ptr<v8::Isolate, decltype(&dispose_isolate)> isolate(
            v8::Isolate::New(create_params), dispose_isolate);
        // create scope and context
        v8::Isolate::Scope isolate_scope(isolate.get());
        v8::HandleScope handle_scope(isolate.get());
        v8::Local<v8::Context> context = v8::Context::New(isolate.get());
        // enter context
        v8::Context::Scope context_scope(context);
        v8::TryCatch try_catch(isolate.get());
        // load module
        auto source_code = to_v8_string(isolate.get(), source);
        auto maybe_module = load_module(source_code, context);
        if (maybe_module.IsEmpty()) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        auto mod = maybe_module.ToLocalChecked();
        if (!mod->InstantiateModule(context, nullptr).FromMaybe(false)) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        if (mod->Evaluate(context).IsEmpty()) {
            throw_runtime_error(isolate.get(), try_catch.Exception());
        }
        return call_default_export(isolate.get(), context, mod);
    }

    /**
     * compile source code
     * take snapshot of the v8 heap after the module is loaded and compiled
     * return snapshot so app can save the deployment for later invocations
     */
    static py::bytes compile_source_to_snapshot(const std::string& src) {
        // this uses a different isolate setup than normal script compilation
        v8::SnapshotCreator snapshot_creator;
        auto* isolate = snapshot_creator.GetIsolate();
        {
            v8::Isolate::Scope isolate_scope(isolate);
            v8::HandleScope handle_scope(isolate);
            v8::Local<v8::Context> context = v8::Context::New(isolate);
            snapshot_creator.SetDefaultContext(context);
            v8::Context::Scope context_scope(context);
            v8::TryCatch try_catch(isolate);
            auto source = to_v8_string(isolate, src);
            auto maybe_module = load_module(source, context);
            if (maybe_module.IsEmpty()) {
                throw_runtime_error(isolate, try_catch.Exception());
            }
            auto module = maybe_module.ToLocalChecked();
            if (!module->InstantiateModule(context, nullptr).FromMaybe(false)) {
                throw_runtime_error(isolate, try_catch.Exception());
            }
            if (module->Evaluate(context).IsEmpty()) {
                throw_runtime_error(isolate, try_catch.Exception());
            }
        }
        v8::StartupData snapshot = snapshot_creator.CreateBlob(
            v8::SnapshotCreator::FunctionCodeHandling::kKeep);
        py::bytes snapshot_bytes(snapshot.data, snapshot.raw_size);
        delete[] snapshot.data;
        return snapshot_bytes;
    }

   private:
    /**
     * v8 platform instance. this needs to be kept alive for the lifetime of the
     * class instance
     */
    std::unique_ptr<v8::Platform> platform_;
    /**
     * keep 8 isolates warm
     */
    LRUCache<std::string, v8::Isolate*> isolate_cache{8};

    /**
     * load a module from source code in the given context
     */
    static v8::MaybeLocal<v8::Module> load_module(v8::Local<v8::String> code,
                                                  v8::Local<v8::Context> cx) {
        // compile the module
        v8::ScriptOrigin origin(to_v8_string(cx->GetIsolate(), "module"), 0, 0,
                                false, -1, v8::Local<v8::Value>(), false, false,
                                true, v8::Local<v8::PrimitiveArray>());
        v8::ScriptCompiler::Source source(code, origin);
        auto res = v8::ScriptCompiler::CompileModule(cx->GetIsolate(), &source);
        return res;
    }

    /**
     * takes a compiled esm module and calls the default (async) export. ie:
     * ```js
     * export default async function() {
     *  return "hello world";
     * }
     * ```
     */
    static std::string call_default_export(v8::Isolate* isolate,
                                           v8::Local<v8::Context> context,
                                           v8::Local<v8::Module> module) {
        // get the default export from the module
        v8::Local<v8::Value> namespace_object = module->GetModuleNamespace();
        if (!namespace_object->IsObject()) {
            throw std::runtime_error("module namespace is not an object");
        }
        v8::Local<v8::Object> ns_object = namespace_object.As<v8::Object>();
        auto maybe_default_export =
            ns_object->Get(context, to_v8_string(isolate, "default"));
        if (maybe_default_export.IsEmpty()) {
            throw std::runtime_error("default export is empty");
        }
        auto default_export = maybe_default_export.ToLocalChecked();
        if (!default_export->IsAsyncFunction()) {
            throw std::runtime_error(
                "default export is not an async function. got: " +
                std::string(*v8::String::Utf8Value(isolate, default_export)));
        }
        // call the default export
        auto func = default_export.As<v8::Function>();
        auto maybe_promise = func->Call(context, context->Global(), 0, nullptr);
        if (maybe_promise.IsEmpty()) {
            throw std::runtime_error("failed to call the default export");
        }
        auto promise = maybe_promise.ToLocalChecked();
        if (!promise->IsPromise()) {
            throw std::runtime_error("return value is not a promise");
        }
        // wait for the promise to resolve
        auto result = promise.As<v8::Promise>()->Result();
        return *v8::String::Utf8Value(isolate, result);
    }

    static v8::Local<v8::String> to_v8_string(v8::Isolate* isolate,
                                              const std::string& str) {
        return v8::String::NewFromUtf8(isolate, str.c_str(),
                                       v8::NewStringType::kNormal)
            .ToLocalChecked();
    }

    static void throw_runtime_error(v8::Isolate* isolate,
                                    v8::Local<v8::Value> exception) {
        v8::String::Utf8Value error(isolate, exception);
        throw std::runtime_error(*error ? *error : "unknown error");
    }

    /**
     * dispose the isolate and its array buffer allocator
     * this is called when the unique_ptr of the isolate goes out of scope
     */
    static void dispose_isolate(v8::Isolate* isolate) {
        isolate->Dispose();
        delete v8::ArrayBuffer::Allocator::NewDefaultAllocator();
    }
};

/**
 * expose the V8System class to python
 */
PYBIND11_MODULE(_core, m) {   // NOLINT(misc-use-anonymous-namespace)
    py::class_<V8System>(m, "V8System")
        .def(py::init<>())
        .def_static("compile_and_invoke_source",
                    &V8System::compile_and_invoke_source)
        .def_static("compile_source_to_snapshot",
                    &V8System::compile_source_to_snapshot)
        .def_static("invoke_source_with_snapshot",
                    &V8System::invoke_source_with_snapshot);
}
